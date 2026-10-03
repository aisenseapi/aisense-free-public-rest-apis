"""Write the endpoint pages for hex, base64url, URL and HTML encode and decode
into web/, the eight added on 3 October 2026.

The page around the content, from the head to the footer, is taken from
web/free-public-api-dns-name-api-endpoint.html, as make_logic_pages.py does.
Every example answer was worked out with the service's own functions
(libs/func_codec.php in the service repository), so the pages show what the
service answers.

Usage: python make_codec_pages.py <web>
"""
import html
import io
import json
import shlex
import sys
from collections import OrderedDict

WEB = sys.argv[1]
API = 'https://aisenseapi.com/services/v1'
TEMPLATE = io.open(WEB + '/free-public-api-dns-name-api-endpoint.html', encoding='utf-8').read()
B = chr(92)


def pre(text):
    return '<pre><code>' + html.escape(text, quote=False) + '</code></pre>'


def curl(path, data, accept=None):
    lines = ['curl -X POST ' + API + '/' + path + ' ' + B, '  -H "Content-Type: application/json" ' + B]
    if accept:
        lines.append('  -H "Accept: ' + accept + '" ' + B)
    # Quoted for the shell, so any example can be copied and run as it is.
    lines.append('  -d ' + shlex.quote(json.dumps({'data': data}, ensure_ascii=False)))
    return pre('\n'.join(lines))


def answer(value):
    return pre(json.dumps(value, ensure_ascii=False, separators=(',', ':')))


