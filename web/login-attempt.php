<?php
/**
 * login-attempt.php - tell Admin on Slack when someone uses the client login.
 *
 * There are no client accounts yet. The form on /login stays, and when someone
 * submits it the page posts the email address here, and this sends one line to
 * the private Slack channel: the address and the time. Admin asked for it on
 * 3 October 2026, to see whether anyone uses the form.
 *
 * The password is never sent. The page leaves it out of the request and this
 * file ignores it if it comes: a form that forwarded passwords would collect
 * people's passwords, and many use the same one elsewhere. The page tells the
 * visitor plainly that they were not signed in.
 *
 * The Slack incoming webhook URL is read from /etc/aisense/www-slack-webhook,
 * root owned and readable by the web server, never from this repository. With
 * no such file nothing is sent and the visitor gets the same answer.
 *
 * Limits: one address may report 3 times an hour, and at most 20 lines an hour
 * reach Slack. Past that, and when the hidden field a person cannot see is
 * filled in, the visitor gets the same answer and Slack nothing. A hash of the
 * address and the times are kept for an hour to count, nothing else.
 *
 * Runs on the web box's PHP 7.4: no str_contains, no match, no nullsafe.
 * tools/check-login-attempt.php loads it from the command line, where the
 * request part below does not run, and tests the functions.
 */

declare(strict_types=1);

const LOGIN_ATTEMPT_WEBHOOK_FILE = '/etc/aisense/www-slack-webhook';
const LOGIN_ATTEMPT_PER_ADDRESS = 3;
const LOGIN_ATTEMPT_PER_HOUR = 20;
const LOGIN_ATTEMPT_ORIGINS = ['https://aisense.no', 'https://www.aisense.no'];

/** Whether the request came from a page on this site, by Origin, or Referer when there is none. */
function login_attempt_same_site(array $server): bool
{
    $origin = isset($server['HTTP_ORIGIN']) ? (string) $server['HTTP_ORIGIN'] : '';
    if ($origin !== '') {
        return in_array(rtrim($origin, '/'), LOGIN_ATTEMPT_ORIGINS, true);
    }

    $referer = isset($server['HTTP_REFERER']) ? (string) $server['HTTP_REFERER'] : '';
    foreach (LOGIN_ATTEMPT_ORIGINS as $allowed) {
        if (strpos($referer, $allowed . '/') === 0) {
            return true;
        }
    }

    return false;
}

/** The email address from the request body, or '' when there is no valid one. */
function login_attempt_email(array $input): string
{
    $email = isset($input['email']) && is_string($input['email']) ? trim($input['email']) : '';

    if ($email === '' || strlen($email) > 254 || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
        return '';
    }

    return $email;
}

/**
 * Count one attempt for this address and in total over the last hour, and say
 * whether it may reach Slack. Files that cannot be written count as no limit
 * reached, so a full disk never makes the form stop answering.
 */
function login_attempt_allowed(string $address, string $dir, int $now): bool
{
    if (!is_dir($dir) && !@mkdir($dir, 0700, true) && !is_dir($dir)) {
        return true;
    }

    $allowed = true;
    $files = [
        hash('sha256', 'login-attempt|' . $address) . '.json' => LOGIN_ATTEMPT_PER_ADDRESS,
        'all.json' => LOGIN_ATTEMPT_PER_HOUR,
    ];

    foreach ($files as $name => $limit) {
        $handle = @fopen($dir . '/' . $name, 'c+');
        if ($handle === false) {
            continue;
        }
        if (flock($handle, LOCK_EX)) {
            $times = json_decode((string) stream_get_contents($handle), true);
            $times = array_values(array_filter(is_array($times) ? $times : [], function ($t) use ($now) {
                return is_int($t) && $t > $now - 3600;
            }));
            if (count($times) >= $limit) {
                $allowed = false;
            }
            $times[] = $now;
            rewind($handle);
            ftruncate($handle, 0);
            fwrite($handle, (string) json_encode($times));
            fflush($handle);
            flock($handle, LOCK_UN);
        }
        fclose($handle);
    }

    // An address file left by someone who never comes back is removed by the
    // next visitor once its hour is over.
    foreach ((array) glob($dir . '/*.json') as $file) {
        if (is_string($file) && basename($file) !== 'all.json' && (int) @filemtime($file) < $now - 3600) {
            @unlink($file);
        }
    }

    return $allowed;
}

