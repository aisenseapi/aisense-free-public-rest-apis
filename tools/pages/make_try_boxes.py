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
TRY_VERSION = '20261015b'
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


def text(endpoint, verb, busy, label, sample):
    return {'endpoint': endpoint, 'label': label, 'sample': sample, 'button': verb, 'busy': busy, 'limit': MIB,
            'intro': '%s text here. Your browser sends it in a JSON body, as the quick start does. %s' % (verb, LEAVE_OUT)}


TRY = {
    'free-public-api-base64-encode-api-endpoint.html': encoder('base64_encode', 'Hello world'),
    'free-public-api-base64-decode-api-endpoint.html': decoder('base64_decode', 'Base64', 'SGVsbG8gd29ybGQ='),
    'free-public-api-base64url-encode-api-endpoint.html': encoder('base64url_encode', 'hello?'),
    'free-public-api-base64url-decode-api-endpoint.html': decoder('base64url_decode', 'base64url', 'aGVsbG8_'),
    'free-public-api-base32-encode-api-endpoint.html': encoder('base32_encode', 'Hello world'),
    'free-public-api-base32-decode-api-endpoint.html': decoder('base32_decode', 'Base32', 'JBSWY3DPEB3W64TMMQ======', accept=TWO),
    # base58 takes time that grows with the square of the input (8 KiB took over a second on 15 October 2026),
    # so its boxes stop at 1 KiB and take no file.
    'free-public-api-base58-encode-api-endpoint.html': encoder('base58_encode', 'Hello world', file=False, limit=1024),
    'free-public-api-base58-decode-api-endpoint.html': decoder('base58_decode', 'Base58', 'JxF12TrwXzT5jvT', accept=TWO, limit=1024),
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
}


def esc(value):
    return html.escape(value, quote=False)


def section(spec):
    parts = ['<section id="try"><h2>Try it</h2><p>%s</p>' % esc(spec['intro']),
             '<div class="try-card try-api" data-try-endpoint="%s" data-try-limit="%d" data-try-busy="%s"%s%s>' % (
                 spec['endpoint'], spec['limit'], spec['busy'],
                 ' data-try-file="%s"' % spec['file'] if spec.get('file') else '',
                 ' data-try-chars' if spec.get('chars') else ''),
             '<label for="try-input">%s</label><textarea id="try-input" class="try-input" rows="4" spellcheck="false">%s</textarea>' % (esc(spec['label']), esc(spec['sample']))]
    if spec.get('file'):
        parts.append('<div class="try-drop" role="button" tabindex="0"><strong>Or drop a file here</strong> <small>or click to choose one, up to %s</small></div>'
                     '<input type="file" class="try-file" hidden>' % limit_text(spec['limit']))
    if spec.get('accept'):
        parts.append('<label for="try-accept">Answer as</label><select id="try-accept" class="try-accept">'
                     + ''.join('<option value="%s">%s</option>' % option for option in spec['accept']) + '</select>')
    parts.append('<div class="button-row"><button type="button" class="button button-primary try-run">%s</button></div>' % spec['button'])
    parts.append('<p class="try-status" aria-live="polite"></p><pre class="try-result" hidden><code class="try-out"></code></pre>')
    if ACCEPT_BYTES in spec.get('accept', []):
        parts.append('<p class="try-save" hidden><a class="button button-secondary try-save-link" href="#" download="decoded_data.bin">Save decoded_data.bin</a></p>')
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
