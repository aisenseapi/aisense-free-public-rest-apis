<?php
/**
 * aisense.no is the website; the API answers at aisenseapi.com. A request for an API path sent
 * here gets a 404 with the JSON shape of the API's own errors, error and fix, naming the URL to use
 * instead. services/.htaccess brings every missing path under /services to this file, and a request
 * for /services/ itself lands here as the index.
 *
 * Nothing is redirected: the API keeps one address per endpoint. The request body is never read,
 * and the query is never repeated, as it may carry a key. Whether a name exists is for the API to
 * say; it answers an unknown endpoint with where the list is.
 *
 * Tested by tools/check-services-note.php, which loads this file from the command line, where the
 * request part does not run.
 */

declare(strict_types=1);

/** The answer for one request path: [status, headers, body]. */
function services_note_answer(string $path, bool $hasQuery): array
{
    $lists = 'https://aisense.no/llms.txt and https://aisense.no/free-public-apis list every endpoint.';
    $shape = 'Every endpoint is https://aisenseapi.com/services/v1/{name}, with its arguments in the path. ';
    if (preg_match('#^/services/v1/[A-Za-z0-9._~%/:@+,;=-]{1,400}$#D', $path) === 1) {
        $fix = 'Send the same request to https://aisenseapi.com' . $path . '. ' . $shape . $lists;
    } else {
        $fix = $shape . $lists;
    }
    if ($hasQuery) {
        $fix .= ' Arguments go in the path, not in a query.';
    }
    $body = json_encode(
        ['error' => 'aisense.no is the website, not the API. The API answers at https://aisenseapi.com.', 'fix' => $fix],
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
    );
    return [404, [
        'Content-Type' => 'application/json; charset=utf-8',
        'Cache-Control' => 'no-store',
        'X-Content-Type-Options' => 'nosniff',
        'X-Robots-Tag' => 'noindex',
        'Access-Control-Allow-Origin' => '*',
    ], $body];
}

/** The path and whether a query came with it, from REQUEST_URI, which keeps the request as sent after an ErrorDocument. */
function services_note_request(array $server): array
{
    $uri = (string)($server['REQUEST_URI'] ?? '');
    if ($uri === '') {
        return [(string)($server['REDIRECT_URL'] ?? '/'), (string)($server['REDIRECT_QUERY_STRING'] ?? '') !== ''];
    }
    $parts = explode('?', $uri, 2);
    return [$parts[0], count($parts) === 2];
}

if (PHP_SAPI !== 'cli') {
    [$path, $hasQuery] = services_note_request($_SERVER);
    [$status, $headers, $body] = services_note_answer($path, $hasQuery);
    http_response_code($status);
    foreach ($headers as $name => $value) {
        header($name . ': ' . $value);
    }
    echo $body;
}
