<?php
/**
 * login-attempt.php - tell Admin on Slack when someone uses the client login.
 *
 * There are no client accounts yet. The form on /login stays, and when someone
 * submits it the email address comes here, and this sends one line to the
 * private Slack channel: the address and the time. Admin asked for it on
 * 3 October 2026, to see whether anyone uses the form.
 *
 * The password is never sent. Its field on the page has no name, so no form
 * submission can carry it, with or without JavaScript; the page's script
 * clears it as well, and this file ignores a password field if one comes.
 * A form that forwarded passwords would collect people's passwords, and many
 * use the same one elsewhere. The visitor is told plainly that they were not
 * signed in.
 *
 * The page's script posts JSON and gets JSON back. Without JavaScript the
 * browser posts the form itself, and gets a short HTML page with the same
 * answer.
 *
 * The line goes to Slack through /usr/local/bin/slack_alert, the same writer
 * the API box's alerts use, with the whole message as its one argument. It is
 * started without a shell, so nothing in an address can become a command, and
 * stopped after 5 seconds. Without it, or when it fails, the visitor gets the
 * same answer and the web server's error log says why.
 *
 * Limits: one address may report 3 times an hour, and at most 20 lines an hour
 * reach Slack. Past that, when the hidden field a person cannot see is filled
 * in, and when the counters cannot be read or written, the visitor gets the
 * same answer and Slack nothing: a limit that cannot be checked is treated as
 * reached. A hash of the address and the times are kept for an hour to count,
 * nothing else.
 *
 * Runs on the web box's PHP 7.4: no str_contains, no match, no nullsafe.
 * tools/check-login-attempt.php loads it from the command line, where the
 * request part below does not run, and tests the functions.
 */

declare(strict_types=1);

const LOGIN_ATTEMPT_SLACK = '/usr/local/bin/slack_alert';
const LOGIN_ATTEMPT_TIMEOUT = '/usr/bin/timeout';
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

/**
 * What the request carried: the email address and the hidden field, from a
 * JSON body or from a form post, and whether it was a form post. Nothing else
 * is taken, a password field included.
 */
function login_attempt_input(string $content_type, string $raw, array $post): array
{
    $form = stripos($content_type, 'application/json') === false;
    $source = $form ? $post : json_decode($raw, true);
    $source = is_array($source) ? $source : [];

    return [
        'email' => isset($source['email']) && is_string($source['email']) ? $source['email'] : '',
        'website' => isset($source['website']) && is_string($source['website']) ? $source['website'] : '',
        'form' => $form,
    ];
}

/** The email address, or '' when there is no valid one. */
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
 * whether it may reach Slack. When the counters cannot be read or written the
 * answer is no, so a broken disk cannot be used to flood Slack; the visitor's
 * answer does not depend on it.
 */
