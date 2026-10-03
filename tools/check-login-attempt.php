<?php
/**
 * Tests for web/login-attempt.php, which tells Admin on Slack when someone uses
 * the client login, and for the form on web/login.html. The handler is loaded
 * from the command line, where its request part does not run, so the functions
 * are tested here and nothing reaches Slack.
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
$json = login_attempt_input('application/json', '{"email":"a@b.no","password":"hunter2","website":""}', []);
$check($json === ['email' => 'a@b.no', 'website' => '', 'form' => false], 'from the script\'s JSON: the address and the hidden field, never the password');
$form = login_attempt_input('application/x-www-form-urlencoded', 'email=a%40b.no', ['email' => 'a@b.no', 'password' => 'hunter2']);
$check($form === ['email' => 'a@b.no', 'website' => '', 'form' => true], 'from a form post without JavaScript: the same, and marked as a form post');
$check(login_attempt_input('application/json', 'not json', [])['email'] === '', 'a body that is not JSON carries no address');
$check(login_attempt_email(['email' => ' name@company.com ']) === 'name@company.com', 'a valid address is kept, trimmed');
$check(login_attempt_email(['email' => 'not an address']) === '', 'an invalid one is refused');
$check(login_attempt_email(['email' => str_repeat('a', 250) . '@b.no']) === '', 'one over 254 characters is refused');
$check(login_attempt_email([]) === '', 'no address is refused');

echo "\nThe form on /login\n";
$page = (string) file_get_contents(dirname(__DIR__) . '/web/login.html');
preg_match('/<input\b[^>]*\bid="login-password"[^>]*>/', $page, $password_field);
$check(isset($password_field[0]) && strpos($password_field[0], 'name=') === false, 'the password field has no name, so no form submission can carry it');
preg_match('/<form\b[^>]*\bid="login-form"[^>]*>/', $page, $form_tag);
$check(isset($form_tag[0]) && strpos($form_tag[0], 'method="post"') !== false && strpos($form_tag[0], 'action="/login-attempt.php"') !== false, 'without JavaScript the form posts to the handler, so nothing lands in a URL');
$check(preg_match('/JSON\.stringify\(\{\s*email:[^}]*\}\)/', $page) === 1 && preg_match('/JSON\.stringify\(\{[^}]*password/', $page) === 0, 'with JavaScript it sends the email address and never the password');

echo "\nThe answer without JavaScript\n";
$html = login_attempt_page('Client accounts are not open yet', 'a <b> & "c"');
$check(strpos($html, 'a &lt;b&gt; &amp; &quot;c&quot;') !== false && strpos($html, 'href="/login"') !== false, 'a short page, its text escaped, with the way back');

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

// A limit that cannot be checked is a limit reached: Slack gets nothing. A
// path under an ordinary file cannot become a directory on any system, where
// /proc/... would be created as a real directory on Windows.
$plain = $dir . '-plain-file';
file_put_contents($plain, 'x');
$blocked = [];
for ($i = 0; $i < 25; $i++) {
    $blocked[] = login_attempt_allowed('203.0.113.' . $i, $plain . '/counters', $now);
}
@unlink($plain);
$check(!in_array(true, $blocked, true), 'with no directory for the counters, none of 25 attempts reaches Slack');
$jammed = $dir . '-jammed';
mkdir($jammed . '/all.json', 0700, true);
$check(!login_attempt_allowed('203.0.113.50', $jammed, $now), 'with a counter file that cannot be opened, Slack gets nothing either');
foreach ([$dir, $dir . '-total', $jammed] as $clean) {
    foreach ((array) glob($clean . '/*') as $file) {
        is_dir((string) $file) ? @rmdir((string) $file) : @unlink((string) $file);
    }
    @rmdir($clean);
}

echo "\nHanding the line to slack_alert\n";
// A stand-in that writes what it was given, one argument per line.
$stub = rtrim(sys_get_temp_dir(), '/\\') . '/aisense-slack-stub-' . bin2hex(random_bytes(6));
$seen = $stub . '.out';
file_put_contents($stub . '.php', '<?php file_put_contents(' . var_export($seen, true) . ', implode("\n", array_slice($argv, 1))); exit(0);');
$hostile = 'Someone: a$(touch /tmp/pwned)`id`;"x"\'y\' | & > <b>@d.no';
$check(login_attempt_slack($hostile, [PHP_BINARY, $stub . '.php']) === '', 'a line is handed over and the stand-in reports success');
$check((string) @file_get_contents($seen) === $hostile, 'it arrives as one argument, byte for byte, with no shell to run what is in it');
file_put_contents($stub . '.php', '<?php fwrite(STDERR, "no token"); exit(3);');
$why = login_attempt_slack('x', [PHP_BINARY, $stub . '.php']);
$check(strpos($why, 'exited with 3') !== false && strpos($why, 'no token') !== false, 'a failure comes back with its exit code and what it said, for the error log');
$check(strpos(login_attempt_slack('x', [$stub . '-missing']), 'not there or not executable') !== false, 'a missing slack_alert is reported, not run');
@unlink($stub . '.php');
@unlink($seen);

echo "\nThe line Slack shows\n";
$line = login_attempt_message('a<b>&c@d.no', new DateTime('2026-10-03 14:05:00', new DateTimeZone('Europe/Oslo')));
$check(strpos($line, 'a&lt;b&gt;&amp;c@d.no') !== false, 'Slack markup in the address is written as entities');
$check(strpos($line, '3 Oct 2026 14:05 Oslo time') !== false, 'with the time in Oslo');
$check(strpos($line, 'password') === false, 'and no word about a password, because there is none to give');

echo "\ncheck-login-attempt: {$passed} passed / {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
