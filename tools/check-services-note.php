<?php
/**
 * Tests for web/services/index.php, the JSON note aisense.no answers when a request for the API
 * reaches the website, and for web/services/.htaccess, which sends every missing path under
 * /services there. The note is loaded from the command line, where its request part does not run.
 *
 * Run from anywhere with: php tools/check-services-note.php
 */

declare(strict_types=1);

$web = dirname(__DIR__) . '/web/services';
require_once $web . '/index.php';

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
$note = function (string $path, bool $hasQuery = false): array {
    [$status, $headers, $body] = services_note_answer($path, $hasQuery);
    return [$status, $headers, $body, json_decode($body, true)];
};

echo "An API path sent to the website\n";
[$status, $headers, $body, $json] = $note('/services/v1/aiq/emi');
$check($status === 404, 'answers 404, as the API does for an unknown endpoint');
$check(is_array($json) && array_keys($json) === ['error', 'fix'], 'with the API error shape, error and fix, and nothing else');
$check(strpos($json['error'], 'aisense.no is the website, not the API') === 0 && strpos($json['error'], 'https://aisenseapi.com') !== false,
    'the error says this is the website and names the API host');
$check(strpos($json['fix'], 'Send the same request to https://aisenseapi.com/services/v1/aiq/emi. ') === 0, 'the fix names the same path on aisenseapi.com');
$check(strpos($json['fix'], 'https://aisense.no/llms.txt') !== false && strpos($json['fix'], 'https://aisense.no/free-public-apis') !== false,
    'and where every endpoint is listed');
$check(($headers['Content-Type'] ?? '') === 'application/json; charset=utf-8' && ($headers['X-Content-Type-Options'] ?? '') === 'nosniff',
    'as JSON that is never sniffed as a page');
$check(($headers['Cache-Control'] ?? '') === 'no-store' && ($headers['X-Robots-Tag'] ?? '') === 'noindex', 'not cached and not indexed');
$check(!isset($headers['Location']), 'and never a redirect');
[, , , $json] = $note('/services/v1/aiq/start/emi');
$check(strpos($json['fix'], 'https://aisenseapi.com/services/v1/aiq/start/emi. ') !== false, 'a start path keeps its whole path');
[, , , $json] = $note('/services/v1/encode/base64/aGVsbG8=');
$check(strpos($json['fix'], 'https://aisenseapi.com/services/v1/encode/base64/aGVsbG8=. ') !== false, 'an argument in the path is kept as sent');

echo "\nPaths that are not an API path\n";
foreach (['/services/', '/services/v1', '/services/v1/', '/services/v2/time', '/services/index.php'] as $path) {
    [$status, , , $json] = $note($path);
    $check($status === 404 && strpos($json['fix'], 'Send the same request') === false
        && strpos($json['fix'], 'https://aisenseapi.com/services/v1/{name}') !== false, $path . ' gets the shape of an endpoint, not a URL to try');
}
[, , $body, $json] = $note('/services/v1/x"><script>alert(1)</script>');
$check(strpos($json['fix'], 'Send the same request') === false && strpos($body, '<') === false, 'markup in the path is never repeated');
[, , , $json] = $note('/services/v1/a b');
$check(strpos($json['fix'], 'Send the same request') === false, 'nor a path with a space');
[, , , $json] = $note('/services/v1/' . str_repeat('a', 401));
$check(strpos($json['fix'], 'Send the same request') === false, 'nor a path longer than any endpoint');

echo "\nThe query\n";
[$path, $hasQuery] = services_note_request(['REQUEST_URI' => '/services/v1/time?key=abc123']);
$check($path === '/services/v1/time' && $hasQuery === true, 'the path is read without its query');
[, , $body, $json] = $note($path, $hasQuery);
$check(strpos($body, 'abc123') === false && strpos($body, 'key=') === false, 'the query is never repeated, as it may carry a key');
$check(substr($json['fix'], -strlen(' Arguments go in the path, not in a query.')) === ' Arguments go in the path, not in a query.', 'the fix says arguments go in the path');
[$path, $hasQuery] = services_note_request(['REQUEST_URI' => '/services/v1/time']);
$check($path === '/services/v1/time' && $hasQuery === false, 'no query, no remark about one');
[$path, $hasQuery] = services_note_request(['REDIRECT_URL' => '/services/v1/time', 'REDIRECT_QUERY_STRING' => 'a=b']);
$check($path === '/services/v1/time' && $hasQuery === true, 'without REQUEST_URI the redirect variables are read');

echo "\nThe files on the web box\n";
$lines = array_values(array_filter(array_map('trim', file($web . '/.htaccess')), function (string $line): bool {
    return $line !== '' && $line[0] !== '#';
}));
$check($lines === ['ErrorDocument 404 /services/index.php', 'ErrorDocument 403 /services/index.php'],
    '.htaccess holds only the two ErrorDocument lines, which AllowOverride FileInfo allows');
$source = (string)file_get_contents($web . '/index.php');
$check(preg_match('/\b(str_contains|str_starts_with|str_ends_with|array_is_list|get_debug_type)\s*\(|\?->|\bmatch\s*\(/', $source) !== 1,
    'index.php uses nothing newer than PHP 7.4, which the web box runs');
$check(strpos($source, 'php://input') === false && strpos($source, '$_POST') === false && strpos($source, 'file_put_contents') === false,
    'and never reads the body or writes a file');

echo "\ncheck-services-note: {$passed} passed / {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