/** The line Slack shows. Slack reads & < and > as markup, so they are written as entities. */
function login_attempt_message(string $email, DateTimeInterface $when): string
{
    $shown = str_replace(['&', '<', '>'], ['&amp;', '&lt;', '&gt;'], $email);

    return 'Someone used the client login on aisense.no/login: ' . $shown . ', '
        . $when->format('j M Y H:i') . ' Oslo time. No account exists, and they were told so.';
}

/** Post one line to the Slack incoming webhook. False when it could not be sent. */
function login_attempt_slack(string $url, string $text): bool
{
    $payload = (string) json_encode(['text' => $text], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

    if (function_exists('curl_init')) {
        $curl = curl_init($url);
        curl_setopt_array($curl, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $payload,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 5,
        ]);
        $answer = curl_exec($curl);
        $status = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        curl_close($curl);
        return $answer !== false && $status >= 200 && $status < 300;
    }

    $context = stream_context_create(['http' => [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\n",
        'content' => $payload,
        'timeout' => 5,
        'ignore_errors' => true,
    ]]);
    $answer = @file_get_contents($url, false, $context);
    $status = 0;
    if (isset($http_response_header[0]) && preg_match('!^HTTP/\S+\s+(\d{3})!', $http_response_header[0], $m)) {
        $status = (int) $m[1];
    }
    return $answer !== false && $status >= 200 && $status < 300;
}

function login_attempt_send(int $status, array $body): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_SLASHES);
    exit;
}

function login_attempt_main(): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
        header('Allow: POST');
        login_attempt_send(405, ['error' => 'Method not allowed', 'fix' => 'The login form on /login posts here. There is nothing to read.']);
    }

    if (!login_attempt_same_site($_SERVER)) {
        login_attempt_send(403, ['error' => 'Not from this site', 'fix' => 'Use the form on https://aisense.no/login.']);
    }

    $input = json_decode((string) file_get_contents('php://input', false, null, 0, 4096), true);
    $input = is_array($input) ? $input : [];

    $email = login_attempt_email($input);
    if ($email === '') {
        login_attempt_send(400, ['error' => 'Invalid email address', 'fix' => 'Type the email address connected to your AI SENSE account, such as name@company.com.']);
    }

    // The field a person cannot see. Filled in, it was not a person.
    $honeypot = isset($input['website']) && is_string($input['website']) ? trim($input['website']) : '';
    $address = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : '';
    $dir = rtrim(sys_get_temp_dir(), '/') . '/aisense-login-attempts';

    if ($honeypot === '' && login_attempt_allowed($address, $dir, time())) {
        $url = is_readable(LOGIN_ATTEMPT_WEBHOOK_FILE) ? trim((string) file_get_contents(LOGIN_ATTEMPT_WEBHOOK_FILE)) : '';

        if (strpos($url, 'https://hooks.slack.com/') === 0) {
            $text = login_attempt_message($email, new DateTime('now', new DateTimeZone('Europe/Oslo')));
            if (!login_attempt_slack($url, $text)) {
                error_log('login-attempt.php: the Slack webhook did not accept the message');
            }
        } else {
            error_log('login-attempt.php: no Slack webhook in ' . LOGIN_ATTEMPT_WEBHOOK_FILE);
        }
    }

    login_attempt_send(200, ['ok' => true]);
}

if (PHP_SAPI !== 'cli') {
    login_attempt_main();
}
