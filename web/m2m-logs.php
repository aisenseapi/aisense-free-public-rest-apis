<?php
/**
 * Machine access to this site's Apache logs, for the operator dashboard on
 * aisenseapi.com.
 *
 * This file is in a public repository. Everything about how it works is
 * readable by anyone, which is the intended position: the only secret is the
 * token, and a 256 bit token cannot be guessed. Nothing here is defended by
 * being hard to find.
 *
 * Runs on PHP 7.4, which reached end of life in November 2022. Written narrowly
 * on purpose so the whole attack surface fits on one screen:
 *
 *   - Reads. Never writes, deletes, includes or executes anything.
 *   - No shell, no eval, no dynamic include, no unserialize.
 *   - No path ever comes from the caller. A date is validated, converted to a
 *     number, and that number builds the filename.
 *   - Two actions and nothing else. An unknown action is refused, not guessed.
 *
 * No str_contains or str_starts_with anywhere: both arrived in PHP 8.0 and this
 * box does not have them.
 */

header( 'Content-Type: application/json; charset=utf-8' );
header( 'Cache-Control: no-store' );
header( 'X-Content-Type-Options: nosniff' );

/** Log directory. Apache already answers 403 for it, verified 2026-08-27. */
$log_dir = __DIR__ . '/logs';

/**
 * Token file, deliberately outside the document root.
 *
 * Not in the log directory even though that is currently forbidden: relying on
 * one Apache rule to keep a credential secret means a config change silently
 * publishes it. Outside the root there is no rule to get wrong.
 */
$token_file = '/etc/aisense/www-m2m-token';

/** One shape for every answer, so a caller never has to branch on the format. */
function m2m_send( $code, $data, $message = 'ok' ) {
    http_response_code( $code );
    echo json_encode(
        array(
            'status' => array( 'code' => $code, 'message' => $message ),
            'data'   => $data,
        ),
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    );
    exit;
}

// --- authentication ------------------------------------------------------

if ( ! is_file( $token_file ) || ! is_readable( $token_file ) ) {
    // A setup problem, not a caller problem, and saying so saves an hour of
    // sending correct tokens at a server that cannot read its own copy.
    m2m_send( 503, null, 'Token file missing or unreadable on the server.' );
}

$expected = trim( (string) file_get_contents( $token_file ) );

if ( strlen( $expected ) < 32 ) {
    m2m_send( 503, null, 'Token file is too short to be a key.' );
}

/*
 * The token arrives in X-Aisense-Token, not in Authorization.
 *
 * This Apache does not pass Authorization through to PHP. That is the default
 * and not a misconfiguration: the header is dropped unless CGIPassAuth is on or
 * a rewrite rule copies it into the environment. Verified here on 2026-08-27 by
 * sending a known value and printing every $_SERVER key containing "auth", which
 * printed nothing at all.
 *
 * A custom header is passed through untouched, so this needs no change to the
 * server config. That matters on a box running end of life PHP, where the right
 * instinct is to touch as little as possible.
 *
 * Authorization is still read as a fallback, so this keeps working if that
 * config is ever turned on.
 */
$presented = '';

if ( isset( $_SERVER['HTTP_X_AISENSE_TOKEN'] ) ) {
    $presented = trim( (string) $_SERVER['HTTP_X_AISENSE_TOKEN'] );
}

if ( $presented === '' ) {
    $auth = isset( $_SERVER['HTTP_AUTHORIZATION'] ) ? $_SERVER['HTTP_AUTHORIZATION'] : '';

    if ( $auth === '' && isset( $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ) ) {
        $auth = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
    }

    if ( stripos( $auth, 'Bearer ' ) === 0 ) {
        $presented = trim( substr( $auth, 7 ) );
    }
}

/*
 * "No token" and "wrong token" are reported separately.
 *
 * Both were one message until 2026-08-27, and the caller spent a round of
 * debugging on two files that were identical all along while the header was
 * being dropped in front of them. Saying which failed reveals nothing: an
 * attacker already knows whether they sent a header.
 */
if ( $presented === '' ) {
    m2m_send( 401, null, 'No token presented. Send it as the X-Aisense-Token header.' );
}