def table(head, rows):
    return ('<div class="table-wrap field-table"><table><thead><tr>' + ''.join('<th>%s</th>' % h for h in head)
            + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>%s</td>' % c for c in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def cards(items):
    return '<div class="use-case-grid">' + ''.join('<article><h3>%s</h3><p>%s</p></article>' % item for item in items) + '</div>'


def related(items):
    return '<div class="related-api-grid">' + ''.join('<a href="%s">%s<span>%s</span></a>' % item for item in items) + '</div>'


def errors(rows):
    return table(['Status', 'error', 'When'], rows)


def privacy(name):
    return ('<section id="privacy"><h2>Privacy and limits</h2><div class="api-note warning-note"><p>Nothing is stored. The '
            + name + ' answer is worked out while the request is open and the data is gone with it. The access log records '
            'the path and the status, not the body.</p></div><p>The base URL is <code>https://aisenseapi.com/services/v1</code>. '
            'There is no key, no account and no sign-up step. One request carries at most 1 MiB of data, and the service-wide '
            'limit is 5000 requests per IP address per day. Every endpoint in the collection is listed on the '
            '<a href="/free-public-apis">Free public REST APIs</a> reference, and the encodings side by side on '
            '<a href="/encoding-apis">Encoding APIs</a>.</p></section>')


INPUT = ('<p>Send the data as <code>{"data": "..."}</code> with <code>Content-Type: application/json</code>, or as the raw '
         'request body with any other content type. The raw body takes binary data as it is: '
         '<code>curl --data-binary @file.bin -H "Content-Type: application/octet-stream"</code>.</p>')

ACCEPT_TABLE = table(['Accept header sent', 'Response'], [
    ['text/plain', '<code>text/plain; charset=utf-8</code>, the decoded text as the whole body'],
    ['application/json', '<code>{"type": "json", "decoded_data": ...}</code> when the bytes are JSON, otherwise '
                         '<code>{"type": "binary", "encoding": "base64", "decoded_data": "..."}</code>'],
    ['application/octet-stream, the wildcard or no header', '<code>application/octet-stream</code>, an attachment named decoded_data.bin'],
    ['anything else', 'HTTP 406 with a fix'],
])

TOO_BIG = ['413', 'Data over 1 MiB.', 'More than 1 MiB in one request']


def page(spec):
    slug = 'free-public-api-' + spec['slug'] + '-api-endpoint'
    out = TEMPLATE
    top, bottom = out[:out.index('<main')], out[out.index('</main>') + len('</main>'):]

    def swap(text, start, end, value):
        i = text.index(start) + len(start)
        j = text.index(end, i)
        return text[:i] + value + text[j:]

    top = swap(top, '<title>', '</title>', html.escape(spec['title'], quote=False))
    top = swap(top, '<meta name="description" content="', '">', html.escape(spec['description']))
    top = swap(top, '<link rel="canonical" href="', '">', 'https://aisense.no/' + slug)
    top = swap(top, '<meta property="og:title" content="', '">', html.escape(spec['h1']))
    top = swap(top, '<meta property="og:description" content="', '">', html.escape(spec['description']))
    top = swap(top, '<meta property="og:url" content="', '">', 'https://aisense.no/' + slug)
    ld = OrderedDict([('@context', 'https://schema.org'), ('@graph', [
        OrderedDict([('@type', 'WebAPI'), ('name', spec['h1']), ('description', spec['description']),
                     ('url', 'https://aisense.no/' + slug), ('documentation', 'https://aisense.no/encoding-apis'),
                     ('provider', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS'), ('url', 'https://aisense.no/')]))]),
        OrderedDict([('@type', 'BreadcrumbList'), ('itemListElement', [
            OrderedDict([('@type', 'ListItem'), ('position', 1), ('name', 'Home'), ('item', 'https://aisense.no/')]),
            OrderedDict([('@type', 'ListItem'), ('position', 2), ('name', 'Free public REST APIs'), ('item', 'https://aisense.no/free-public-apis')]),
            OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', spec['crumb']), ('item', 'https://aisense.no/' + slug)])])])])])
    top = swap(top, '<script type="application/ld+json">\n', '\n</script>', json.dumps(ld, indent=2, ensure_ascii=False))

    sections = spec['sections'] + [privacy(spec['short']), '<section id="related"><h2>Related APIs</h2>' + related(spec['related']) + '</section>']
    toc = spec['toc'] + [('privacy', 'Privacy'), ('related', 'Related')]
    main = ('<main id="main-content" class="api-detail-main">\n'
            '<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/free-public-apis">'
            'Free public REST APIs</a></li><li aria-current="page">' + spec['crumb'] + '</li></ol></nav>\n'
            '<section class="api-detail-hero" aria-labelledby="page-title"><div><p class="eyebrow">Transform - Encoding</p>'
            '<h1 id="page-title">' + spec['h1'] + '</h1><p class="lede">' + spec['lede'] + '</p><ul class="badges">'
            + ''.join('<li>%s</li>' % b for b in spec['badges']) + '</ul></div><div class="endpoint-banner"><p class="endpoint-banner-label">'
            + spec['label'] + '</p><p class="sig"><span class="method post">POST</span><span class="path">/' + spec['path']
            + '</span></p><code>' + API + '/' + spec['path'] + '</code></div></section>\n'
            '<div class="api-doc-layout"><article class="api-doc">\n' + '\n'.join(sections) + '\n'
            '</article><aside class="on-this-page" aria-label="On this page"><p>On this page</p><ul>'
            + ''.join('<li><a href="#%s">%s</a></li>' % item for item in toc) + '</ul></aside></div>\n</main>')
    body = top + main + bottom
    io.open(WEB + '/' + slug + '.html', 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote', slug + '.html', len(body.encode('utf-8')), 'bytes')


PAGES = [
    {
        'slug': 'hex-encode', 'path': 'hex_encode', 'crumb': 'Hex Encode API Endpoint', 'short': 'hex encode',
        'title': 'Free Hex Encode API Endpoint - Bytes to Hexadecimal | AI SENSE',
        'h1': 'Free Hex Encode API Endpoint',
        'description': 'The free hex encode API endpoint turns text or any bytes into lower-case hexadecimal, two digits a byte. One POST, binary safe, no API key.',
        'lede': 'The free hex encode API endpoint turns text or any bytes into lower-case hexadecimal, two digits for every byte. Send the data as JSON or as the raw body, binary included, and read the hex back.',
        'badges': ['No API key', 'Lower-case hex', 'Binary safe', 'One POST request'],
        'label': 'Encode to hex',
        'toc': [('quick-start', 'Quick start'), ('input', 'Input'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free hex encode API endpoint</h2><p>Post the data under a <code>data</code> key:</p>'
            + curl('hex_encode', 'hello') + answer({'hex_encoded_data': '68656c6c6f'})
            + '<p>Every byte becomes two hex digits, so the answer is twice as long as the input. Text is encoded as its UTF-8 bytes: '
              '<code>é</code> is the two bytes <code>c3a9</code>. To go the other way, use the '
              '<a href="/free-public-api-hex-decode-api-endpoint">hex decode API endpoint</a>.</p></section>',
            '<section id="input"><h2>Sending the input</h2>' + INPUT
            + pre('printf ' + "'" + B + 'x00' + B + "xff' | curl -X POST " + API + '/hex_encode ' + B
                  + '\n  -H "Content-Type: application/octet-stream" --data-binary @-')
            + answer({'hex_encoded_data': '00ff'}) + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to encode.', 'No <code>data</code> string and no body'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('See the bytes', 'Show exactly what a payload holds, invisible characters and byte order marks included, before something else misreads it.'),
                ('Keys and digests', 'Hashes, keys and checksums are usually written in hex, so a value in hex can be compared with them as text.'),
                ('Device protocols', 'Build the hex string a serial device, a radio module or a test vector expects from a command written as text.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-hex-decode-api-endpoint', 'Hex Decode API Endpoint', 'Hex back to bytes'),
            ('/free-public-api-base64-encode-api-endpoint', 'Base64 Encode API Endpoint', 'A third shorter than hex'),
            ('/free-public-api-sha256-hash-api-endpoint', 'SHA256 Hash API Endpoint', 'A digest in hex'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'hex-decode', 'path': 'hex_decode', 'crumb': 'Hex Decode API Endpoint', 'short': 'hex decode',
        'title': 'Free Hex Decode API Endpoint - Hexadecimal to Bytes | AI SENSE',
        'h1': 'Free Hex Decode API Endpoint',
        'description': 'The free hex decode API endpoint turns hexadecimal, in either case, with or without 0x, back into bytes, as text, JSON or a download. No API key.',
        'lede': 'The free hex decode API endpoint turns hexadecimal back into the bytes it stands for. Either case works, and so do a leading 0x and spaces. One Accept header decides whether you get text, a typed JSON envelope or the raw bytes.',
        'badges': ['No API key', 'Either case', 'Text, JSON or bytes', 'One POST request'],
        'label': 'Decode hex',
        'toc': [('quick-start', 'Quick start'), ('accept-modes', 'Response shapes'), ('input', 'Input'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free hex decode API endpoint</h2><p>Post the hex under a <code>data</code> key and ask for text:</p>'
            + curl('hex_decode', '68656C6C6F', 'text/plain') + pre('hello')
            + '<p>The other way is the <a href="/free-public-api-hex-encode-api-endpoint">hex encode API endpoint</a>.</p></section>',
            '<section id="accept-modes"><h2>Three response shapes, one Accept header</h2><p>Decoded bytes can be text, JSON or anything else, so the endpoint answers exactly as the '
            '<a href="/free-public-api-base64-decode-api-endpoint">Base64 decode API endpoint</a> does, chosen by the Accept header:</p>' + ACCEPT_TABLE
            + curl('hex_decode', '7b226f6b223a747275657d', 'application/json') + answer({'type': 'json', 'decoded_data': {'ok': True}}) + '</section>',
            '<section id="input"><h2>Sending the input</h2><p>The digits 0-9 and a-f, in either case. A leading <code>0x</code> and spaces, tabs and line breaks '
            'between the digits are allowed, so a hex dump can be pasted as it is. The count of digits has to be even, two for every byte.</p>' + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to decode.', 'No <code>data</code> string and no body'],
                ['400', 'Invalid hex input.', 'An odd count of digits, or a character that is not hex'],
                ['406', 'Unsupported Accept header.', 'An Accept header the endpoint cannot answer'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Read a hex dump', 'Turn the hex a log, a debugger or a packet capture shows back into the text or file it was.'),
                ('Digests and keys as bytes', 'Get the raw bytes of a key or a digest written in hex, to hand on to something that wants bytes.'),
                ('Device payloads', 'Many sensors and radio networks deliver their readings as hex; decode them before parsing.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-hex-encode-api-endpoint', 'Hex Encode API Endpoint', 'Bytes to hex'),
            ('/free-public-api-base64-decode-api-endpoint', 'Base64 Decode API Endpoint', 'The same three shapes for Base64'),
            ('/free-public-api-hash-verify-api-endpoint', 'Hash Verify API Endpoint', 'Check a hex digest'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'base64url-encode', 'path': 'base64url_encode', 'crumb': 'base64url Encode API Endpoint', 'short': 'base64url encode',
        'title': 'Free base64url Encode API Endpoint - URL-Safe Base64 | AI SENSE',
        'h1': 'Free base64url Encode API Endpoint',
        'description': 'The free base64url encode API endpoint writes text or bytes in the URL-safe Base64 alphabet, - and _ with no padding, as JWT uses. No API key.',
        'lede': 'The free base64url encode API endpoint writes text or bytes in base64url, the URL-safe alphabet of RFC 4648 with - and _ in place of + and /, and no = padding. It is the form JWT, OAuth PKCE and WebAuthn use, and it goes into a URL or a file name as it is.',
        'badges': ['No API key', 'URL safe', 'No padding', 'Binary safe'],
        'label': 'Encode to base64url',
        'toc': [('quick-start', 'Quick start'), ('difference', 'base64url and Base64'), ('input', 'Input'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free base64url encode API endpoint</h2>' + curl('base64url_encode', 'hello?')
            + answer({'base64url_encoded_data': 'aGVsbG8_'})
            + '<p>Plain Base64 writes the same bytes as <code>aGVsbG8/</code>. To go back, use the '
              '<a href="/free-public-api-base64url-decode-api-endpoint">base64url decode API endpoint</a>.</p></section>',
            '<section id="difference"><h2>What differs from Base64</h2>' + table(['', 'Base64', 'base64url'], [
                ['Character 62', '<code>+</code>', '<code>-</code>'],
                ['Character 63', '<code>/</code>', '<code>_</code>'],
                ['Padding', '<code>=</code> to a multiple of four', 'none'],
                ['Safe in a URL path or query', 'no, + and / and = need escaping', 'yes'],
            ]) + '<p>Everything else is the same, so the two decode to the same bytes once the two characters are swapped back.</p></section>',
            '<section id="input"><h2>Sending the input</h2>' + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to encode.', 'No <code>data</code> string and no body'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('JWT parts', 'The header and payload of a JWT are base64url JSON. Build or inspect one part at a time.'),
                ('IDs in URLs', 'Put a binary ID, a hash or a token into a path segment or a query value without escaping anything.'),
                ('File names', 'base64url has no slash, so an encoded value can be a file name on any system.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-base64url-decode-api-endpoint', 'base64url Decode API Endpoint', 'Back to bytes'),
            ('/free-public-api-base64-encode-api-endpoint', 'Base64 Encode API Endpoint', 'With + / and padding'),
            ('/free-public-api-jwt-encode-api-endpoint', 'JWT Encode API Endpoint', 'A signed token in one call'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'base64url-decode', 'path': 'base64url_decode', 'crumb': 'base64url Decode API Endpoint', 'short': 'base64url decode',
        'title': 'Free base64url Decode API Endpoint - URL-Safe Base64 to Bytes | AI SENSE',
        'h1': 'Free base64url Decode API Endpoint',
        'description': 'The free base64url decode API endpoint turns URL-safe Base64, with or without padding, back into bytes, as text, JSON or a download. No API key.',
        'lede': 'The free base64url decode API endpoint turns base64url, with or without = padding, back into the bytes it stands for. It answers as the Base64 decode endpoint does: text, a typed JSON envelope or the raw bytes, chosen by the Accept header.',
        'badges': ['No API key', 'With or without padding', 'Text, JSON or bytes', 'One POST request'],
        'label': 'Decode base64url',
        'toc': [('quick-start', 'Quick start'), ('jwt', 'A JWT payload'), ('accept-modes', 'Response shapes'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free base64url decode API endpoint</h2>' + curl('base64url_decode', 'aGVsbG8_', 'text/plain') + pre('hello?')
            + '<p>The other way is the <a href="/free-public-api-base64url-encode-api-endpoint">base64url encode API endpoint</a>.</p></section>',
            '<section id="jwt"><h2>Reading a JWT payload</h2><p>The middle part of a JWT is base64url JSON. Ask for JSON and it comes back parsed:</p>'
            + curl('base64url_decode', 'eyJzdWIiOiIxMjMiLCJuYW1lIjoiQWRhIn0', 'application/json')
            + answer({'type': 'json', 'decoded_data': {'sub': '123', 'name': 'Ada'}})
            + '<p>That reads the claims and checks nothing. To check the signature as well, use the '
              '<a href="/free-public-api-jwt-decode-api-endpoint">JWT decode API endpoint</a>.</p></section>',
            '<section id="accept-modes"><h2>Three response shapes, one Accept header</h2><p>As on the '
            '<a href="/free-public-api-base64-decode-api-endpoint">Base64 decode API endpoint</a>:</p>' + ACCEPT_TABLE + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to decode.', 'No <code>data</code> string and no body'],
                ['400', 'Invalid base64url input.', 'A <code>+</code> or <code>/</code>, which belong to Base64, a space, or a length one past a block of four'],
                ['406', 'Unsupported Accept header.', 'An Accept header the endpoint cannot answer'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>; for <code>+</code> and <code>/</code> it points at <code>/base64_decode</code>.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Inspect a token', 'Read the header or the claims of a JWT, or the client data of a WebAuthn response.'),
                ('IDs from URLs', 'Turn a base64url ID taken from a path or a query value back into its bytes.'),
                ('Check a PKCE challenge', 'Decode a code challenge to the 32 bytes of the SHA-256 digest it carries.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-base64url-encode-api-endpoint', 'base64url Encode API Endpoint', 'Bytes to base64url'),
            ('/free-public-api-jwt-decode-api-endpoint', 'JWT Decode API Endpoint', 'Claims and signature'),
            ('/free-public-api-base64-decode-api-endpoint', 'Base64 Decode API Endpoint', 'With + / and padding'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'url-encode', 'path': 'url_encode', 'crumb': 'URL Encode API Endpoint', 'short': 'URL encode',
        'title': 'Free URL Encode API Endpoint - Percent-Encoding | AI SENSE',
        'h1': 'Free URL Encode API Endpoint',
        'description': 'The free URL encode API endpoint percent-encodes text for a URL path segment or query value, RFC 3986 style, a space as %20. No API key.',
        'lede': 'The free URL encode API endpoint percent-encodes text for one path segment or one query value, the way RFC 3986 says: every byte but A-Z a-z 0-9 - _ . ~ becomes %XX, so a space is %20 and a slash %2F.',
        'badges': ['No API key', 'RFC 3986', 'Space as %20', 'UTF-8'],
        'label': 'Percent-encode',
        'toc': [('quick-start', 'Quick start'), ('what', 'What is encoded'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free URL encode API endpoint</h2>' + curl('url_encode', 'a b/c?é')
            + answer({'url_encoded_data': 'a%20b%2Fc%3F%C3%A9'})
            + '<p>The other way is the <a href="/free-public-api-url-decode-api-endpoint">URL decode API endpoint</a>.</p></section>',
            '<section id="what"><h2>What is encoded</h2>' + table(['In', 'Out', 'Why'], [
                ['a space', '<code>%20</code>', 'not <code>+</code>, which means a space only in HTML form bodies'],
                ['<code>/ ? # &amp; =</code>', '<code>%2F %3F %23 %26 %3D</code>', 'they separate the parts of a URL'],
                ['<code>@</code>', '<code>%40</code>', '<code>ada@example.com</code> becomes <code>ada%40example.com</code>'],
                ['<code>é</code>', '<code>%C3%A9</code>', 'each UTF-8 byte on its own'],
                ['<code>A-Z a-z 0-9 - _ . ~</code>', 'unchanged', 'the unreserved characters'],
            ]) + '<p>Encode each segment or value on its own. Encoding a whole URL turns its own slashes into <code>%2F</code>.</p>' + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to encode.', 'No <code>data</code> string and no body'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Path arguments', 'This API takes its arguments in the path. A value with a space, a slash or an @ in it goes in encoded.'),
                ('Query values', 'Build a query string for another API without a library, one value at a time.'),
                ('Agents building URLs', 'Let an agent hand over the text and get back exactly what the URL needs, instead of guessing the escapes.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-url-decode-api-endpoint', 'URL Decode API Endpoint', 'Percent-encoding to text'),
            ('/free-public-api-slugify-api-endpoint', 'Slugify API Endpoint', 'Text to a readable URL slug'),
            ('/free-public-api-url-shortener-api-endpoint', 'URL Shortener API Endpoint', 'Short links that expire'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'url-decode', 'path': 'url_decode', 'crumb': 'URL Decode API Endpoint', 'short': 'URL decode',
        'title': 'Free URL Decode API Endpoint - Percent-Encoding to Text | AI SENSE',
        'h1': 'Free URL Decode API Endpoint',
        'description': 'The free URL decode API endpoint turns percent-encoding back into UTF-8 text and answers JSON. A + stays a +. No API key.',
        'lede': 'The free URL decode API endpoint turns percent-encoding back into text and answers JSON. A + stays a +, since it means a space only in HTML form bodies, and a broken escape is refused rather than passed on.',
        'badges': ['No API key', 'JSON answer', 'Strict escapes', 'UTF-8'],
        'label': 'Decode percent-encoding',
        'toc': [('quick-start', 'Quick start'), ('rules', 'Rules'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free URL decode API endpoint</h2>' + curl('url_decode', 'a%20b%2Fc+%C3%A9')
            + answer({'url_decoded_data': 'a b/c+é'})
            + '<p>The other way is the <a href="/free-public-api-url-encode-api-endpoint">URL encode API endpoint</a>.</p></section>',
            '<section id="rules"><h2>Rules</h2><ul><li>Every <code>%</code> has to be followed by two hex digits. A literal % is written <code>%25</code>.</li>'
            '<li>A <code>+</code> is left as it is. A query string from an HTML form writes a space as +; replace those before decoding.</li>'
            '<li>The decoded bytes have to be UTF-8 text, since the answer is JSON. For binary data use the '
            '<a href="/free-public-api-hex-decode-api-endpoint">hex</a> or <a href="/free-public-api-base64-decode-api-endpoint">Base64</a> decoder.</li></ul>'
            + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to decode.', 'No <code>data</code> string and no body'],
                ['400', 'Invalid percent-encoding.', 'A <code>%</code> without two hex digits after it'],
                ['400', 'The decoded bytes are not UTF-8 text.', 'Escapes that decode to bytes that are not text'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Read a logged URL', 'Turn a path or query value from an access log back into the text a client sent.'),
                ('Check an encoder', 'Decode what another library produced and compare it with what went in.'),
                ('Agents reading links', 'Give an agent the readable form of a link before it reasons about it.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-url-encode-api-endpoint', 'URL Encode API Endpoint', 'Text to percent-encoding'),
            ('/free-public-api-hex-decode-api-endpoint', 'Hex Decode API Endpoint', 'For bytes that are not text'),
            ('/free-public-api-user-agent-api-endpoint', 'User Agent API Endpoint', 'Echo what a client sends'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'html-encode', 'path': 'html_encode', 'crumb': 'HTML Encode API Endpoint', 'short': 'HTML encode',
        'title': 'Free HTML Encode API Endpoint - Escape Text for HTML | AI SENSE',
        'h1': 'Free HTML Encode API Endpoint',
        'description': 'The free HTML encode API endpoint escapes & < > " and \' as entities, so text can go into a page or an attribute as it is. No API key.',
        'lede': 'The free HTML encode API endpoint escapes the five characters that mean something in HTML, so text can go into a page or an attribute as it is and show as text, markup and all.',
        'badges': ['No API key', 'Five characters', 'Attribute safe', 'UTF-8'],
        'label': 'Escape for HTML',
        'toc': [('quick-start', 'Quick start'), ('what', 'What is escaped'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free HTML encode API endpoint</h2>' + curl('html_encode', '<b>"Tom" & Jerry</b>')
            + answer({'html_encoded_data': '&lt;b&gt;&quot;Tom&quot; &amp; Jerry&lt;/b&gt;'})
            + '<p>The other way is the <a href="/free-public-api-html-decode-api-endpoint">HTML decode API endpoint</a>.</p></section>',
            '<section id="what"><h2>What is escaped</h2>' + table(['In', 'Out'], [
                ['<code>&amp;</code>', '<code>&amp;amp;</code>'], ['<code>&lt;</code>', '<code>&amp;lt;</code>'],
                ['<code>&gt;</code>', '<code>&amp;gt;</code>'], ['<code>"</code>', '<code>&amp;quot;</code>'],
                ['<code>\'</code>', '<code>&amp;#039;</code>'],
            ]) + '<p>Nothing else changes: <code>é</code> stays <code>é</code>, since a page served as UTF-8 shows it as it is. Every <code>&amp;</code> '
            'is escaped, an entity already in the text included, so escape text once, as it goes into the page.</p>' + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to encode.', 'No <code>data</code> string and no body'],
                ['400', 'The data is not UTF-8 text.', 'Bytes that are not text'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Show what people wrote', 'Put a comment, a name or a message into a page so it shows as text and never runs as markup.'),
                ('Attributes', 'Fill a title, alt or value attribute with text that has quotes in it.'),
                ('Reports from agents', 'Let an agent that writes an HTML report escape the values it did not write itself.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-html-decode-api-endpoint', 'HTML Decode API Endpoint', 'Entities back to characters'),
            ('/free-public-api-html-to-pdf-api-endpoint', 'HTML to PDF API Endpoint', 'Render the page to a PDF'),
            ('/free-public-api-url-encode-api-endpoint', 'URL Encode API Endpoint', 'Escapes for a URL'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'html-decode', 'path': 'html_decode', 'crumb': 'HTML Decode API Endpoint', 'short': 'HTML decode',
        'title': 'Free HTML Decode API Endpoint - Entities to Characters | AI SENSE',
        'h1': 'Free HTML Decode API Endpoint',
        'description': 'The free HTML decode API endpoint turns every named HTML5 entity and every numeric one back into its character, and answers JSON. No API key.',
        'lede': 'The free HTML decode API endpoint turns HTML entities back into characters: every named HTML5 entity such as &amp;eacute; or &amp;nbsp;, and every numeric one such as &amp;#233; or &amp;#xE9;. Text that is not an entity stays as it is.',
        'badges': ['No API key', 'Every HTML5 entity', 'Numeric too', 'JSON answer'],
        'label': 'Decode HTML entities',
        'toc': [('quick-start', 'Quick start'), ('what', 'What is decoded'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free HTML decode API endpoint</h2>' + curl('html_decode', '&lt;b&gt; &amp; &eacute; &#233;')
            + answer({'html_decoded_data': '<b> & é é'})
            + '<p>The other way is the <a href="/free-public-api-html-encode-api-endpoint">HTML encode API endpoint</a>.</p></section>',
            '<section id="what"><h2>What is decoded</h2>' + table(['In', 'Out'], [
                ['<code>&amp;lt; &amp;gt; &amp;amp; &amp;quot; &amp;apos;</code>', '<code>&lt; &gt; &amp; " \'</code>'],
                ['<code>caf&amp;eacute; &amp;amp; cr&amp;egrave;me</code>', '<code>café &amp; crème</code>'],
                ['<code>&amp;#233; &amp;#xE9;</code>', '<code>é é</code>'],
                ['<code>&amp;nbsp;</code>', 'a no-break space, U+00A0'],
            ]) + '<p>Markup is not removed: <code>&amp;lt;b&amp;gt;</code> becomes <code>&lt;b&gt;</code>, as text.</p>' + INPUT + '</section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No data to decode.', 'No <code>data</code> string and no body'],
                ['400', 'The data is not UTF-8 text.', 'Bytes that are not text'], TOO_BIG])
            + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p></section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Clean scraped text', 'Turn the entities in text taken from a page back into the characters a reader sees.'),
                ('Feeds and mail', 'RSS titles and email bodies often carry entities; decode them before storing or comparing.'),
                ('Agents reading HTML', 'Give an agent plain characters to reason about instead of escape sequences.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-html-encode-api-endpoint', 'HTML Encode API Endpoint', 'Characters to entities'),
            ('/free-public-api-url-decode-api-endpoint', 'URL Decode API Endpoint', 'Percent-encoding to text'),
            ('/free-public-api-slugify-api-endpoint', 'Slugify API Endpoint', 'Text to a readable URL slug'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
]

for spec in PAGES:
    page(spec)
