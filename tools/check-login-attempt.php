<?php
/**
 * Tests for web/login-attempt.php, which tells Admin on Slack when someone uses
 * the client login. Loaded from the command line, where its request part does
 * not run, so the functions are tested here and nothing reaches Slack.
 *
 * Run from anywhere with: php tools/check-login-attempt.php
 */

declare(strict_types=1);

require_once dirname(__DIR__) . '/web/login-attempt.php';

$passed = 0;
$failed = 0;
$check = function (bool $condition, string $label) use (&$passed, &$failed): void {
    if ($condition) {
        $passed++;
        echo "  ok    {$label}\n";
    } else {
        $failed++;
        echo "  FAIL  {$label}\n";
    }
};

echo "Where the request came from\n";
$check(login_attempt_same_site(['HTTP_ORIGIN' => 'https://aisense.no']), 'the site itself is accepted');
$check(login_attempt_same_site(['HTTP_ORIGIN' => 'https://www.aisense.no/']), 'and the www name');
$check(!login_attempt_same_site(['HTTP_ORIGIN' => 'https://evil.example']), 'another origin is refused');
$check(!login_attempt_same_site(['HTTP_ORIGIN' => 'https://aisense.no.evil.example']), 'a name that only starts like ours is refused');
$check(login_attempt_same_site(['HTTP_REFERER' => 'https://aisense.no/login']), 'without Origin, a Referer from the site is accepted');
$check(!login_attempt_same_site(['HTTP_REFERER' => 'https://aisense.no.evil.example/login']), 'and one that only starts like it is not');
$check(!login_attempt_same_site([]), 'with neither, the request is refused');

echo "\nThe email address, and nothing else\n";
$check(login_attempt_email(['email' => ' name@company.com ']) === 'name@company.com', 'a valid address is kept, trimmed');
$check(login_attempt_email(['email' => 'not an address']) === '', 'an invalid one is refused');
$check(login_attempt_email(['email' => str_repeat('a', 250) . '@b.no']) === '', 'one over 254 characters is refused');
$check(login_attempt_email(['email' => ['name@company.com']]) === '', 'something that is not a string is refused');
$check(login_attempt_email([]) === '', 'no address is refused');
$source = (string) file_get_contents(dirname(__DIR__) . '/web/login-attempt.php');
$check(strpos($source, "\$input['password']") === false && strpos($source, '$_POST') === false, 'the handler never reads a password field');
$page = (string) file_get_contents(dirname(__DIR__) . '/web/login.html');
$check(preg_match('/JSON\.stringify\(\{\s*email:[^}]*\}\)/', $page) === 1 && preg_match('/JSON\.stringify\(\{[^}]*password/', $page) === 0, 'the page sends the email address and never the password');

echo "\nThe limits\n";
$dir = rtrim(sys_get_temp_dir(), '/\\') . '/aisense-login-check-' . bin2hex(random_bytes(6));
$now = 1791024067;
$results = [];
for ($i = 0; $i < 4; $i++) {
    $results[] = login_attempt_allowed('203.0.113.9', $dir, $now + $i);
}
$check($results === [true, true, true, false], 'one address reaches Slack three times an hour, not four');
$check(login_attempt_allowed('203.0.113.9', $dir, $now + 3601 + 3), 'and again once the hour has passed');
$files = glob($dir . '/*.json');
$check(is_array($files) && strpos((string) file_get_contents($files[0]), '203.0.113.9') === false && strpos(implode('', array_map('basename', $files)), '203.0.113.9') === false, 'the address itself is never written, only its hash');
$others = [];
for ($i = 0; $i < 20; $i++) {
    $others[] = login_attempt_allowed('198.51.100.' . $i, $dir . '-total', $now);
}
$check(!in_array(false, $others, true) && !login_attempt_allowed('198.51.100.99', $dir . '-total', $now), 'twenty lines an hour in total, then none');
touch($dir . '/' . hash('sha256', 'login-attempt|192.0.2.1') . '.json', $now - 7200);
login_attempt_allowed('192.0.2.2', $dir, $now);
$check(!is_file($dir . '/' . hash('sha256', 'login-attempt|192.0.2.1') . '.json'), 'an address file older than an hour is removed by the next visitor');
$check(login_attempt_allowed('203.0.113.9', '/proc/no-such-dir/' . bin2hex(random_bytes(4)), $now), 'a directory that cannot be made counts as no limit, so the form still answers');
foreach ([$dir, $dir . '-total'] as $clean) {
    foreach ((array) glob($clean . '/*') as $file) {
        @unlink((string) $file);
    }
    @rmdir($clean);
}

echo "\nThe line Slack shows\n";
$line = login_attempt_message('a<b>&c@d.no', new DateTime('2026-10-03 14:05:00', new DateTimeZone('Europe/Oslo')));
$check(strpos($line, 'a&lt;b&gt;&amp;c@d.no') !== false, 'Slack markup in the address is written as entities');
$check(strpos($line, '3 Oct 2026 14:05 Oslo time') !== false, 'with the time in Oslo');
$check(strpos($line, 'password') === false, 'and no word about a password, because there is none to give');

echo "\ncheck-login-attempt: {$passed} passed / {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
