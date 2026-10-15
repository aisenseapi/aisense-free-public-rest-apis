"""Write the Try box into the endpoint pages listed in TRY.

Each page gets a section right after its quick start, its line under On this page, the stylesheet
assets/aisense-try.css after the theme script in the head, and the script assets/aisense-try.js after
main, which says how the box works. The box sends the request of the page's quick start from the
visitor's browser. Search traffic lands on the endpoint pages themselves, so the box sits there, high on
the page, and not on a page of its own (Admin, 15 October 2026).

Every run writes each box whole, so this file is the one place a box is defined, and a page that leaves
TRY loses its box at the next run. build.py runs this after the page generators, since some of these
pages are theirs, and before site_nav.py. A run with nothing changed changes nothing.

Python 3, standard library only:

    python tools/pages/make_try_boxes.py [web dir]
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(HERE)), 'web')
NL = chr(10)
MIB = 1048576

# Change this whenever aisense-try.css or aisense-try.js changes: they are served with no Cache-Control.
TRY_VERSION = '20261015f'
CSS_START = '<link rel="stylesheet" href="/assets/aisense-try.css?v='
CSS_TAG = CSS_START + TRY_VERSION + '">'
JS_START = '<script src="/assets/aisense-try.js?v='
JS_TAG = JS_START + TRY_VERSION + '" defer></script>'
THEME_START = '<script src="/assets/aisense-theme.js?v='

ACCEPT_TEXT = ('text/plain', 'Text (Accept: text/plain)')
ACCEPT_JSON = ('application/json', 'JSON envelope (Accept: application/json)')
ACCEPT_BYTES = ('application/octet-stream', 'Bytes as a file (Accept: application/octet-stream)')
THREE = [ACCEPT_TEXT, ACCEPT_JSON, ACCEPT_BYTES]
# base32_decode and base58_decode have no text mode: any Accept but JSON gets the bytes.
TWO = [ACCEPT_BYTES, ACCEPT_JSON]

LEAVE_OUT = 'Leave secrets and personal data out.'


def limit_text(n):
    if n % MIB == 0:
        return '%d MiB' % (n // MIB)
    return '%d KiB' % (n // 1024) if n % 1024 == 0 else '%d bytes' % n


def encoder(endpoint, sample, file=True, limit=MIB):
    if file:
        intro = 'Encode text or a file here. Your browser sends the text in a JSON body, as the quick start does, and a file as the raw body.'
    else:
        intro = 'Encode text here, up to %s. Your browser sends it in a JSON body, as the quick start does.' % limit_text(limit)
    return {'endpoint': endpoint, 'label': 'Text', 'sample': sample, 'button': 'Encode', 'busy': 'Encoding',
            'file': 'raw' if file else None, 'chars': True, 'limit': limit, 'intro': intro + ' ' + LEAVE_OUT}


def hasher(endpoint, verb='Hash', busy='Hashing'):
    intro = ('%s text or a file here. Your browser sends the text in a JSON body, as the quick start does, '
             'and a file as a multipart upload.' % verb)
    return {'endpoint': endpoint, 'label': 'Text', 'sample': 'Hello world', 'button': verb, 'busy': busy,
            'file': 'multipart', 'limit': MIB, 'intro': intro + ' ' + LEAVE_OUT}


def decoder(endpoint, label, sample, accept=THREE, limit=MIB):
    upto = '' if limit == MIB else ', up to %s' % limit_text(limit)
    intro = ('Decode a string here%s. Your browser sends it in a JSON body, as the quick start does, with the Accept header you pick. '
             'Bytes as a file shows them as text when they read as text and as hex otherwise, and lets you save them.' % upto)
    return {'endpoint': endpoint, 'label': label, 'sample': sample, 'button': 'Decode', 'busy': 'Decoding',
            'accept': accept, 'limit': limit, 'intro': intro + ' ' + LEAVE_OUT}


def text(endpoint, verb, busy, label, sample, limit=MIB, intro=None):
    return {'endpoint': endpoint, 'label': label, 'sample': sample, 'button': verb, 'busy': busy, 'limit': limit,
            'intro': intro or '%s text here. Your browser sends it in a JSON body, as the quick start does. %s' % (verb, LEAVE_OUT)}


# The types of /services/v1/validate/{type} the box offers, each with a value that passes. card is left out:
# a box on a public page should not invite card numbers.
VALIDATE_TYPES = [
    ('iban', 'IBAN', 'NO9386011117947'),
    ('orgnr', 'Organisasjonsnummer (orgnr)', '923609016'),
    ('kontonummer', 'Kontonummer', '86011117947'),
    ('phone', 'Phone number (E.164 shape)', '+47 22 12 34 56'),
]


def validator():
    return {'endpoint': 'validate', 'paths': VALIDATE_TYPES, 'label': 'Value', 'sample': VALIDATE_TYPES[0][2],
            'button': 'Check', 'busy': 'Checking', 'limit': 4096,
            'intro': 'Pick a type and check a value here. Your browser sends it in a JSON body to the path of the type, '
                     'as the quick start does. ' + LEAVE_OUT}


def qr_encoder():
    return {'endpoint': 'qrcode_encode', 'key': 'payload', 'image': 'qrcode_image', 'save': 'qrcode.png',
            'label': 'Text', 'sample': 'https://aisense.no/free-public-apis', 'button': 'Make the code', 'busy': 'Making the code',
            'limit': 1800,
            'intro': 'Make a QR code here, from up to 1800 bytes of text. Your browser sends the text in a JSON field named '
                     'payload, as the quick start does, and draws the PNG that comes back. ' + LEAVE_OUT}


def getter(endpoint, args=None, label=None, button='Send', busy='Calling', intro=None):
    """A one-click GET: the request of the quick start, with the arguments that follow the endpoint editable."""
    spec = {'endpoint': endpoint, 'method': 'GET', 'button': button, 'busy': busy, 'limit': 1024}
    if args is None:
        spec['intro'] = intro or 'Call it here. Your browser sends the GET request of the quick start and shows the answer.'
    else:
        spec['args'] = args
        spec['args_label'] = label
        spec['intro'] = intro or ('Call it here. Your browser sends the GET request of the quick start; change the %s in '
                                  'the path to try others.' % label.lower())
    return spec


def qr_decoder():
    return {'endpoint': 'qrcode_decode', 'file': 'multipart', 'field': 'qrcode_image', 'sample_file': '/assets/aisense-try-qr.png',
            'drop': 'Drop a QR image here', 'button': 'Read the sample code', 'busy': 'Reading', 'limit': 8 * MIB,
            'intro': 'Read a QR code here: drop a PNG, JPEG, GIF or WebP image, or read the sample code, which holds '
                     'https://aisense.no/free-public-apis. Your browser uploads the image as a form field named qrcode_image. ' + LEAVE_OUT}


TRY = {
    'free-public-api-base64-encode-api-endpoint.html': encoder('base64_encode', 'Hello world'),
    'free-public-api-base64-decode-api-endpoint.html': decoder('base64_decode', 'Base64', 'SGVsbG8gd29ybGQ='),
    'free-public-api-base64url-encode-api-endpoint.html': encoder('base64url_encode', 'hello?'),
    'free-public-api-base64url-decode-api-endpoint.html': decoder('base64url_decode', 'base64url', 'aGVsbG8_'),
    'free-public-api-base32-encode-api-endpoint.html': encoder('base32_encode', 'Hello world'),
    'free-public-api-base32-decode-api-endpoint.html': decoder('base32_decode', 'Base32', 'JBSWY3DPEB3W64TMMQ======', accept=TWO),
    # Base58 takes at most 64 KiB in one request (its work grows faster than the input), so its boxes stop there.
    'free-public-api-base58-encode-api-endpoint.html': encoder('base58_encode', 'Hello world', limit=64 * 1024),
    'free-public-api-base58-decode-api-endpoint.html': decoder('base58_decode', 'Base58', 'JxF12TrwXzT5jvT', accept=TWO, limit=64 * 1024),
    'free-public-api-hex-encode-api-endpoint.html': encoder('hex_encode', 'hello'),
    'free-public-api-hex-decode-api-endpoint.html': decoder('hex_decode', 'Hex', '68656C6C6F'),
    'free-public-api-url-encode-api-endpoint.html': text('url_encode', 'Encode', 'Encoding', 'Text', 'a b/c?é'),
    'free-public-api-url-decode-api-endpoint.html': text('url_decode', 'Decode', 'Decoding', 'Encoded text', 'a%20b%2Fc+%C3%A9'),
    'free-public-api-html-encode-api-endpoint.html': text('html_encode', 'Encode', 'Encoding', 'Text', '<b>"Tom" & Jerry</b>'),
    'free-public-api-html-decode-api-endpoint.html': text('html_decode', 'Decode', 'Decoding', 'HTML', '&lt;b&gt; &amp; &eacute; &#233;'),
    # The hashes take JSON data, text/plain or a multipart file named file; the box sends text as JSON and a file
    # as multipart, up to 1 MiB, which is also BLAKE3's own limit.
    'free-public-api-md5-hash-api-endpoint.html': hasher('md5_hash'),
    'free-public-api-sha1-hash-api-endpoint.html': hasher('sha1_hash'),
    'free-public-api-sha256-hash-api-endpoint.html': hasher('sha256_hash'),
    'free-public-api-sha512-hash-api-endpoint.html': hasher('sha512_hash'),
    'free-public-api-sha3-256-hash-api-endpoint.html': hasher('sha3_256_hash'),
    'free-public-api-sha3-512-hash-api-endpoint.html': hasher('sha3_512_hash'),
    'free-public-api-blake2b-hash-api-endpoint.html': hasher('blake2b_hash'),
    'free-public-api-blake3-hash-api-endpoint.html': hasher('blake3_hash'),
    'free-public-api-whirlpool-hash-api-endpoint.html': hasher('whirlpool_hash'),
    'free-public-api-crc32-checksum-api-endpoint.html': hasher('crc32_checksum', 'Checksum', 'Computing'),
    # Text and values. Every JSON body stops at 256 KiB, HTML to Markdown at 1 MiB.
    'free-public-api-slugify-api-endpoint.html': text('slugify', 'Slugify', 'Slugifying', 'Text', 'Blåbærsyltetøy på Ås!', limit=256 * 1024),
    'free-public-api-html-to-markdown-api-endpoint.html': text(
        'html_to_markdown', 'Convert', 'Converting', 'HTML',
        '<title>Release notes</title><h1>Version 2</h1><p>Now with <b>tables</b> and <a href="https://aisense.no">links</a>.</p><script>track()</script>',
        intro='Convert HTML to Markdown here. Your browser sends it in a JSON body, as the quick start does. ' + LEAVE_OUT),
    'free-public-api-markdown-to-html-api-endpoint.html': text(
        'markdown_to_html', 'Convert', 'Converting', 'Markdown',
        NL.join(['# Report', '', '- **3** jobs done', '- [ ] one left', '', '| Job | Time |', '|---|--:|', '| sync | 2.1 s |']),
        limit=256 * 1024, intro='Convert Markdown to HTML here. Your browser sends it in a JSON body, as the quick start does. ' + LEAVE_OUT),
    'free-public-api-timestamp-convert-api-endpoint.html': text(
        'timestamp_convert', 'Convert', 'Converting', 'Date, time or Unix timestamp', '2026-08-19T20:28:10+00:00', limit=1024,
        intro='Convert a date, a time or a Unix timestamp in seconds or milliseconds here. Your browser sends it in a JSON body, as the quick start does.'),
    'free-public-api-validate-api-endpoint.html': validator(),
    'free-public-api-email-validate-api-endpoint.html': text(
        'email_validate', 'Check', 'Checking', 'Address', 'test@gmail.com', limit=1024,
        intro='Check an address here: its syntax, and the mail servers its domain publishes. Your browser sends it in a '
              'JSON body, as the quick start does. Use a test address, or one you are free to share.'),
    'free-public-api-qr-code-encode-api-endpoint.html': qr_encoder(),
    'free-public-api-qr-code-decode-api-endpoint.html': qr_decoder(),
    # One-click GETs. Left out: what makes an object or a public link (inbox, DNS names, short links, PDF to
    # storage), what makes a secret others could use (the wallet generators), the crypto balances for now, and
    # mock_response, which has a box of its own.
    'free-public-api-uuid-api-endpoint.html': getter('uuid', button='Make a UUID', busy='Making'),
    'free-public-api-guid-api-endpoint.html': getter('guid', button='Make a GUID', busy='Making'),
    'free-public-api-password-api-endpoint.html': getter('password', '20', 'Length', button='Make a password', busy='Making'),
    'free-public-api-passphrase-api-endpoint.html': getter('passphrase', '4', 'Groups', button='Make a passphrase', busy='Making'),
    'free-public-api-random-number-api-endpoint.html': getter('random_number', '1/100', 'From and to', button='Draw', busy='Drawing'),
    'free-public-api-random-color-api-endpoint.html': getter('random_color', button='Draw a color', busy='Drawing'),
    'free-public-api-datetime-api-endpoint.html': getter(
        'datetime', '', 'Time zone or offset (optional)', button='Ask', busy='Asking',
        intro='Call it here. Your browser sends the GET request of the quick start, which answers in UTC; put a time '
              'zone such as europe/oslo, or an offset such as +0200, in the path to ask for another.'),
    'free-public-api-timestamp-api-endpoint.html': getter('timestamp', button='Ask', busy='Asking'),
    'free-public-api-microtimestamp-api-endpoint.html': getter('microtimestamp', button='Ask', busy='Asking'),
    'free-public-api-swatchinternettime-api-endpoint.html': getter('swatchinternettime', button='Ask', busy='Asking'),
    'free-public-api-timezones-api-endpoint.html': getter('timezones', button='List the time zones', busy='Listing'),
    'free-public-api-client-ip-api-endpoint.html': getter('client_ip', button='Show my IP', busy='Asking'),
    'free-public-api-user-agent-api-endpoint.html': getter('user_agent', button='Show my user agent', busy='Asking'),
    'free-public-api-ip-datetime-api-endpoint.html': getter('ip_datetime', '8.8.8.8', 'IP address', button='Look up', busy='Looking up'),
    'free-public-api-domain-ip-lookup-api-endpoint.html': getter('domain_ip_lookup', 'example.com', 'Domain', button='Look up', busy='Looking up'),
    'free-public-api-ip-reverse-lookup-api-endpoint.html': getter('ip_reverse_lookup', '8.8.8.8', 'IP address', button='Look up', busy='Looking up'),
    'free-public-api-health-api-endpoint.html': getter('health', button='Check', busy='Checking'),
    'free-public-api-ping-api-endpoint.html': getter('ping', button='Ping', busy='Pinging'),
}


def esc(value):
    return html.escape(value, quote=False)


def attr(value):
    return html.escape(value, quote=True)


def section(spec):
    data = [('data-try-endpoint', spec['endpoint']), ('data-try-limit', '%d' % spec['limit']), ('data-try-busy', spec['busy'])]
    for name, key in (('data-try-key', 'key'), ('data-try-file', 'file'), ('data-try-field', 'field'),
                      ('data-try-image', 'image'), ('data-try-sample', 'sample_file'), ('data-try-method', 'method')):
        if spec.get(key):
            data.append((name, spec[key]))
    parts = ['<section id="try"><h2>Try it</h2><p>%s</p>' % esc(spec['intro']),
             '<div class="try-card try-api" %s%s>' % (' '.join('%s="%s"' % (name, attr(value)) for name, value in data),
                                                     ' data-try-chars' if spec.get('chars') else '')]
    if spec.get('paths'):
        parts.append('<label for="try-path">Type</label><select id="try-path" class="try-path">'
                     + ''.join('<option value="%s" data-sample="%s">%s</option>' % (attr(value), attr(sample), esc(label))
                               for value, label, sample in spec['paths']) + '</select>')
    if 'sample' in spec:
        parts.append('<label for="try-input">%s</label><textarea id="try-input" class="try-input" rows="4" spellcheck="false">%s</textarea>'
                     % (esc(spec['label']), esc(spec['sample'])))
    if 'args' in spec:
        parts.append('<label for="try-args">%s</label><div class="try-url"><code>https://aisenseapi.com/services/v1/%s/</code>'
                     '<input id="try-args" class="try-args" type="text" value="%s" spellcheck="false" autocomplete="off"></div>'
                     % (esc(spec['args_label']), esc(spec['endpoint']), attr(spec['args'])))
    if spec.get('file'):
        parts.append('<div class="try-drop" role="button" tabindex="0"><strong>%s</strong> <small>or click to choose one, up to %s</small></div>'
                     '<input type="file" class="try-file" hidden>' % (esc(spec.get('drop', 'Or drop a file here')), limit_text(spec['limit'])))
    if spec.get('accept'):
        parts.append('<label for="try-accept">Answer as</label><select id="try-accept" class="try-accept">'
                     + ''.join('<option value="%s">%s</option>' % option for option in spec['accept']) + '</select>')
    parts.append('<div class="button-row"><button type="button" class="button button-primary try-run">%s</button></div>' % spec['button'])
    parts.append('<p class="try-status" aria-live="polite"></p>')
    if spec.get('image'):
        parts.append('<div class="try-image" hidden><img alt="The image the API answered with"></div>')
    parts.append('<pre class="try-result" hidden><code class="try-out"></code></pre>')
    if ACCEPT_BYTES in spec.get('accept', []) or spec.get('save'):
        name = spec.get('save', 'decoded_data.bin')
        parts.append('<p class="try-save" hidden><a class="button button-secondary try-save-link" href="#" download="%s">Save %s</a></p>' % (attr(name), esc(name)))
    parts.append('</div></section>')
    return ''.join(parts)


def cut(text, start_marker, end_marker, with_newline_before=False):
    """Text without the span from start_marker through end_marker and the newline after it; unchanged when absent."""
    start = text.find(start_marker)
    if start == -1:
        return text
    end = text.index(end_marker, start) + len(end_marker)
    if with_newline_before and start > 0 and text[start - 1] == NL:
        start -= 1
    elif end < len(text) and text[end] == NL:
        end += 1
    return text[:start] + text[end:]


def strip(text):
    """The page without its Try box, as this script writes it, and without the first Base64 boxes of the same day."""
    text = cut(text, CSS_START, '>')
    text = cut(text, '<style>' + NL + '.try-api textarea', '</style>')
    text = cut(text, '<section id="try">', '</div></section>', with_newline_before=True)
    text = text.replace('<li><a href="#try">Try it</a></li>', '')
    text = cut(text, JS_START, '</script>')
    for prefix in ('b64d', 'b64e'):
        text = cut(text, '<script>' + NL + '(function () {' + NL + "  var input = document.getElementById('" + prefix + "-input');", '</script>')
    return text


def add(text, spec, name):
    theme = text.index(THEME_START)
    theme_end = text.index('</script>', theme) + len('</script>')
    if text[theme_end] == NL:
        text = text[:theme_end + 1] + CSS_TAG + NL + text[theme_end + 1:]
    else:
        text = text[:theme_end] + NL + CSS_TAG + text[theme_end:]
    quick = text.index('<section id="quick-start">')
    quick_end = text.index('</section>', quick) + len('</section>')
    text = text[:quick_end] + NL + section(spec) + text[quick_end:]
    toc = re.search(r'<li><a href="#quick-start">[^<]*</a></li>', text)
    if toc is None:
        raise SystemExit(name + ': no quick start line under On this page')
    text = text[:toc.end()] + '<li><a href="#try">Try it</a></li>' + text[toc.end():]
    main_end = text.index('</main>' + NL) + len('</main>' + NL)
    return text[:main_end] + JS_TAG + NL + text[main_end:]


def main():
    changed = 0
    for name in sorted(os.listdir(WEB)):
        if not name.endswith('.html'):
            continue
        path = os.path.join(WEB, name)
        with open(path, encoding='utf-8', newline='') as handle:
            old = handle.read()
        if name not in TRY and 'data-try-endpoint=' not in old and JS_START not in old:
            continue
        new = strip(old)
        if name in TRY:
            new = add(new, TRY[name], name)
        if new != old:
            with open(path, 'w', encoding='utf-8', newline='') as handle:
                handle.write(new)
            changed += 1
            print('wrote the Try box of', name if name in TRY else name + ' (removed)')
    missing = [name for name in TRY if not os.path.exists(os.path.join(WEB, name))]
    if missing:
        raise SystemExit('pages in TRY that do not exist: ' + ', '.join(missing))
    print('Try boxes: %d pages, %d changed' % (len(TRY), changed))


main()
