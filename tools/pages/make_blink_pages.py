"""Write the endpoint pages for blink_encode and blink_decode into web/, added on 10 November 2026.

Blink is layers 2 and 3 of the Morse family: text as an on and off signal in
Morse timing, and back from bits, run lengths or the levels a camera or a light
sensor recorded. The page around the content, from the head to the footer, is
taken from web/free-public-api-dns-name-api-endpoint.html, as
make_morse_pages.py does. Every example answer was worked out with the
service's own functions (libs/func_blink.php in the service repository), so the
pages show what the service answers.

Usage: python make_blink_pages.py <web>
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
# Full screen starts at 170 ms: the sender's fastest pattern, dots one unit apart, flashes once in two units, and WCAG 2.3.1
# allows at most three flashes a second, so 167 ms is the floor (Admin, 11 November 2026: "da blir det 170ms"). The 80 ms
# unit blinks only in a 140 px square, under a quarter of the 341 by 256 px field in which WCAG counts a general flash
# (Admin, the same day: "den lille ruten er ingen fare", "så 80ms da?"). At 30 frames a second, 70 ms read 6 of 9 trials.
# Change this whenever assets/aisense-blink.css, aisense-blink.js or the receiver QR code change.
LAB_VERSION = '20261111b'

SOS_BITS = '101010001110111011100010101'
SOS_TIMING = [100, 100, 100, 100, 100, 300, 300, 100, 300, 100, 300, 300, 100, 100, 100, 100, 100]
ET_LEVELS = [20, 20, 20, 200, 200, 200] + [20] * 9 + [200] * 9 + [20, 20, 20]
DARK_LEVELS = [230, 230, 230, 15, 15, 15] + [230] * 9 + [15] * 9 + [230, 230, 230]
TIMED = [[0, 20], [40, 22], [70, 21], [101, 198], [134, 205], [168, 201], [199, 19], [233, 24], [266, 20], [300, 22],
         [333, 18], [366, 21], [401, 23], [433, 20], [467, 21], [500, 199], [534, 202], [566, 200], [600, 204], [633, 198],
         [668, 201], [700, 203], [733, 199], [766, 200], [800, 21], [833, 20], [866, 22]]

ENCODE_SOS = OrderedDict([('coding', 'morse'), ('morse', '... --- ...'), ('bits', SOS_BITS), ('timing', SOS_TIMING),
                          ('unit_ms', 100), ('duration_ms', 2700), ('skipped', [])])
ENCODE_HELLO = OrderedDict([('coding', 'morse'), ('morse', '.... . .-.. .-.. ---'), ('bits', '1010101000100010111010100010111010100011101110111'),
                            ('timing', [200, 200, 200, 200, 200, 200, 200, 600, 200, 600, 200, 200, 600, 200, 200, 200, 200, 600, 200, 200, 600, 200, 200, 200, 200, 600, 600, 200, 600, 200, 600]),
                            ('unit_ms', 200), ('duration_ms', 9800), ('skipped', [])])
ENCODE_OK = OrderedDict([('coding', 'morse'), ('morse', '--- -.- / .----'), ('bits', '11101110111000111010111000000010111011101110111'),
                         ('timing', [300, 100, 300, 100, 300, 300, 300, 100, 100, 100, 300, 700, 100, 100, 300, 100, 300, 100, 300, 100, 300]),
                         ('unit_ms', 100), ('duration_ms', 4700), ('skipped', ['#'])])


def read(text, morse, unit=100, inverted=False):
    return OrderedDict([('coding', 'morse'), ('text', text), ('morse', morse), ('unknown', []), ('unit_ms', unit),
                        ('quality', 1), ('inverted', inverted)])


def pre(text):
    return '<pre><code>' + html.escape(text, quote=False) + '</code></pre>'


def curl_get(path):
    return pre('curl ' + API + '/' + path)


def curl_post(path, body):
    return pre('\n'.join(['curl -X POST ' + API + '/' + path + ' ' + B, '  -H "Content-Type: application/json" ' + B,
                          '  -d ' + shlex.quote(json.dumps(body, ensure_ascii=False, separators=(', ', ': ')))]))


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
            + name + ' answer is worked out while the request is open and the signal is gone with it. The access log records '
            'the path and the status. A text or bits sent in the path are part of that path, so post them when they should not be logged.</p></div>'
            '<p>The base URL is <code>https://aisenseapi.com/services/v1</code>. There is no key, no account and no sign-up step. '
            'An encode takes at most 128 bytes of text and a decode at most 200,000 bits, run lengths or levels, and the service-wide '
            'limit is 5000 requests per IP address per day. Every endpoint in the collection is listed on the <a href="/free-public-apis">'
            'Free public REST APIs</a> reference, and the encodings side by side on <a href="/encoding-apis">Encoding APIs</a>.</p></section>')


def banner(path, get_arg):
    return ('<div class="endpoint-banner"><p class="endpoint-banner-label">%s</p>'
            '<p class="sig"><span class="method get">GET</span><span class="path">/%s/%s</span></p>'
            '<p class="sig"><span class="method post">POST</span><span class="path">/%s</span></p>'
            '<code>%s/%s</code></div>') % (('Text to a blink' if path == 'blink_encode' else 'A blink to text'), path, get_arg, path, API, path)


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
    # The lab has a stylesheet and a script of its own, as the audio pages do.
    assert top.count('</head>') == 1 and bottom.count('</body>') == 1
    top = top.replace('</head>', '<link rel="stylesheet" href="/assets/aisense-blink.css?v=' + LAB_VERSION + '">' + chr(10) + '</head>')
    bottom = bottom.replace('</body>', '<script src="/assets/aisense-blink.js?v=' + LAB_VERSION + '" defer></script>' + chr(10) + '</body>')

    sections = spec['sections'] + [privacy(spec['short']), '<section id="related"><h2>Related APIs</h2>' + related(spec['related']) + '</section>']
    toc = spec['toc'] + [('privacy', 'Privacy'), ('related', 'Related')]
    main = ('<main id="main-content" class="api-detail-main">\n'
            '<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/free-public-apis">'
            'Free public REST APIs</a></li><li aria-current="page">' + spec['crumb'] + '</li></ol></nav>\n'
            '<section class="api-detail-hero" aria-labelledby="page-title"><div><p class="eyebrow">Transform - Encoding</p>'
            '<h1 id="page-title">' + spec['h1'] + '</h1><p class="lede">' + spec['lede'] + '</p><ul class="badges">'
            + ''.join('<li>%s</li>' % b for b in spec['badges']) + '</ul></div>' + banner(spec['path'], spec['get_arg']) + '</section>\n'
            '<div class="api-doc-layout"><article class="api-doc">\n' + '\n'.join(sections) + '\n'
            '</article><aside class="on-this-page" aria-label="On this page"><p>On this page</p><ul>'
            + ''.join('<li><a href="#%s">%s</a></li>' % item for item in toc) + '</ul></aside></div>\n</main>')
    body = top + main + bottom
    io.open(WEB + '/' + slug + '.html', 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote', slug + '.html', len(body.encode('utf-8')), 'bytes')


ENCODE_ERRORS = errors([
    ['400', 'No text to blink.', 'No text in the path, no <code>data</code> string and no body'],
    ['413', 'Text over 128 bytes.', 'More than 128 bytes of text in one request'],
    ['400', 'The data is not UTF-8 text.', 'Bytes that are not UTF-8'],
    ['400', 'Nothing in the text has a Morse code.', 'Only characters without a code; <code>skipped</code> lists them'],
    ['400', 'coding is morse.', 'Another coding was asked for'],
    ['400', 'unit_ms is a whole number of milliseconds from 5 to 5000.', 'A unit outside 5 to 5000, or one with a fraction'],
])
DECODE_ERRORS = errors([
    ['400', 'Send one of bits, durations or levels.', 'None of the three, two of them, or a body that is not JSON'],
    ['400', 'bits is a string of 0 and 1.', 'Anything else in the bits'],
    ['400', 'durations is a list of positive numbers of milliseconds, the first one on.', 'A length that is no number or not above 0'],
    ['400', 'levels is a list of numbers, or of [milliseconds, level] pairs.', 'A level that is no number, or a pair of another size'],
    ['400', 'rate is the number of levels per second, above 0 and at most 100000.', 'Plain levels without a rate, or a rate out of range'],
    ['400', 'The times in levels must rise.', 'A pair with a time no later than the one before'],
    ['413', 'At most 200,000 bits, durations or levels.', 'More samples than that in one request'],
    ['400', 'unit_ms is a number of milliseconds above 0 and at most 60000.', 'A unit out of range'],
    ['400', 'invert is true or false.', 'Another value for invert'],
    ['400', 'coding is morse or auto.', 'Another coding was asked for'],
    ['400', 'The levels never change, so there is no signal to read.', 'One level throughout'],
    ['400', 'No Morse could be read from the signal.', 'No letter came out; the answer still gives the code read, <code>unknown</code>, the unit and the quality'],
])
FIX = '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p>'

PAGES = [
    {
        'slug': 'blink-encode', 'path': 'blink_encode', 'get_arg': '{text}', 'crumb': 'Blink Encode API Endpoint', 'short': 'blink encode',
        'title': 'Free Blink Encode API Endpoint - Text to a Blinking Signal | AI SENSE',
        'h1': 'Free Blink Encode API Endpoint',
        'description': 'The free blink encode API endpoint turns up to 128 bytes of text into an on and off signal in Morse timing, as bits and run lengths in milliseconds, for a screen, a lamp, a smart bulb or shades. No API key.',
        'lede': 'The free blink encode API endpoint turns a short text into an on and off signal in Morse timing. The answer holds the signal twice: as bits, one character per unit, and as the lengths of the on and off runs in milliseconds, ready for a screen, a lamp, a smart bulb, window shades or a buzzer to play.',
        'badges': ['No API key', 'Morse timing', 'GET or POST', 'Up to 128 bytes'],
        'toc': [('quick-start', 'Quick start'), ('try', 'Try it'), ('timing', 'The timing'), ('input', 'Input and answer'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free blink encode API endpoint</h2><p>Put the text in the path:</p>'
            + curl_get('blink_encode/SOS') + answer(ENCODE_SOS)
            + '<p>Or post it with a unit of your own, here 200 ms for a lamp seen across a room:</p>'
            + curl_post('blink_encode', OrderedDict([('data', 'HELLO'), ('unit_ms', 200)])) + answer(ENCODE_HELLO)
            + '<p>The way back is the <a href="/free-public-api-blink-decode-api-endpoint">blink decode API endpoint</a>.</p></section>',
            '<section id="try" class="blink-lab" data-blink-tool="send"><div class="blink-lab-head"><p class="blink-kicker">Try it / Sender</p>'
    '<h2>Blink a message on this screen</h2><p>Type a message, and the square below blinks it in Morse timing for a phone camera to read.</p></div>'
    '<div class="blink-lab-body"><ol class="blink-steps"><li>Open the <a href="/free-public-api-blink-decode-api-endpoint#try">receiver</a> on a phone '
    'and choose Start camera.</li><li>Type a message here and choose Blink.</li><li>Hold the phone so the square fills the marked frame until the text comes.</li></ol>'
    '<div class="blink-pair"><img src="/assets/aisense-blink-receiver-qr.png?v=' + LAB_VERSION + '" width="132" height="132" '
    'alt="QR code that opens the blink receiver page"><p>Scan the code to open the receiver on your phone, or go to '
    '<a href="/free-public-api-blink-decode-api-endpoint#try">aisense.no/free-public-api-blink-decode-api-endpoint</a>.</p></div>'
    '<noscript><p>Enable JavaScript to blink here, or call the API as the quick start shows.</p></noscript>'
    '<label for="blink-text">Message</label><textarea id="blink-text" rows="2" spellcheck="false">HELLO</textarea>'
    '<p id="blink-count" class="blink-count">5 / 128 bytes</p>'
    '<label for="blink-unit">Unit</label><select id="blink-unit"><option value="80">80 ms, in a small square: hold the phone still</option>'
    '<option value="170">170 ms, the fastest in full screen</option>'
    '<option value="200" selected>200 ms, a phone held in the hand</option>'
    '<option value="300">300 ms, a camera further off</option><option value="500">500 ms, slow enough to follow by eye</option></select>'
    '<p class="blink-warning">The square flashes white and black, at most 3 times a second from 170 ms. At 80 ms it flashes up to 6 times a second, so it '
    'blinks in a small square and full screen is off. Do not use it if flashing light affects you.</p>'
    '<div class="blink-actions"><button id="blink-start" type="button" class="button button-primary">Blink</button>'
    '<button id="blink-stop" type="button" class="button button-secondary" disabled>Stop</button>'
    '<button id="blink-full" type="button" class="button button-secondary">Full screen</button></div>'
    '<div class="blink-stage"><div class="blink-lamp" data-on="false" aria-hidden="true"></div><p class="blink-note" aria-live="polite">Ready.</p></div>'
    '<p class="blink-status" aria-live="polite" hidden></p>'
    '<div class="blink-output" hidden><h3>The signal</h3><p class="blink-code"></p><pre><code class="blink-json"></code></pre></div>'
    '<p class="blink-help">The text goes to the API, which answers the timing. The blinking runs in your browser, and the screen stays awake '
    'while it blinks where the browser allows it.</p></div></section>',
            '<section id="timing"><h2>The timing</h2><p>Morse timing counts in units. The text becomes International Morse code '
            'first, as the <a href="/free-public-api-morse-encode-api-endpoint">Morse encode API endpoint</a> writes it, with its code table.</p>'
            + table(['Part', 'Length'], [['A dot', '1 unit on'], ['A dash', '3 units on'], ['The gap inside a letter', '1 unit off'],
                                         ['The gap between letters', '3 units off'], ['The gap between words', '7 units off']])
            + '<p>Pick the unit for what will see the signal. It needs at least three samples a unit.</p>'
            + table(['Reader', 'Unit'], [['A phone or webcam at 30 frames per second', '100 ms, the default; 150 ms or more when the picture flickers or moves'],
                                         ['A camera at 60 frames per second', '50 ms'], ['An LED switched by a small computer, read by a light sensor at 1 kHz or more', '5 ms and up'],
                                         ['A person, or window shades seen from afar', '1000 to 5000 ms']]) + '</section>',
            '<section id="input"><h2>Input and answer</h2><ul>'
            '<li><code>GET /blink_encode/{text}</code> takes the text as one path segment, percent-encoded: a space as <code>%20</code>, '
            'a slash as <code>%2F</code>. Two more segments may follow, the coding and the unit: <code>/blink_encode/SOS/morse/200</code>.</li>'
            '<li><code>POST /blink_encode</code> takes <code>{"data": "...", "unit_ms": 100}</code> with <code>Content-Type: application/json</code>, '
            'or the text as the raw request body with any other type. At most 128 bytes, in UTF-8. <code>unit_ms</code> is a whole number from 5 to 5000.</li>'
            '<li><code>morse</code> is the code. <code>bits</code> has one character per unit, <code>1</code> for on and <code>0</code> for off. '
            '<code>timing</code> lists the lengths of the runs in milliseconds, the first one on. <code>duration_ms</code> is the whole signal.</li>'
            '<li><code>skipped</code> lists each character without a code once, as the Morse encode endpoint does.</li></ul>'
            '<p>To play the signal, switch on for the first value of <code>timing</code>, off for the next, and so on. Leave it off for a '
            'few units before and after, so a reader sees where the message starts and ends.</p>'
            + curl_post('blink_encode', OrderedDict([('data', 'OK #1')])) + answer(ENCODE_OK) + '</section>',
            '<section id="errors"><h2>Errors</h2>' + ENCODE_ERRORS + FIX + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('A screen that speaks to a phone', 'Blink a square on a laptop, a kiosk or a sign, and read it back with a phone camera through the decode endpoint.'),
                ('A lamp or a smart bulb', 'Switch a lamp by the timing to pass a short code, a room number or a status across a room.'),
                ('Shades and slow signals', 'At a unit of a second or more, shades, a porch light or a flag can carry a word that a camera reads from far away.'),
                ('Agents', 'Through the MCP server the same encoder is the tool <code>encode_blink</code>.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-blink-decode-api-endpoint', 'Blink Decode API Endpoint', 'A blink back to text'),
            ('/free-public-api-morse-encode-api-endpoint', 'Morse Encode API Endpoint', 'Text to dots and dashes'),
            ('/free-public-api-audio-encode-api-endpoint', 'Audio Encode API Endpoint', 'A message as sound'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'blink-decode', 'path': 'blink_decode', 'get_arg': '{bits}', 'crumb': 'Blink Decode API Endpoint', 'short': 'blink decode',
        'title': 'Free Blink Decode API Endpoint - Read Text from a Blinking Light | AI SENSE',
        'h1': 'Free Blink Decode API Endpoint',
        'description': 'The free blink decode API endpoint reads text back from an on and off signal: bits, run lengths, or the brightness a camera or a light sensor recorded. It finds the unit and which level is on. No API key.',
        'lede': 'The free blink decode API endpoint reads Morse back from an on and off signal. Send the bits, the lengths of the on and off runs, or the levels a camera or a light sensor recorded, and it finds the threshold, the unit and which level means on.',
        'badges': ['No API key', 'Bits, runs or levels', 'Finds the unit', 'Up to 200,000 samples'],
        'toc': [('quick-start', 'Quick start'), ('try', 'Try it'), ('signals', 'Signals it reads'), ('reading', 'How it reads'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free blink decode API endpoint</h2><p>Put the bits in the path:</p>'
            + curl_get('blink_decode/' + SOS_BITS) + answer(read('SOS', '... --- ...'))
            + '<p>Or post the brightness of a square in each camera frame, with the frames per second:</p>'
            + curl_post('blink_decode', OrderedDict([('levels', ET_LEVELS), ('rate', 30)])) + answer(read('ET', '. -'))
            + '<p>The way there is the <a href="/free-public-api-blink-encode-api-endpoint">blink encode API endpoint</a>.</p></section>',
            '<section id="try" class="blink-lab" data-blink-tool="receive"><div class="blink-lab-head"><p class="blink-kicker">Try it / Receiver</p>'
    '<h2>Read a blink with the camera</h2><p>Film the blinking square, and the brightness in the marked frame becomes text.</p></div>'
    '<div class="blink-lab-body"><ol class="blink-steps"><li>Open the <a href="/free-public-api-blink-encode-api-endpoint#try">sender</a> on a laptop or '
    'another screen.</li><li>Choose Start camera here and fit the square in the marked frame.</li><li>Choose Blink there. The text comes when the square stays dark.</li></ol>'
    '<noscript><p>Enable JavaScript for the camera, or send levels to the API as the examples below show.</p></noscript>'
    '<div class="blink-view" data-live="false"><video playsinline muted aria-label="The camera picture"></video><div class="blink-target" aria-hidden="true"></div></div>'
    '<label class="blink-auto-option"><input id="blink-auto" type="checkbox" checked>Read automatically when the blinking stops</label>'
    '<div class="blink-actions"><button id="blink-camera" type="button" class="button button-primary">Start camera</button>'
    '<button id="blink-read" type="button" class="button button-secondary" disabled>Stop and read</button>'
    '<button id="blink-cancel" type="button" class="button button-secondary" disabled>Cancel</button></div>'
    '<div class="blink-meter-row"><label for="blink-level">Brightness</label><meter id="blink-level" min="0" max="255" value="0">0</meter>'
    '<span class="blink-dot" data-on="false" aria-hidden="true"></span><span class="blink-timer">0.0 s</span></div>'
    '<p class="blink-help">The camera starts only when you choose Start camera, and the picture stays in your browser. Only the brightness of the '
    'marked frame, one number a frame with its time, goes to AI SENSE when the blinking stops or when you choose Stop and read. Cancel sends nothing.</p>'
    '<p class="blink-status" aria-live="polite" hidden></p>'
    '<div class="blink-output" hidden><h3>The message</h3><p class="blink-result-text"></p><p class="blink-result-meta"></p>'
    '<details><summary>The answer</summary><pre><code class="blink-json"></code></pre></details></div></div></section>',
            '<section id="signals"><h2>Signals it reads</h2><p>Send one of these in a JSON body, at most 200,000 values:</p><ul>'
            '<li><code>bits</code>, a string of <code>0</code> and <code>1</code>, one character per unit, as the encode endpoint answers it. '
            'In the path it is <code>/blink_decode/{bits}</code>, or <code>/blink_decode/{bits}/{unit_ms}</code> to name the length of a character '
            'in the answer, 100 ms by default.</li>'
            '<li><code>durations</code>, the lengths of the on and off runs in milliseconds in turn, the first one on, as the encode endpoint '
            'answers them in <code>timing</code>.</li>'
            '<li><code>levels</code> with <code>rate</code>, one reading per sample, such as the mean brightness of a square in each camera '
            'frame, and the samples per second.</li>'
            '<li><code>levels</code> as <code>[milliseconds, level]</code> pairs, for frames that come unevenly.</li></ul>'
            + curl_post('blink_decode', OrderedDict([('durations', SOS_TIMING)])) + answer(read('SOS', '... --- ...'))
            + curl_post('blink_decode', OrderedDict([('levels', TIMED)])) + answer(read('ET', '. -', 99.6)) + '</section>',
            '<section id="reading"><h2>How it reads</h2><ul>'
            '<li>A median of three takes out a glitch in one frame. The levels split into two groups halfway between their means, with a '
            'margin on each side, so noise near the middle does not switch the state.</li>'
            '<li>The level at both ends of the series is taken as off, since a signal starts and ends idle. A screen that goes dark to signal '
            'is found that way and the answer says <code>"inverted": true</code>. Send <code>invert</code> to say it yourself.</li>'
            '<li>Runs shorter than a third of the unit are flicker and join the run before them.</li>'
            '<li>The unit is the one that fits the runs best to 1 or 3 units on and 1, 3 or 7 units off. A message of one letter has runs '
            'of one length only and is read at the unit nearest 100 ms, so send <code>unit_ms</code> when it went out at another.</li>'
            '<li><code>quality</code> is the share of runs within a quarter unit of the 1, 3 or 7 units they were read as: 1 for a clean '
            'signal and lower for a noisy one.</li>'
            '<li>Record a few units of idle before and after the message, and at least three samples a unit. A camera at 30 frames per '
            'second reads 100 ms units in a steady picture and needs 150 ms or more when the picture flickers.</li></ul>'
            '<p>The answer holds <code>text</code> in upper case, <code>morse</code> as read, <code>unknown</code> for sequences without a '
            'character, the <code>unit_ms</code> found, <code>quality</code> and <code>inverted</code>. A dark signal on a bright screen:</p>'
            + curl_post('blink_decode', OrderedDict([('levels', DARK_LEVELS), ('rate', 30)])) + answer(read('ET', '. -', 100, True)) + '</section>',
            '<section id="errors"><h2>Errors</h2>' + DECODE_ERRORS + FIX + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Read a blinking screen with a phone', 'Measure the brightness of a square in each camera frame and send the levels with the frame rate.'),
                ('A light sensor on a small board', 'Send the readings of a photodiode, and let the endpoint find the threshold and the unit.'),
                ('Check what a device sends', 'Record a status light or a buzzer as on and off lengths and read the code it keys.'),
                ('Agents', 'Through the MCP server the same decoder is the tool <code>decode_blink</code>.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-blink-encode-api-endpoint', 'Blink Encode API Endpoint', 'Text to a blinking signal'),
            ('/free-public-api-morse-decode-api-endpoint', 'Morse Decode API Endpoint', 'Dots and dashes to text'),
            ('/free-public-api-audio-decode-api-endpoint', 'Audio Decode API Endpoint', 'Read data from a recording'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
]

for spec in PAGES:
    page(spec)
