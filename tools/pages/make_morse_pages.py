"""Write the endpoint pages for morse_encode and morse_decode into web/, the Morse pair added on 10 November 2026.

The page around the content, from the head to the footer, is taken from
web/free-public-api-dns-name-api-endpoint.html, as make_codec_pages.py does.
Every example answer was worked out with the service's own functions
(libs/func_morse.php in the service repository), and the code table is that
file's table, so the pages show what the service answers.

Usage: python make_morse_pages.py <web>
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

# libs/func_morse.php, aisense_morse_table(), in its order.
TABLE = [
    ('A', '.-'), ('B', '-...'), ('C', '-.-.'), ('D', '-..'), ('E', '.'), ('F', '..-.'), ('G', '--.'), ('H', '....'),
    ('I', '..'), ('J', '.---'), ('K', '-.-'), ('L', '.-..'), ('M', '--'), ('N', '-.'), ('O', '---'), ('P', '.--.'),
    ('Q', '--.-'), ('R', '.-.'), ('S', '...'), ('T', '-'), ('U', '..-'), ('V', '...-'), ('W', '.--'), ('X', '-..-'),
    ('Y', '-.--'), ('Z', '--..'),
    ('0', '-----'), ('1', '.----'), ('2', '..---'), ('3', '...--'), ('4', '....-'), ('5', '.....'), ('6', '-....'),
    ('7', '--...'), ('8', '---..'), ('9', '----.'),
    ('.', '.-.-.-'), (',', '--..--'), ('?', '..--..'), ("'", '.----.'), ('/', '-..-.'), ('(', '-.--.'), (')', '-.--.-'),
    (':', '---...'), ('=', '-...-'), ('+', '.-.-.'), ('-', '-....-'), ('"', '.-..-.'), ('@', '.--.-.'), ('!', '-.-.--'),
    ('&', '.-...'), (';', '-.-.-.'), ('_', '..--.-'), ('$', '...-..-'),
    ('Æ', '.-.-'), ('Ø', '---.'), ('Å', '.--.-'), ('Ä', '.-.-'), ('Ö', '---.'), ('Ü', '..--'),
    ('É', '..-..'), ('Ñ', '--.--'), ('Ç', '-.-..'), ('À', '.--.-'),
]


def pre(text):
    return '<pre><code>' + html.escape(text, quote=False) + '</code></pre>'


def curl_get(path):
    return pre('curl ' + API + '/' + path)


def curl_post(path, data):
    return pre('\n'.join(['curl -X POST ' + API + '/' + path + ' ' + B, '  -H "Content-Type: application/json" ' + B,
                          '  -d ' + shlex.quote(json.dumps({'data': data}, ensure_ascii=False))]))


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


def code_table():
    """The 64 characters in four column pairs, character and code."""
    cells = [('<code>%s</code>' % html.escape(c), '<code>%s</code>' % code) for c, code in TABLE]
    rows = []
    for i in range(0, len(cells), 4):
        row = []
        for pair in cells[i:i + 4]:
            row.extend(pair)
        row.extend([''] * (8 - len(row)))
        rows.append(row)
    return table(['Character', 'Code'] * 4, rows)


def privacy(name):
    return ('<section id="privacy"><h2>Privacy and limits</h2><div class="api-note warning-note"><p>Nothing is stored. The '
            + name + ' answer is worked out while the request is open and the text is gone with it. The access log records '
            'the path and the status. A text sent in the path is part of that path, so post it when it should not be logged.</p></div>'
            '<p>The base URL is <code>https://aisenseapi.com/services/v1</code>. There is no key, no account and no sign-up step. '
            'An encode takes at most 64 KiB of text and a decode at most 512 KiB of code, and the service-wide limit is 5000 requests '
            'per IP address per day. Every endpoint in the collection is listed on the <a href="/free-public-apis">Free public REST '
            'APIs</a> reference, and the encodings side by side on <a href="/encoding-apis">Encoding APIs</a>.</p></section>')


def banner(path, get_arg):
    return ('<div class="endpoint-banner"><p class="endpoint-banner-label">%s</p>'
            '<p class="sig"><span class="method get">GET</span><span class="path">/%s/%s</span></p>'
            '<p class="sig"><span class="method post">POST</span><span class="path">/%s</span></p>'
            '<code>%s/%s</code></div>') % (('Text to Morse' if path == 'morse_encode' else 'Morse to text'), path, get_arg, path, API, path)


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
            + ''.join('<li>%s</li>' % b for b in spec['badges']) + '</ul></div>' + banner(spec['path'], spec['get_arg']) + '</section>\n'
            '<div class="api-doc-layout"><article class="api-doc">\n' + '\n'.join(sections) + '\n'
            '</article><aside class="on-this-page" aria-label="On this page"><p>On this page</p><ul>'
            + ''.join('<li><a href="#%s">%s</a></li>' % item for item in toc) + '</ul></aside></div>\n</main>')
    body = top + main + bottom
    io.open(WEB + '/' + slug + '.html', 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote', slug + '.html', len(body.encode('utf-8')), 'bytes')


ENCODE_ERRORS = errors([
    ['400', 'No text to encode in Morse.', 'No text in the path, no <code>data</code> string and no body'],
    ['413', 'Text over 64 KiB.', 'More than 64 KiB of text in one request'],
    ['400', 'The data is not UTF-8 text.', 'Bytes that are not UTF-8'],
    ['400', 'Nothing in the text has a Morse code.', 'Only characters without a code; <code>skipped</code> lists them'],
])
DECODE_ERRORS = errors([
    ['400', 'No Morse code to decode.', 'No code in the path, no <code>data</code> string and no body'],
    ['413', 'Morse code over 512 KiB.', 'More than 512 KiB of code in one request'],
    ['400', 'The data is not UTF-8 text.', 'Bytes that are not UTF-8'],
    ['400', 'No sequence in the code is Morse for a character.', 'Nothing could be read; <code>unknown</code> lists what was sent'],
])
FIX = '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p>'

PAGES = [
    {
        'slug': 'morse-encode', 'path': 'morse_encode', 'get_arg': '{text}', 'crumb': 'Morse Encode API Endpoint', 'short': 'Morse encode',
        'title': 'Free Morse Code Encode API Endpoint - Text to Morse Code | AI SENSE',
        'h1': 'Free Morse Code Encode API Endpoint',
        'description': 'The free Morse code encode API endpoint turns text into International Morse code: dots and dashes, a space between letters and a slash between words. GET or POST, no API key.',
        'lede': 'The free Morse code encode API endpoint turns text into International Morse code: dots and dashes for each letter, one space between letters and a slash between words. Put the text in the URL or post it. A character without a code is listed in the answer, never guessed.',
        'badges': ['No API key', 'International Morse', 'GET or POST', 'Æ Ø Å'],
        'toc': [('quick-start', 'Quick start'), ('code', 'The code'), ('input', 'Input and answer'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free Morse code encode API endpoint</h2><p>Put the text in the path:</p>'
            + curl_get('morse_encode/SOS') + answer({'morse_encoded_data': '... --- ...', 'skipped': []})
            + '<p>Or post it, for longer text or text that should stay out of the URL:</p>'
            + curl_post('morse_encode', 'Hello, world!')
            + answer({'morse_encoded_data': '.... . .-.. .-.. --- --..-- / .-- --- .-. .-.. -.. -.-.--', 'skipped': []})
            + '<p>The other way is the <a href="/free-public-api-morse-decode-api-endpoint">Morse decode API endpoint</a>.</p></section>',
            '<section id="code"><h2>The code</h2><p>International Morse code as ITU-R M.1677-1 sets it out, with the marks ! &amp; ; _ $ '
            'that are in common use and the letters beyond A to Z that Nordic and other European languages need. Letters are encoded '
            'whatever their case.</p>' + code_table()
            + '<p>Ä and Æ share a code, as do Ö and Ø, and À and Å. A dot is the unit of time: a dash lasts three units, '
            'the gap inside a letter one, the gap between letters three and the gap between words seven.</p></section>',
            '<section id="input"><h2>Input and answer</h2><ul>'
            '<li><code>GET /morse_encode/{text}</code> takes the text as one path segment, percent-encoded: a space as <code>%20</code>, '
            'a slash as <code>%2F</code>, å as <code>%C3%A5</code>. The server turns away a path with two dots in a row, so text such as '
            '<code>Wait...</code> goes in a POST.</li>'
            '<li><code>POST /morse_encode</code> takes <code>{"data": "..."}</code> with <code>Content-Type: application/json</code>, or the '
            'text as the raw request body with any other type. At most 64 KiB, in UTF-8.</li>'
            '<li>A run of spaces, tabs or line breaks is one word gap, written <code> / </code>. Spaces at the ends are left out.</li>'
            '<li><code>morse_encoded_data</code> is the code. <code>skipped</code> lists each character without a code once, at most 32 of them; '
            'invisible marks such as the selector after an emoji are left out without being listed.</li></ul>'
            + curl_post('morse_encode', 'Call 112 #now')
            + answer({'morse_encoded_data': '-.-. .- .-.. .-.. / .---- .---- ..--- / -. --- .--', 'skipped': ['#']}) + '</section>',
            '<section id="errors"><h2>Errors</h2>' + ENCODE_ERRORS + FIX + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Learning and practice', 'Turn practice words and call signs into code to read or key, and check what a learner wrote.'),
                ('A message by light or sound', 'Encode a short message, then flash a lamp or sound a buzzer by its dots and dashes, a dot as one unit of time.'),
                ('Puzzles and games', 'Hide a clue in dots and dashes for an escape room, a treasure hunt or a game level.'),
                ('Agents', 'Through the MCP server the same encoder is <code>encode_data</code> with the format <code>morse</code>.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-morse-decode-api-endpoint', 'Morse Decode API Endpoint', 'Morse code back to text'),
            ('/free-public-api-spell-api-endpoint', 'Spell API Endpoint', 'Spell text letter by letter as sound'),
            ('/free-public-api-url-encode-api-endpoint', 'URL Encode API Endpoint', 'Text for a path segment'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
    {
        'slug': 'morse-decode', 'path': 'morse_decode', 'get_arg': '{code}', 'crumb': 'Morse Decode API Endpoint', 'short': 'Morse decode',
        'title': 'Free Morse Code Decode API Endpoint - Morse Code to Text | AI SENSE',
        'h1': 'Free Morse Code Decode API Endpoint',
        'description': 'The free Morse code decode API endpoint turns dots and dashes back into text. It reads the usual look-alikes, splits words at a slash or two spaces and lists what it cannot read. No API key.',
        'lede': 'The free Morse code decode API endpoint turns dots and dashes back into text in upper case. It reads the look-alikes people type, such as a middle dot or a long dash, and lists every sequence it cannot read instead of guessing.',
        'badges': ['No API key', 'International Morse', 'GET or POST', 'Lists what it cannot read'],
        'toc': [('quick-start', 'Quick start'), ('rules', 'Rules'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free Morse code decode API endpoint</h2><p>Put the code in the path with <code>*</code> '
            'for each dot and <code>%20</code> for a space, since a path cannot hold two dots in a row:</p>' + curl_get('morse_decode/***%20---%20***')
            + answer({'morse_decoded_data': 'SOS', 'unknown': []})
            + '<p>Or post it:</p>' + curl_post('morse_decode', '.... . .-.. .-.. --- / .-- --- .-. .-.. -..')
            + answer({'morse_decoded_data': 'HELLO WORLD', 'unknown': []})
            + '<p>The other way is the <a href="/free-public-api-morse-encode-api-endpoint">Morse encode API endpoint</a>.</p></section>',
            '<section id="rules"><h2>Rules</h2><ul>'
            '<li>One space between letters. Between words a slash, a <code>|</code>, a line break or two or more spaces. In a URL a '
            '<code>|</code> needs no escape, while a slash is written <code>%2F</code>.</li>'
            '<li>Dots and dashes may be typed as <code>.</code> and <code>-</code> or as their look-alikes: the middle dot, the bullet and '
            '<code>*</code> for a dot, and the en dash, the em dash, the minus sign and the underscore for a dash.</li>'
            '<li>The text comes back in upper case, since Morse has no case. A code that two letters share comes back as Æ, Ø or Å.</li>'
            '<li><code>unknown</code> lists each sequence that is not a character once, at most 32 of them, and the text goes on without it.</li>'
            '<li><code>GET /morse_decode/{code}</code> takes the code as one path segment. The server turns away a path with two dots in a '
            'row, so write each dot there as <code>*</code>. <code>POST /morse_decode</code> takes '
            '<code>{"data": "..."}</code> with <code>Content-Type: application/json</code>, or the code as the raw body. At most 512 KiB.</li></ul>'
            + curl_post('morse_decode', '.- ........ -...') + answer({'morse_decoded_data': 'AB', 'unknown': ['........']}) + '</section>',
            '<section id="errors"><h2>Errors</h2>' + DECODE_ERRORS + FIX + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Check what was keyed', 'Read back the dots and dashes a learner or a program wrote, and see at once which letters did not come through.'),
                ('Read a written message', 'Turn code copied from a puzzle, a note or a recording transcript into text.'),
                ('Agents', 'Through the MCP server the same decoder is <code>encode_data</code> with the format <code>morse</code> and the operation <code>decode</code>.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-morse-encode-api-endpoint', 'Morse Encode API Endpoint', 'Text to Morse code'),
            ('/free-public-api-url-decode-api-endpoint', 'URL Decode API Endpoint', 'Percent-encoding to text'),
            ('/free-public-api-audio-decode-api-endpoint', 'Audio Decode API Endpoint', 'Read data from a recording'),
            ('/encoding-apis', 'Encoding APIs', 'Every encoding side by side'),
        ],
    },
]

for spec in PAGES:
    page(spec)