function login_attempt_allowed(string $address, string $dir, int $now): bool
{
    if (!is_dir($dir) && !@mkdir($dir, 0700, true) && !is_dir($dir)) {
        return false;
    }

    $allowed = true;
    $files = [
        hash('sha256', 'login-attempt|' . $address) . '.json' => LOGIN_ATTEMPT_PER_ADDRESS,
        'all.json' => LOGIN_ATTEMPT_PER_HOUR,
    ];

    foreach ($files as $name => $limit) {
        $handle = @fopen($dir . '/' . $name, 'c+');
        if ($handle === false) {
            return false;
        }
        if (!flock($handle, LOCK_EX)) {
            fclose($handle);
            return false;
        }
        $times = json_decode((string) stream_get_contents($handle), true);
        $times = array_values(array_filter(is_array($times) ? $times : [], function ($t) use ($now) {
            return is_int($t) && $t > $now - 3600;
        }));
        if (count($times) >= $limit) {
            $allowed = false;
        }
        $times[] = $now;
        $data = (string) json_encode($times);
        $written = rewind($handle) && ftruncate($handle, 0) && fwrite($handle, $data) === strlen($data) && fflush($handle);
        flock($handle, LOCK_UN);
        fclose($handle);
        if (!$written) {
            return false;
        }
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

/**
 * Hand one line to slack_alert. The command and the message are separate
 * arguments to the program itself, with no shell between, and timeout stops
 * it after 5 seconds where timeout exists. Returns '' when it was sent, or why
 * it was not. $command is the program and any arguments before the message;
 * the test passes a stand-in.
 */
function login_attempt_slack(string $text, array $command = [LOGIN_ATTEMPT_SLACK]): string
{
    if (!function_exists('proc_open')) {
        return 'proc_open is not available to PHP here';
    }
    if (count($command) === 1 && !is_executable($command[0])) {
        return $command[0] . ' is not there or not executable for the web server';
    }

    $argv = array_merge(is_executable(LOGIN_ATTEMPT_TIMEOUT) ? [LOGIN_ATTEMPT_TIMEOUT, '5'] : [], $command, [$text]);
    $null = DIRECTORY_SEPARATOR === '\\' ? 'NUL' : '/dev/null';
    $process = @proc_open($argv, [0 => ['file', $null, 'r'], 1 => ['file', $null, 'w'], 2 => ['pipe', 'w']], $pipes);
    if (!is_resource($process)) {
        return 'it could not be started';
    }

    $errors = trim((string) stream_get_contents($pipes[2], 500));
    fclose($pipes[2]);
    $code = proc_close($process);

    return $code === 0 ? '' : 'it exited with ' . $code . ($errors === '' ? '' : ': ' . $errors);
}

/** The short HTML page a browser without JavaScript shows after posting the form. */
function login_attempt_page(string $title, string $text): string
{
    $title = htmlspecialchars($title, ENT_QUOTES, 'UTF-8');
    $text = htmlspecialchars($text, ENT_QUOTES, 'UTF-8');

    return '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        . '<meta name="robots" content="noindex"><title>' . $title . ' - AI SENSE</title><link rel="stylesheet" href="/assets/aisense.css"></head>'
        . '<body class="login-page"><main id="main-content" class="login-main"><section class="login-shell"><div class="login-intro">'
        . '<p class="eyebrow">AI SENSE client portal</p><h1>' . $title . '</h1><p class="lede">' . $text . '</p>'
        . '<p><a href="/login">Back to the login page</a>, or write to <a href="mailto:support@aisense.no">support@aisense.no</a>.</p>'
        . '</div></section></main></body></html>';
}

function login_attempt_send(int $status, array $body, bool $form): void
{
    http_response_code($status);
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');

    if ($form) {
        header('Content-Type: text/html; charset=utf-8');
        echo $status === 200
            ? login_attempt_page('Client accounts are not open yet', 'You are not signed in. We received the email address you typed, never the password, and may contact you about access.')
            : login_attempt_page('You are not signed in', (string) $body['fix']);
        exit;
    }

    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($body, JSON_UNESCAPED_SLASHES);
    exit;
}

function login_attempt_main(): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
        header('Allow: POST');
        login_attempt_send(405, ['error' => 'Method not allowed', 'fix' => 'The login form on /login posts here. There is nothing to read.'], false);
    }

    $input = login_attempt_input(
        isset($_SERVER['CONTENT_TYPE']) ? (string) $_SERVER['CONTENT_TYPE'] : '',
        (string) file_get_contents('php://input', false, null, 0, 4096),
        $_POST
    );

    if (!login_attempt_same_site($_SERVER)) {
        login_attempt_send(403, ['error' => 'Not from this site', 'fix' => 'Use the form on https://aisense.no/login.'], $input['form']);
    }

    $email = login_attempt_email($input);
    if ($email === '') {
        login_attempt_send(400, ['error' => 'Invalid email address', 'fix' => 'Type the email address connected to your AI SENSE account, such as name@company.com.'], $input['form']);
    }

    // The field a person cannot see. Filled in, it was not a person.
    $honeypot = trim($input['website']);
    $address = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : '';
    $dir = rtrim(sys_get_temp_dir(), '/') . '/aisense-login-attempts';

    if ($honeypot === '' && login_attempt_allowed($address, $dir, time())) {
        $failed = login_attempt_slack(login_attempt_message($email, new DateTime('now', new DateTimeZone('Europe/Oslo'))));
        if ($failed !== '') {
            error_log('login-attempt.php: nothing reached Slack, because ' . $failed);
        }
    }

    login_attempt_send(200, ['ok' => true], $input['form']);
}

if (PHP_SAPI !== 'cli') {
    login_attempt_main();
}