// hash_equals, not ==, so a wrong token cannot be found one byte at a time.
if ( ! hash_equals( $expected, $presented ) ) {
    m2m_send( 401, null, 'Token does not match the one on this server.' );
}

// --- helpers -------------------------------------------------------------

/**
 * The log file for one date.
 *
 * Apache names each day's file after the Unix timestamp of its start, so
 * ssl-access_log.1787788800 is 2026-08-27. The date is validated first and the
 * filename is then built from an integer, so nothing the caller sends ever
 * reaches the filesystem as text.
 */
function m2m_log_file( $dir, $date, $which ) {
    if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $date ) ) {
        return '';
    }

    $parts = explode( '-', $date );
    $stamp = gmmktime( 0, 0, 0, (int) $parts[1], (int) $parts[2], (int) $parts[0] );

    if ( $stamp === false ) {
        return '';
    }

    $name = $which === 'static' ? 'ssl-static_log.' : 'ssl-access_log.';

    return $dir . '/' . $name . $stamp;
}

/** Last $n lines of a file, read from the end so a large log is never loaded whole. */
function m2m_tail( $file, $n ) {
    if ( ! is_file( $file ) || ! is_readable( $file ) ) {
        return array();
    }

    $fh = @fopen( $file, 'rb' );

    if ( $fh === false ) {
        return array();
    }

    $chunk = 8192;
    $pos   = filesize( $file );
    $buf   = '';
    $found = 0;

    while ( $pos > 0 && $found <= $n ) {
        $read = min( $chunk, $pos );
        $pos -= $read;
        fseek( $fh, $pos );
        $buf   = fread( $fh, $read ) . $buf;
        $found = substr_count( $buf, "\n" );
    }

    fclose( $fh );

    $lines = explode( "\n", $buf );
    $lines = array_values( array_filter( $lines, 'strlen' ) );

    return array_slice( $lines, -$n );
}

// --- actions -------------------------------------------------------------

$action = isset( $_GET['action'] ) ? (string) $_GET['action'] : 'status';

/*
 * status: which days exist, how big they are, and what the server thinks the
 * time is. The clock matters because these logs are stamped in local time with
 * an offset while the API box logs UTC, and a dashboard that merges the two
 * without knowing that is wrong by two hours for half the year.
 */
if ( $action === 'status' ) {
    $days = array();

    foreach ( glob( $log_dir . '/ssl-access_log.*' ) as $path ) {
        $stamp = (int) substr( $path, strrpos( $path, '.' ) + 1 );

        if ( $stamp > 0 ) {
            $days[ gmdate( 'Y-m-d', $stamp ) ] = filesize( $path );
        }
    }

    ksort( $days );

    m2m_send( 200, array(
        'host'          => 'aisense.no',
        'log_dir_found' => is_dir( $log_dir ),
        'days'          => $days,
        'day_count'     => count( $days ),
        'server_time'   => date( 'c' ),
        'server_utc'    => gmdate( 'c' ),
        'log_timezone'  => date( 'P' ),
        'php_version'   => PHP_VERSION,
    ) );
}

/*
 * logs: the tail of one day. Raw lines rather than aggregates, because the
 * parser already lives on the API box and one parser is easier to keep correct
 * than two that must agree.
 */
if ( $action === 'logs' ) {
    $date  = isset( $_GET['date'] ) ? (string) $_GET['date'] : gmdate( 'Y-m-d' );
    $which = ( isset( $_GET['which'] ) && $_GET['which'] === 'static' ) ? 'static' : 'access';
    $lines = isset( $_GET['lines'] ) ? (int) $_GET['lines'] : 500;
    $lines = max( 1, min( 5000, $lines ) );

    $file = m2m_log_file( $log_dir, $date, $which );

    if ( $file === '' ) {
        m2m_send( 400, null, 'Date must be YYYY-MM-DD.' );
    }

    $rows = m2m_tail( $file, $lines );

    m2m_send( 200, array(
        'date'      => $date,
        'which'     => $which,
        'file'      => basename( $file ),
        'file_found'=> is_file( $file ),
        'readable'  => is_file( $file ) && is_readable( $file ),
        'returned'  => count( $rows ),
        'requested' => $lines,
        'lines'     => $rows,
    ) );
}

m2m_send( 400, null, 'Unknown action. Known actions: status, logs.' );
