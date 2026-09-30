"""Write the seven image tool pages into web/.

The example answers come from the JSON files in data/, recorded by running
each request through the service's real handler with ImageMagick on test
images. build.py runs this with the right arguments.

Usage: python make_image_pages.py <web> <results-images.json> <results-more.json> [<results-heic.json>]
"""
import html
import io
import json
import sys
from collections import OrderedDict

WEB = sys.argv[1]
RESULTS = json.load(io.open(sys.argv[2], encoding='utf-8'), object_pairs_hook=OrderedDict)
for extra in sys.argv[3:]:
    RESULTS.update(json.load(io.open(extra, encoding='utf-8'), object_pairs_hook=OrderedDict))
B = chr(92)

HEADER = io.open(WEB + '/free-json-to-csv-api.html', encoding='utf-8').read().split('<header class="site-header">', 1)[1].split('</header>', 1)[0]
HEADER = '<header class="site-header">' + HEADER + '</header>'
FOOTER = io.open(WEB + '/free-json-to-csv-api.html', encoding='utf-8').read().split('<footer class="site-footer">', 1)[1].split('</footer>', 1)[0]
FOOTER = '<footer class="site-footer">' + FOOTER + '</footer>'

PROVIDER = OrderedDict([
    ('@type', 'Organization'),
    ('name', 'AI SENSE AS'),
    ('url', 'https://aisense.no'),
    ('address', OrderedDict([
        ('@type', 'PostalAddress'),
        ('postOfficeBoxNumber', 'Postboks 1202 Vika'),
        ('postalCode', '0110'),
        ('addressLocality', 'Oslo'),
        ('addressCountry', 'NO')
    ]))
])

RELATED = '''<h2 id="related">Related tools</h2>
<ul>
  <li><a href="/free-image-converter-api">Image converter</a>, <a href="/free-image-resizer-api">image resizer</a> and <a href="/free-image-compression-api">image compression</a>, and the <a href="/free-heic-to-jpg-converter">HEIC to JPG converter</a> for iPhone photos</li>
  <li><a href="/free-image-metadata-viewer-api">Image metadata viewer</a> and <a href="/free-exif-remover-api">EXIF remover</a></li>
  <li>Guide: <a href="/convert-heic-webp-png-and-jpg-images">how to convert HEIC, WebP, PNG and JPG, and make images smaller</a></li>
  <li>Guide: <a href="/remove-gps-location-and-exif-data-from-photos">how to see and remove the location hidden in your photos</a></li>
  <li><a href="/free-image-color-palette-api">Colour palette</a> and <a href="/free-favicon-generator-api">favicon generator</a></li>
  <li>Guide: <a href="/favicon-sizes-and-the-files-a-website-needs">favicon sizes and the files a website needs</a></li>
  <li><a href="/free-json-to-csv-api">JSON to CSV</a>, <a href="/free-csv-to-json-api">CSV to JSON</a> and <a href="/free-table-matching-api">table matching</a></li>
  <li><a href="/free-json-formatter-api">JSON formatter</a> and <a href="/free-json-validator-api">JSON validator</a></li>
  <li><a href="/upload">File uploader</a> and the <a href="/free-public-api-storage-api-endpoint">Temporary Storage API</a>, where every result is kept for 24 hours</li>
</ul>

<p class="button-row"><a class="button button-secondary" href="/free-public-apis#images">All image endpoints</a> <a class="button button-light" href="/free-public-apis">All free public APIs</a></p>'''

STORAGE_SECTION = '''<h2 id="storage">The answer is a Storage link</h2>
<p>The endpoint never sends the image in its answer. It stores the result for 24 hours and answers with the same fields the <a href="/free-public-api-storage-api-endpoint">Temporary Storage API</a> answers with, plus what the result is:</p>
<table>
  <thead><tr><th>Field</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>storage_id</code>, <code>storage_url</code></td><td>Where the result is. A GET on the URL returns the image.</td></tr>
    <tr><td><code>sha256_hash</code>, <code>bytes</code></td><td>The digest and size of the stored image.</td></tr>
    <tr><td><code>expire_timestamp</code>, <code>expire_datetime</code></td><td>When the result is removed, 24 hours after it was stored.</td></tr>
    <tr><td><code>content_type</code>, <code>filename</code></td><td>The type of the image and the name to save it under.</td></tr>
    <tr><td><code>operation</code>, <code>format</code>, <code>width</code>, <code>height</code></td><td>The endpoint that made it, and the format and size of the result in pixels.</td></tr>
    <tr><td><code>input_format</code>, <code>input_bytes</code></td><td>What the upload was, so the saving can be read off.</td></tr>
  </tbody>
</table>
<p>The example at the top of the page comes from a test run with a test image of 1600 x 1200 pixels. The id and the expiry are different on every call, and the sizes depend on the image.</p>
<p>Anyone with the link can open the image until it expires, so do not send pictures of people or anything confidential. Stored results count against the Storage budget of 80 MB per IP address per day.</p>'''

STORAGE_ROWS = '''    <tr><td><code>storage_id</code>, <code>storage_url</code></td><td>Where the result is. A GET on the URL returns it.</td></tr>
    <tr><td><code>sha256_hash</code>, <code>bytes</code></td><td>The digest and size of the stored result.</td></tr>
    <tr><td><code>expire_timestamp</code>, <code>expire_datetime</code></td><td>When the result is removed, 24 hours after it was stored.</td></tr>'''

LIMITS = '''<h2 id="limits">Limits</h2>
<ul>
  <li>The upload is at most 10 MB and 25 megapixels.</li>
  <li>The result is at most 8 MB. A photo saved as PNG often goes over that; as JPEG or WebP it is far smaller.</li>
  <li>WebP allows at most 16383 pixels per side.</li>
  <li>One conversion may take at most 45 seconds.</li>
  <li>At most two images are converted at a time. A third waits up to ten seconds and is then answered 503 with <code>Retry-After</code>.</li>
</ul>'''

LIMITS_DECODED = '''<h2 id="limits">Limits</h2>
<ul>
  <li>The upload is a JPEG, PNG or WebP of at most 10 MB and 25 megapixels.</li>
  <li>One request may take at most 45 seconds.</li>
  <li>At most two images are worked on at a time, together with the image converter and image compression. A third waits up to ten seconds and is then answered 503 with <code>Retry-After</code>.</li>
</ul>'''

LIMITS_READ = '''<h2 id="limits">Limits</h2>
<ul>
  <li>The upload is a JPEG, PNG or WebP of at most 10 MB. There is no pixel limit, since the image is not decoded.</li>
  <li>HEIC is read by the <a href="/free-image-converter-api">image converter</a> and the <a href="/free-image-resizer-api">image resizer</a> only.</li>
  <li>%s</li>
</ul>'''


def errors(formats, bad_request, unavailable):
    return '''<h2 id="errors">Errors</h2>
<p>A refused request stores nothing and answers with <code>error</code>. The endpoint's own refusals also carry <code>fix</code>, a sentence saying what to send instead.</p>
<table>
  <thead><tr><th>Status</th><th>When</th></tr></thead>
  <tbody>
    <tr><td><code>400</code></td><td>%s</td></tr>
    <tr><td><code>405</code></td><td>The method is not <code>POST</code>.</td></tr>
    <tr><td><code>413</code></td><td>The upload, its number of pixels or the result is over a limit.</td></tr>
    <tr><td><code>415</code></td><td>The body is not <code>multipart/form-data</code>, or the file is not a %s.</td></tr>
    <tr><td><code>429</code></td><td>More than 5000 requests from one IP address in 24 hours, or the day's Storage budget is used up.</td></tr>
    <tr><td><code>503</code></td><td>%s</td></tr>
  </tbody>
</table>''' % (bad_request, formats, unavailable)


ERRORS_CONVERT = errors('JPEG, PNG, WebP or HEIC',
    'A field is missing, unknown or out of range, the upload is not one whole file, or ImageMagick cannot read the image.',
    'Two images are being converted already, the conversion took more than 45 seconds, or the service cannot convert right now.')
ERRORS = errors('JPEG, PNG or WebP',
    'A field is missing, unknown or out of range, the upload is not one whole file, or ImageMagick cannot read the image.',
    'Two images are being converted already, the conversion took more than 45 seconds, or the service cannot convert right now.')
ERRORS_READ = errors('JPEG, PNG or WebP',
    'A field was sent, the upload is not one whole file, or the file cannot be read as an image.',
    'The service cannot read or store the image right now.')
ERRORS_DECODED = errors('JPEG, PNG or WebP',
    'A field is unknown or out of range, the upload is not one whole file, or ImageMagick cannot read the image.',
    'Two images are being worked on already, the work took more than 45 seconds, or the service cannot do it right now.')

METADATA = '''<li><strong>The image is turned upright</strong> from the orientation a phone camera writes in the EXIF data, before that data is removed.</li>
  <li><strong>EXIF, XMP, IPTC and comments are removed</strong>, so the camera, the GPS position, the date and the software do not follow the image. The ICC colour profile is kept, so the colours stay the same. A CMYK JPEG is converted to RGB.</li>'''

ACCEPT = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
ACCEPT_HEIC = ACCEPT + ',image/heic,image/heif,.heic,.heif'


def drop(kinds, accept):
    return '''    <div class="tool-drop tool-drop-large" id="tool-drop" role="button" tabindex="0">
      <strong>Drop an image here</strong>
      <small>or click to choose one, or paste it with Ctrl+V. %s, up to 10 MB.</small>
    </div>
    <input type="file" id="tool-file" accept="%s" hidden>
    <div class="tool-chosen" id="tool-chosen" hidden>
      <img id="tool-thumb" alt="The image you chose">
      <p class="tool-meta" id="tool-chosen-text"></p>
    </div>''' % (kinds, accept)


DROP = drop('JPEG, PNG or WebP', ACCEPT)

# The first lines of every page script: the elements and the formats the page
# takes. SCRIPT_CHOOSE follows it on every page.
def script_start(accepts, accepts_text, extra=''):
    return r'''(function () {
  var T = window.AisenseTools;
  var form = document.getElementById('tool-form');
''' + extra + r'''  var submit = document.getElementById('tool-submit');
  var chosen = document.getElementById('tool-chosen');
  var thumb = document.getElementById('tool-thumb');
  var chosenText = document.getElementById('tool-chosen-text');
  var result = document.getElementById('tool-result');
  var accepts = [''' + ', '.join("'%s'" % a for a in accepts) + r'''];
  var acceptsText = ''' + "'%s'" % accepts_text + r''';
  if (!T || !form) { return; }
'''


# The chosen image and its format, read from the first bytes. A HEIC is known
# by an HEVC brand in its ftyp box; most browsers cannot show it, so its
# preview is hidden.
SCRIPT_CHOOSE = r'''  var names = { jpeg: 'JPEG', png: 'PNG', webp: 'WebP', heic: 'HEIC' };
  var hevc = ['heic', 'heix', 'heim', 'heis', 'hevc', 'hevx'];
  var file = null;
  var chosenFormat = null;
  var thumbUrl = null;

  function formatOf(picked) {
    return picked.slice(0, 64).arrayBuffer().then(function (buffer) {
      var b = new Uint8Array(buffer);
      var text = function (from, to) { return String.fromCharCode.apply(null, b.subarray(from, to)); };
      if (b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF) { return 'jpeg'; }
      if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4E && b[3] === 0x47) { return 'png'; }
      if (text(0, 4) === 'RIFF' && text(8, 12) === 'WEBP') { return 'webp'; }
      if (b.length >= 16 && text(4, 8) === 'ftyp') {
        var end = Math.min(b.length, ((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]) >>> 0);
        var brands = [text(8, 12)];
        for (var at = 16; at + 4 <= end; at += 4) { brands.push(text(at, at + 4)); }
        if (brands[0] !== 'avif' && brands[0] !== 'avis' && brands.some(function (brand) { return hevc.indexOf(brand) !== -1; })) { return 'heic'; }
      }
      return null;
    });
  }

  function choose(picked, done) {
    file = picked;
    T.clear(result);
    Promise.all([T.imageSize(picked), formatOf(picked)]).then(function (read) {
      var size = read[0];
      chosenFormat = read[1];
      if (thumbUrl) { URL.revokeObjectURL(thumbUrl); }
      thumbUrl = size ? size.url : null;
      thumb.src = thumbUrl || '';
      thumb.hidden = !thumbUrl;
      chosen.hidden = false;
      chosenText.textContent = picked.name + ', ' + (chosenFormat ? names[chosenFormat] + ', ' : '') + T.bytes(picked.size)
        + (size ? ', ' + size.width + ' x ' + size.height + ' pixels' : '');
      var taken = !!chosenFormat && accepts.indexOf(chosenFormat) !== -1;
      if (!taken) {
        var error = new Error(chosenFormat === 'heic' ? 'HEIC is read by the image converter and the image resizer only.' : 'This is not a ' + acceptsText + ' image.');
        error.fix = chosenFormat === 'heic' ? 'Convert it to JPEG on the image converter page first.' : 'Choose a ' + acceptsText + ' file.';
        T.showError(result, error);
      }
      submit.disabled = !taken;
      done();
    });
  }'''

# The line that says what a conversion saved, for the converter and compression.
SCRIPT_SUMMARY = r'''

  function summary(answer) {
    var change = answer.bytes - answer.input_bytes;
    var percent = Math.round(Math.abs(change) / answer.input_bytes * 100);
    var line = names[answer.input_format] + ', ' + T.bytes(answer.input_bytes) + ', became ' + names[answer.format] + ', '
      + T.bytes(answer.bytes) + ', ' + answer.width + ' x ' + answer.height + ' pixels';
    if (change < 0) { return line + '. That is ' + percent + '% smaller.'; }
    // A new format is asked for because it opens where the old one does not.
    if (change > 0 && answer.format !== answer.input_format) { return line + '. That is ' + percent + '% larger.'; }
    if (change > 0) { return line + '. That is ' + percent + '% larger, so the original may be the better file.'; }
    return line + '. That is the same size.';
  }'''

UPLOADS = {'image_favicon': 'logo.png'}


def curl(operation, fields, upload=None):
    lines = ['curl -s -X POST https://aisenseapi.com/services/v1/' + operation, '  -F "file=@%s"' % ( upload or UPLOADS.get(operation, 'photo.jpg') )]
    lines += ['  -F "%s=%s"' % (name, value) for name, value in (fields or {}).items()]
    return (' ' + B + '\n').join(lines)


def answer_json(operation):
    return json.dumps(json.loads(RESULTS[operation]['answer'], object_pairs_hook=OrderedDict), indent=2, ensure_ascii=False)


def example(key):
    run = RESULTS[key]
    operation = json.loads(run['answer'])['operation']
    return html.escape(curl(operation, run['fields'], run.get('upload')), quote=False) + '\n\n' + html.escape(answer_json(key), quote=False)


def stored_json(operation):
    return json.loads(RESULTS[operation]['stored'], object_pairs_hook=OrderedDict)


def page(slug, title, description, h1, lede, badges, operation, tool_html, body_html, script, faq, api_name, example_key=None):
    ld = OrderedDict([
        ('@context', 'https://schema.org'),
        ('@graph', [
            OrderedDict([
                ('@type', 'WebAPI'),
                ('name', api_name),
                ('url', 'https://aisense.no/' + slug),
                ('documentation', 'https://aisense.no/' + slug),
                ('termsOfService', 'https://aisense.no/terms'),
                ('description', description),
                ('inLanguage', 'en'),
                ('provider', PROVIDER),
                ('potentialAction', OrderedDict([
                    ('@type', 'ConsumeAction'),
                    ('target', OrderedDict([
                        ('@type', 'EntryPoint'),
                        ('urlTemplate', 'https://aisenseapi.com/services/v1/' + operation),
                        ('httpMethod', 'POST'),
                        ('contentType', 'multipart/form-data'),
                        ('encodingType', 'application/json')
                    ]))
                ]))
            ]),
            OrderedDict([
                ('@type', 'FAQPage'),
                ('mainEntity', [
                    OrderedDict([
                        ('@type', 'Question'),
                        ('name', q),
                        ('acceptedAnswer', OrderedDict([('@type', 'Answer'), ('text', a)]))
                    ]) for q, a in faq
                ])
            ]),
            OrderedDict([
                ('@type', 'BreadcrumbList'),
                ('itemListElement', [
                    OrderedDict([('@type', 'ListItem'), ('position', 1), ('name', 'Home'), ('item', 'https://aisense.no/')]),
                    OrderedDict([('@type', 'ListItem'), ('position', 2), ('name', 'Free public REST APIs'), ('item', 'https://aisense.no/free-public-apis')]),
                    OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', h1)])
                ])
            ])
        ])
    ])
    faq_html = '\n\n'.join('<h3>%s</h3>\n<p>%s</p>' % (html.escape(q, quote=False), html.escape(a, quote=False)) for q, a in faq)
    badge_html = '\n'.join('      <span>%s</span>' % b for b in badges)
    out = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="canonical" href="https://aisense.no/%(slug)s">

<meta property="og:type" content="website">
<meta property="og:site_name" content="AI SENSE">
<meta property="og:title" content="%(h1)s - AI SENSE">
<meta property="og:description" content="%(description)s">
<meta property="og:url" content="https://aisense.no/%(slug)s">
<meta name="twitter:card" content="summary">

<link rel="stylesheet" href="/assets/aisense.css">
<link rel="stylesheet" href="/assets/aisense-tools.css?v=20260930">

<script type="application/ld+json">
%(ld)s
</script>

<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
</head>
<body>

%(header)s

<main>

<nav class="breadcrumbs" aria-label="Breadcrumb">
  <a href="/">Home</a> / <a href="/free-public-apis">Free public REST APIs</a> / %(h1)s
</nav>

<div class="hero">
  <h1>%(h1)s</h1>
  <p class="lede">%(lede)s</p>

  <div class="tool-lead-api">
    <div class="api-window">
      <div class="api-window-bar">The whole API</div>
      <div class="api-window-body"><pre><code>%(example)s</code></pre></div>
    </div>
    <div class="tool-badges">
%(badges)s
    </div>
  </div>
</div>

<h2 id="try">Try it in the browser</h2>
<p>This form posts your image to the same endpoint and shows the stored result. The image is sent to aisenseapi.com, and the result is kept for 24 hours at a link that anyone with the link can open.</p>

<div class="tool-card">
  <noscript>
    <p class="tool-noscript"><strong>The form needs JavaScript.</strong> The endpoint itself is plain HTTP and works from curl, a script or an agent. The request is at the top of the page.</p>
  </noscript>
%(tool)s
</div>

%(body)s

<h2 id="faq">Questions</h2>

%(faq)s

%(related)s

</main>

%(footer)s

<script src="/assets/aisense-tools.js"></script>
<script>
%(script)s
</script>

</body>
</html>
''' % {
        'title': title,
        'description': description,
        'slug': slug,
        'h1': h1,
        'lede': lede,
        'example': example(example_key or operation),
        'badges': badge_html,
        'tool': tool_html,
        'body': wrap_tables(body_html),
        'faq': faq_html,
        'related': RELATED,
        'header': HEADER,
        'footer': FOOTER,
        'script': script.strip('\n'),
        'ld': json.dumps(ld, indent=2, ensure_ascii=False)
    }
    io.open(WEB + '/' + slug + '.html', 'w', encoding='utf-8', newline='\n').write(out)
    print('wrote', slug + '.html', len(out.encode('utf-8')), 'bytes')


FAQ_FREE = 'Yes. No API key, no account and no sign up. The limit is 5000 requests per IP address per 24 hours, and stored results count against the Storage budget of 80 MB per IP address per day.'


def wrap_tables(body):
    """Each table in a table-wrap, which scrolls when the table is wider than a phone."""
    wrapped = body.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
    if wrapped.count('<div class="table-wrap"><table>') != wrapped.count('</table></div>') or '<table ' in body:
        raise SystemExit('a table the wrap does not match')
    return wrapped


def answer_table(rows):
    return '''<table>
  <thead><tr><th>Field</th><th>Meaning</th></tr></thead>
  <tbody>
''' + STORAGE_ROWS + '\n' + rows + '''
  </tbody>
</table>'''


# The converter script, shared by the image converter and the HEIC page.
CONVERT_SCRIPT = script_start(['jpeg', 'png', 'webp', 'heic'], 'JPEG, PNG, WebP or HEIC', r'''  var format = document.getElementById('tool-format');
  var quality = document.getElementById('tool-quality');
  var qualityValue = document.getElementById('tool-quality-value');
  var qualityField = document.getElementById('tool-quality-field');
  var lossless = document.getElementById('tool-lossless');
  var losslessField = document.getElementById('tool-lossless-field');
''') + SCRIPT_CHOOSE + SCRIPT_SUMMARY + r'''

  function refresh() {
    losslessField.hidden = format.value !== 'webp';
    if (format.value !== 'webp') { lossless.checked = false; }
    qualityField.hidden = format.value === 'png' || lossless.checked;
    qualityValue.textContent = quality.value;
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, refresh);
  });
  format.addEventListener('change', refresh);
  lossless.addEventListener('change', refresh);
  quality.addEventListener('input', refresh);

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    var fields = { format: format.value };
    if (format.value === 'webp' && lossless.checked) {
      fields.lossless = 'true';
    } else if (format.value !== 'png') {
      fields.quality = quality.value;
    }
    T.busy(result, 'Converting...');
    submit.disabled = true;
    T.postFile('image_convert', file, fields).then(function (answer) {
      T.showStored(result, answer, { image: true, summary: summary(answer) });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });

  refresh();
})();'''

# -- The image converter -------------------------------------------------------

page(
    'free-image-converter-api',
    'Free image converter API: HEIC, WebP, PNG and JPEG | AI SENSE',
    'Convert images between WebP, PNG and JPEG, and HEIC from an iPhone to any of them, in your browser or with one API call. EXIF and GPS data are removed, the colour profile is kept, and the result is a link that lasts 24 hours. No API key.',
    'Free image converter: HEIC, WebP, PNG and JPEG',
    'Drop an image and choose WebP, PNG or JPEG. HEIC photos from an iPhone work too. The form calls the same free API your code can call: one POST, no API key and no account. The converted image waits in Storage for 24 hours, with the camera and GPS data removed.',
    ['No API key', 'No account', 'HEIC, WebP, PNG and JPEG', 'EXIF removed', '5000 req / IP / 24h'],
    'image_convert',
    '''  <form id="tool-form">
''' + drop('JPEG, PNG, WebP or HEIC', ACCEPT_HEIC) + '''
    <div class="tool-options">
      <div class="tool-field">
        <label for="tool-format">Convert to</label>
        <select id="tool-format">
          <option value="webp" selected>WebP</option>
          <option value="png">PNG</option>
          <option value="jpeg">JPEG</option>
        </select>
      </div>
      <div class="tool-field" id="tool-quality-field">
        <label for="tool-quality">Quality: <output id="tool-quality-value" for="tool-quality">82</output></label>
        <input type="range" id="tool-quality" min="40" max="95" step="1" value="82">
      </div>
      <label class="tool-check" id="tool-lossless-field"><input type="checkbox" id="tool-lossless"> Lossless</label>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Convert</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="how">How the conversion works</h2>
<ul>
  <li><strong>JPEG, PNG, WebP and HEIC in, JPEG, PNG or WebP out.</strong> The format is read from the file itself, not from its name. An animated image is converted from its first frame.</li>
  <li><strong>HEIC from an iPhone</strong> is turned the way the phone stored it, once, and keeps its colour profile, so the colours of a Display P3 photo stay right. HEIC can be read but not written.</li>
  <li><strong>Quality</strong> goes from 40 to 95 for JPEG and WebP, and is 82 when you send none. PNG is lossless and takes no quality.</li>
  <li><strong>Lossless WebP</strong> keeps every pixel. For screenshots and graphics it is usually far smaller than PNG.</li>
  <li><strong>Transparency</strong> is kept in PNG and WebP. JPEG has none, so transparent pixels become white.</li>
  ''' + METADATA + '''
  <li><strong>Nothing is resized.</strong> The result has the width and height of the upload, turned upright. The <a href="/free-image-resizer-api">image resizer</a> makes a new size.</li>
</ul>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_convert</code> with <code>multipart/form-data</code>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The image: JPEG, PNG, WebP or HEIC.</td></tr>
    <tr><td><code>format</code></td><td>yes</td><td><code>jpeg</code>, <code>png</code> or <code>webp</code>. <code>jpg</code> is read as <code>jpeg</code>.</td></tr>
    <tr><td><code>quality</code></td><td>no</td><td>40 to 95, for JPEG and WebP. 82 when left out.</td></tr>
    <tr><td><code>lossless</code></td><td>no</td><td><code>true</code> or <code>false</code>, for WebP only. Lossless takes no quality.</td></tr>
  </tbody>
</table>
<p>A GET on <code>storage_url</code> returns the image with its own image type, so the link also works in an <code>&lt;img&gt;</code> tag.</p>

''' + STORAGE_SECTION + '''

''' + LIMITS + '''

''' + ERRORS_CONVERT,
    CONVERT_SCRIPT,
    [
        ('Is the image converter API free?', FAQ_FREE),
        ('Does it keep transparency?', 'In PNG and WebP, yes. JPEG has no transparency, so transparent pixels become white.'),
        ('Is the GPS position removed?', 'Yes. EXIF, XMP, IPTC and comments are removed from every result. The colour profile is kept, so the colours stay the same.'),
        ('Can it convert HEIC or GIF?', 'HEIC, yes: a photo from an iPhone becomes a JPEG, PNG or WebP, turned the right way and with its colour profile. GIF, no.')
    ],
    'Free image converter API'
)

# -- HEIC to JPG ------------------------------------------------------------------

page(
    'free-heic-to-jpg-converter',
    'Free HEIC to JPG Converter: iPhone Photos to JPEG | AI SENSE',
    'Convert iPhone HEIC photos to JPG, PNG or WebP in your browser or with one API call. Turned the right way, colours kept, GPS removed. Free, no account.',
    'Free HEIC to JPG converter',
    'Drop a HEIC photo from an iPhone and get a JPG back, turned the right way, with its colours and without its GPS position. The form calls the same free API your code can call: one POST, no API key and no account. The JPG waits in Storage for 24 hours.',
    ['No API key', 'No account', 'HEIC to JPG, PNG or WebP', 'GPS removed', 'Colours kept'],
    'image_convert',
    """  <form id="tool-form">
""" + drop('HEIC, JPEG, PNG or WebP', ACCEPT_HEIC) + """
    <div class="tool-options">
      <div class="tool-field">
        <label for="tool-format">Convert to</label>
        <select id="tool-format">
          <option value="jpeg" selected>JPG (JPEG)</option>
          <option value="png">PNG</option>
          <option value="webp">WebP</option>
        </select>
      </div>
      <div class="tool-field" id="tool-quality-field">
        <label for="tool-quality">Quality: <output id="tool-quality-value" for="tool-quality">82</output></label>
        <input type="range" id="tool-quality" min="40" max="95" step="1" value="82">
      </div>
      <label class="tool-check" id="tool-lossless-field"><input type="checkbox" id="tool-lossless"> Lossless</label>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Convert</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>""",
    """<h2 id="what">What HEIC is, and why convert it</h2>
<p>HEIC is the format an iPhone has saved photos in since iOS 11. It stores a photo in less space than JPEG, which is why Apple uses it, but many websites, upload forms and programs cannot open it, and Windows needs extra extensions from the Microsoft Store to show it. A JPG opens everywhere.</p>
<p>The JPG is usually somewhat larger than the HEIC it came from, as in the example at the top of the page: 84 381 bytes of HEIC became 98 701 bytes of JPG at quality 82. That is the price of a format everything can read.</p>

<h2 id="how">How the conversion works</h2>
<ul>
  <li><strong>Turned the right way, once.</strong> An iPhone records how a photo is turned twice, once in the HEIC file for HEIC readers and once in EXIF. A converter that applies both turns a portrait sideways. This one applies it once, and we test that with a file built the way an iPhone builds one.</li>
  <li><strong>The colours are kept.</strong> A recent iPhone takes photos in the Display P3 colour space. The colour profile is read from the HEIC file and written into the JPG, so the colours look the same.</li>
  <li><strong>The GPS position is removed</strong>, with the rest of EXIF, XMP and comments, so the JPG does not say where or with what it was taken.</li>
  <li><strong>JPG, PNG or WebP out.</strong> JPG takes a quality from 40 to 95 and is 82 when you send none. PNG is lossless and much larger. WebP is smaller than JPG at the same quality.</li>
  <li><strong>The main photo only.</strong> Depth maps and other extra images inside the HEIC file are left out, and nothing is resized.</li>
</ul>

<h2 id="iphone">HEIC on the iPhone itself</h2>
<p>Two settings decide whether an iPhone hands out HEIC at all:</p>
<ul>
  <li><strong>Settings, Camera, Formats, Most Compatible</strong> makes the camera save new photos as JPG instead of HEIC. Photos already taken stay HEIC.</li>
  <li><strong>Settings, Photos, Transfer to Mac or PC, Automatic</strong> converts photos to JPG when they are copied to a computer by cable.</li>
</ul>
<p>Photos sent another way, or already on a computer as HEIC, are what this converter is for. <a href="/remove-gps-location-and-exif-data-from-photos">The guide to the location in photos</a> has more on what an iPhone photo can carry.</p>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_convert</code> with <code>multipart/form-data</code>, the same endpoint as the <a href="/free-image-converter-api">image converter</a>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The photo: HEIC, JPEG, PNG or WebP.</td></tr>
    <tr><td><code>format</code></td><td>yes</td><td><code>jpeg</code>, <code>png</code> or <code>webp</code>. <code>jpg</code> is read as <code>jpeg</code>.</td></tr>
    <tr><td><code>quality</code></td><td>no</td><td>40 to 95, for JPG and WebP. 82 when left out.</td></tr>
    <tr><td><code>lossless</code></td><td>no</td><td><code>true</code> or <code>false</code>, for WebP only.</td></tr>
  </tbody>
</table>
<p>A folder of photos is converted with one request per photo. At most two images are converted at a time, so a script should wait the seconds in <code>Retry-After</code> when it gets 503.</p>

""" + STORAGE_SECTION + """

""" + LIMITS.replace('<li>The upload is at most 10 MB and 25 megapixels.</li>',
                     '<li>The upload is at most 10 MB and 25 megapixels. The default photos of recent iPhones, 12 or 24 megapixels, are within the limit; a 48 megapixel photo taken with HEIF Max is not.</li>') + """

""" + ERRORS_CONVERT,
    CONVERT_SCRIPT,
    [
        ('Is the HEIC to JPG converter free?', FAQ_FREE),
        ('Does it work on Windows?', 'Yes. The conversion happens on the server, so the browser only sends the file. No extension or app is needed.'),
        ('Is the location removed?', 'Yes. EXIF with the GPS position, XMP and comments are removed from every result. The colour profile is kept.'),
        ('Will my photo be turned the right way?', 'Yes. An iPhone records the turn both in the HEIC file and in EXIF, and the converter applies it once.'),
        ('Does it keep the quality?', 'JPG is saved at quality 82 unless you choose from 40 to 95. For the least loss choose 95, or PNG, which is lossless but much larger.'),
        ('Can it convert HEIF and AVIF?', 'HEIC and other HEIF files with HEVC inside, yes. AVIF, no.')
    ],
    'Free HEIC to JPG converter API',
    'heic_convert'
)

# -- The image resizer ------------------------------------------------------------

page(
    'free-image-resizer-api',
    'Free image resizer API: resize JPEG, PNG, WebP and HEIC | AI SENSE',
    'Resize a JPEG, PNG, WebP or iPhone HEIC to a width, a height or a square thumbnail, in the browser or with one API call. Never enlarged unless asked. Free.',
    'Free image resizer',
    'Drop an image and give it a new width, a new height or both: fitted inside the box with all of the picture kept, or filling the box as a thumbnail cut from the centre. It is never enlarged unless you ask. The form calls the same free API your code can call: one POST, no API key and no account. The result waits in Storage for 24 hours.',
    ['No API key', 'No account', 'Keeps the aspect ratio', 'Square thumbnails', 'HEIC in'],
    'image_resize',
    """  <form id="tool-form">
""" + drop('JPEG, PNG, WebP or HEIC', ACCEPT_HEIC) + """
    <div class="tool-options">
      <div class="tool-field">
        <label for="tool-width">Width in pixels</label>
        <input type="number" id="tool-width" min="1" max="10000" step="1" inputmode="numeric" placeholder="800">
      </div>
      <div class="tool-field">
        <label for="tool-height">Height in pixels</label>
        <input type="number" id="tool-height" min="1" max="10000" step="1" inputmode="numeric" placeholder="Optional">
      </div>
      <div class="tool-field">
        <label for="tool-fit">Fit</label>
        <select id="tool-fit">
          <option value="contain" selected>Contain: keep all of it</option>
          <option value="cover">Cover: fill and crop</option>
        </select>
      </div>
      <div class="tool-field">
        <label for="tool-format">Format</label>
        <select id="tool-format">
          <option value="" selected>Keep the format</option>
          <option value="jpeg">JPG (JPEG)</option>
          <option value="png">PNG</option>
          <option value="webp">WebP</option>
        </select>
      </div>
      <label class="tool-check"><input type="checkbox" id="tool-upscale"> Enlarge a smaller image</label>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Resize</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>""",
    """<h2 id="how">How the resize works</h2>
<ul>
  <li><strong>Contain</strong>, the default, fits all of the picture inside the width and height you give, and keeps its aspect ratio. Give one side only and the other follows.</li>
  <li><strong>Cover</strong> fills the box exactly and cuts what sticks out from the centre, which is what a square thumbnail or a fixed-size card needs. It needs both a width and a height.</li>
  <li><strong>Nothing is enlarged unless you ask.</strong> A picture already smaller than the box keeps its size; with cover, only what sticks out is cut. Send <code>upscale=true</code> to enlarge, and the answer says <code>upscaled: true</code> when it happened.</li>
  <li><strong>The format stays</strong> unless you name another. A HEIC from an iPhone comes out as JPEG, since HEIC is read but not written.</li>
  """ + METADATA + """
</ul>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_resize</code> with <code>multipart/form-data</code>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The image: JPEG, PNG, WebP or HEIC.</td></tr>
    <tr><td><code>width</code>, <code>height</code></td><td>one of them</td><td>The box in pixels, from 1 to 10000.</td></tr>
    <tr><td><code>fit</code></td><td>no</td><td><code>contain</code> or <code>cover</code>. <code>contain</code> when left out; <code>cover</code> needs both sides.</td></tr>
    <tr><td><code>upscale</code></td><td>no</td><td><code>true</code> to let a smaller picture be enlarged. <code>false</code> when left out.</td></tr>
    <tr><td><code>format</code></td><td>no</td><td><code>jpeg</code>, <code>png</code> or <code>webp</code>. The format of the upload when left out, and JPEG for a HEIC.</td></tr>
    <tr><td><code>quality</code>, <code>lossless</code></td><td>no</td><td>As on the <a href="/free-image-converter-api">image converter</a>: 40 to 95 for JPEG and WebP, 82 when left out, and <code>lossless</code> for WebP.</td></tr>
  </tbody>
</table>
<p>The answer has the Storage fields, <code>width</code> and <code>height</code> of the result, and <code>input_width</code> and <code>input_height</code>, the size of the upload once turned upright. <code>fit</code> repeats the fit, and <code>upscaled</code> says whether the picture was enlarged.</p>

""" + STORAGE_SECTION + """

""" + LIMITS.replace('<li>The upload is at most 10 MB and 25 megapixels.</li>',
                     '<li>The upload is at most 10 MB and 25 megapixels, and so is an enlarged result. A width or height is at most 10000 pixels.</li>') + """

""" + ERRORS_CONVERT,
    script_start(['jpeg', 'png', 'webp', 'heic'], 'JPEG, PNG, WebP or HEIC', r"""  var width = document.getElementById('tool-width');
  var height = document.getElementById('tool-height');
  var fit = document.getElementById('tool-fit');
  var format = document.getElementById('tool-format');
  var upscale = document.getElementById('tool-upscale');
""") + SCRIPT_CHOOSE + r"""

  function summary(answer) {
    var line = names[answer.input_format] + ', ' + answer.input_width + ' x ' + answer.input_height + ' pixels, ' + T.bytes(answer.input_bytes)
      + ', became ' + names[answer.format] + ', ' + answer.width + ' x ' + answer.height + ' pixels, ' + T.bytes(answer.bytes) + '.';
    if (answer.upscaled) { return line + ' It was enlarged, so it can look softer than the original.'; }
    if (answer.width === answer.input_width && answer.height === answer.input_height) { return line + ' It already fitted, so only the metadata and the format were changed.'; }
    return line;
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, function () {});
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    var fields = { fit: fit.value };
    if (width.value) { fields.width = width.value; }
    if (height.value) { fields.height = height.value; }
    if (format.value) { fields.format = format.value; }
    if (upscale.checked) { fields.upscale = 'true'; }
    if (!fields.width && !fields.height) {
      var missing = new Error('Give a width, a height or both.');
      missing.fix = 'Type the size in pixels, for example 800.';
      T.showError(result, missing);
      return;
    }
    if (fields.fit === 'cover' && !(fields.width && fields.height)) {
      var both = new Error('Cover needs both a width and a height.');
      both.fix = 'Give both, for example 400 and 400 for a square thumbnail.';
      T.showError(result, both);
      return;
    }
    T.busy(result, 'Resizing...');
    submit.disabled = true;
    T.postFile('image_resize', file, fields).then(function (answer) {
      T.showStored(result, answer, { image: true, summary: summary(answer) });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });
})();""",
    [
        ('Is the image resizer API free?', FAQ_FREE),
        ('Does it keep the aspect ratio?', 'Yes. Contain fits all of the picture inside the box, and cover fills the box and cuts what sticks out from the centre. Neither stretches the picture.'),
        ('How do I make a square thumbnail?', 'Send the same width and height with fit=cover, for example 400 and 400. The picture fills the square and is cut from the centre.'),
        ('Will it enlarge a small image?', 'Only if you send upscale=true. Otherwise a picture already smaller than the box keeps its size, and the answer says upscaled: false.'),
        ('Can it resize iPhone photos?', 'Yes. It reads HEIC, turns the photo upright, keeps its colour profile and gives back a JPEG unless you ask for PNG or WebP.'),
        ('Is the location removed?', 'Yes. EXIF with the GPS position, XMP, IPTC and comments are removed from every result. The colour profile is kept.')
    ],
    'Free image resizer API',
    'image_resize'
)

# -- Image compression ----------------------------------------------------------

page(
    'free-image-compression-api',
    'Free image compression API: JPEG, PNG and WebP | AI SENSE',
    'Make a JPEG, PNG or WebP smaller in your browser or with one API call, in the same format. EXIF and GPS data are removed and the colour profile is kept. No API key.',
    'Free image compression API',
    'Drop a JPEG, PNG or WebP and get it back in the same format, saved again to be smaller, with the camera and GPS data removed. The form calls the same free API your code can call: one POST, no API key and no account. The result waits in Storage for 24 hours.',
    ['No API key', 'No account', 'Same format out', 'EXIF removed', '5000 req / IP / 24h'],
    'image_compress',
    '''  <form id="tool-form">
''' + DROP + '''
    <div class="tool-options">
      <div class="tool-field" id="tool-quality-field">
        <label for="tool-quality">Quality: <output id="tool-quality-value" for="tool-quality">82</output></label>
        <input type="range" id="tool-quality" min="40" max="95" step="1" value="82">
        <small id="tool-quality-note">Lower is smaller. For JPEG and WebP only.</small>
      </div>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Compress</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="how">How the compression works</h2>
<ul>
  <li><strong>The format stays the same.</strong> A JPEG comes back a JPEG, a PNG a PNG and a WebP a WebP. The <a href="/free-image-converter-api">image converter</a> changes the format.</li>
  <li><strong>JPEG and WebP are saved again at the quality you choose</strong>, 82 when you choose none. That is lossy: the lower the quality, the smaller the file and the more fine detail is lost.</li>
  <li><strong>PNG is saved again losslessly</strong> with the strongest zlib compression. Every pixel stays the same, and PNG takes no quality.</li>
  ''' + METADATA + '''
  <li><strong>Nothing is resized.</strong> An image the EXIF data marks as rotated is turned upright, which swaps its width and height; any other keeps both. The <a href="/free-image-resizer-api">image resizer</a> makes a new size.</li>
  <li><strong>The answer says what was saved.</strong> <code>input_bytes</code> is the upload and <code>bytes</code> the result. An image that was already saved at a lower quality, or compressed well already, can come out larger. Then keep the original.</li>
</ul>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_compress</code> with <code>multipart/form-data</code>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The image: JPEG, PNG or WebP.</td></tr>
    <tr><td><code>quality</code></td><td>no</td><td>40 to 95, for JPEG and WebP. 82 when left out. A PNG takes none.</td></tr>
  </tbody>
</table>
<p>A <code>format</code> field is refused; the result always has the format of the upload. A GET on <code>storage_url</code> returns the image with its own image type.</p>

''' + STORAGE_SECTION + '''

''' + LIMITS + '''

''' + ERRORS,
    script_start(['jpeg', 'png', 'webp'], 'JPEG, PNG or WebP', r'''  var quality = document.getElementById('tool-quality');
  var qualityValue = document.getElementById('tool-quality-value');
  var qualityField = document.getElementById('tool-quality-field');
''') + SCRIPT_CHOOSE + SCRIPT_SUMMARY + r'''

  function refresh() {
    qualityField.hidden = chosenFormat === 'png';
    qualityValue.textContent = quality.value;
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, refresh);
  });
  quality.addEventListener('input', refresh);

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    var fields = chosenFormat === 'png' ? {} : { quality: quality.value };
    T.busy(result, 'Compressing...');
    submit.disabled = true;
    T.postFile('image_compress', file, fields).then(function (answer) {
      T.showStored(result, answer, { image: true, summary: summary(answer) });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });

  refresh();
})();''',
    [
        ('Is the image compression API free?', FAQ_FREE),
        ('Is the compression lossless?', 'For PNG, yes. JPEG and WebP are saved again at the quality you choose, which is lossy.'),
        ('Why is my result larger than the upload?', 'The image was already compressed harder than the quality you chose. Keep the original, or choose a lower quality.'),
        ('Does it resize the image?', 'No. An image the EXIF data marks as rotated is turned upright, which swaps its width and height. Any other image keeps both. The free image resizer makes a new size.')
    ],
    'Free image compression API'
)

# -- The metadata viewer --------------------------------------------------------

REPORT = stored_json('image_metadata')
EXCERPT = OrderedDict([('gps', REPORT['gps']), ('privacy', REPORT['privacy'])])

page(
    'free-image-metadata-viewer-api',
    'Free image metadata viewer API: EXIF, GPS and XMP | AI SENSE',
    'See everything a JPEG, PNG or WebP carries besides its pixels: EXIF with the GPS position and the camera, XMP, IPTC, the colour profile and hidden extra images, with a privacy summary. In your browser or with one API call. No API key.',
    'Free image metadata viewer: EXIF, GPS and XMP',
    'Drop an image and see what it says about where, when and with what it was taken. The form calls the same free API your code can call: one POST, no API key and no account. The full report is kept in Storage for 24 hours as JSON.',
    ['No API key', 'No account', 'EXIF, XMP and IPTC', 'GPS in decimal degrees', 'Privacy summary'],
    'image_metadata',
    '''  <form id="tool-form">
''' + DROP + '''
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Read the metadata</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="how">What the report holds</h2>
<p>The image is read, not decoded. The endpoint walks the segments of a JPEG, the chunks of a PNG or the chunks of a WebP and reports what it finds there, as JSON in these parts:</p>
<table>
  <thead><tr><th>Part</th><th>What it holds</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>Format, size in bytes, width, height and megapixels, and what the format tells: the estimated JPEG quality, bit depth, progressive or interlaced, lossy or lossless WebP.</td></tr>
    <tr><td><code>orientation</code></td><td>The EXIF orientation as a number and in words, such as 6 and Rotated 90 degrees clockwise.</td></tr>
    <tr><td><code>color_profile</code></td><td>The ICC colour profile: its name, colour space, device class, version and size.</td></tr>
    <tr><td><code>exif</code></td><td>Every EXIF tag by name, in <code>image</code>, <code>photo</code>, <code>gps</code>, <code>interoperability</code> and <code>thumbnail</code>. An exposure time is written as 1/250, and a maker note by its size only.</td></tr>
    <tr><td><code>gps</code></td><td>Latitude and longitude in decimal degrees, the altitude in metres and the time in UTC, from the EXIF GPS tags.</td></tr>
    <tr><td><code>xmp</code></td><td>The fields of the XMP packet, such as <code>dc:creator</code>, <code>photoshop:City</code> and <code>xmp:CreatorTool</code>.</td></tr>
    <tr><td><code>iptc</code></td><td>IPTC fields such as <code>By-line</code>, <code>City</code>, <code>Keywords</code> and <code>Caption-Abstract</code>.</td></tr>
    <tr><td><code>comments</code>, <code>text</code></td><td>JPEG comments, and the text chunks of a PNG by their keywords.</td></tr>
    <tr><td><code>embedded</code></td><td>What else is inside: an EXIF thumbnail, a multi-picture index, and data after the end of the image, where phones keep depth maps and HDR gain maps.</td></tr>
    <tr><td><code>privacy</code></td><td>What can identify a person, a place, a device or a time, most sensitive first, each with <code>item</code>, <code>level</code> and <code>why</code>.</td></tr>
  </tbody>
</table>
<p>A part the file does not have is <code>null</code> or empty. Long values are cut short, and a report is at most 2 MB.</p>

<h2 id="privacy">The privacy summary</h2>
<p>The <code>privacy</code> list in the report, and <code>findings</code> in the answer, can name these items:</p>
<ul>
  <li><strong>GPS position</strong>, high: where the picture was taken, to within metres.</li>
  <li><strong>Location in XMP</strong>, high: a place an editing program recorded.</li>
  <li><strong>Serial number or unique ID</strong>, high: it links the picture to other pictures from the same camera.</li>
  <li><strong>Names</strong>, medium: an author, owner or copyright holder.</li>
  <li><strong>Place names in IPTC</strong>, medium: a city or location written into the file.</li>
  <li><strong>Camera or phone</strong>, medium: the make and model.</li>
  <li><strong>Date and time</strong>, medium: when the picture was taken or last changed.</li>
  <li><strong>EXIF thumbnail</strong>, <strong>JFIF thumbnail</strong>, <strong>Multi-picture index (MPF)</strong> and <strong>Data after the end of the image</strong>, medium: extra image data that can show more than the picture itself, such as the uncropped original.</li>
  <li><strong>Descriptions and comments</strong>, low: free text written into the file.</li>
  <li><strong>Software</strong>, low: the program that made or edited the file.</li>
</ul>
<p>The <a href="/free-exif-remover-api">EXIF remover</a> takes all of it out without touching the pixels.</p>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_metadata</code> with <code>multipart/form-data</code> and one field, <code>file</code>. The report is stored as <code>metadata.json</code>, and the answer holds the Storage fields and a short version of it:</p>
''' + answer_table('''    <tr><td><code>content_type</code>, <code>filename</code></td><td><code>application/json</code> and <code>metadata.json</code>.</td></tr>
    <tr><td><code>operation</code>, <code>format</code>, <code>width</code>, <code>height</code></td><td><code>image_metadata</code>, and the format and size of the image.</td></tr>
    <tr><td><code>gps</code></td><td><code>true</code> when the image carries a GPS position.</td></tr>
    <tr><td><code>findings</code></td><td>The items of the privacy summary, most sensitive first. Empty when nothing was found.</td></tr>''') + '''
<p>The example at the top of the page comes from a test run with a test photo of 1600 x 1200 pixels, given made-up EXIF data: a camera, a serial number, a date, software and a GPS position at the Oslo Opera House. Part of the stored report:</p>
<pre><code>''' + html.escape(json.dumps(EXCERPT, indent=2, ensure_ascii=False), quote=False) + '''</code></pre>
<p>Anyone with the link can read the report until it expires, and a report can hold a GPS position, so keep the link to yourself for a private photo. Stored reports count against the Storage budget of 80 MB per IP address per day.</p>

''' + LIMITS_READ % 'The report is at most 2 MB.' + '''

''' + ERRORS_READ,
    script_start(['jpeg', 'png', 'webp'], 'JPEG, PNG or WebP') + SCRIPT_CHOOSE + r'''

  function findings(report) {
    var box = T.make('div', 'tool-findings');
    var items = report.privacy || [];
    if (!items.length) {
      box.appendChild(T.make('p', 'tool-status is-good', 'Nothing in the file names a person, a place, a device or a time.'));
      return box;
    }
    box.appendChild(T.make('p', 'tool-status', 'What the image gives away'));
    var list = T.make('ul');
    items.forEach(function (item) {
      var row = T.make('li', item.level === 'high' ? 'is-high' : (item.level === 'medium' ? 'is-medium' : 'is-low'));
      row.appendChild(T.make('strong', '', item.item));
      row.appendChild(document.createTextNode(', ' + item.level + ': ' + item.why));
      list.appendChild(row);
    });
    box.appendChild(list);
    var gps = report.gps;
    if (gps && gps.latitude !== null && gps.longitude !== null) {
      box.appendChild(T.make('p', 'tool-meta', 'GPS position: ' + gps.latitude + ', ' + gps.longitude
        + (gps.altitude_m !== null ? ', ' + gps.altitude_m + ' m' : '') + '.'));
    }
    return box;
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, function () {});
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    T.busy(result, 'Reading...');
    submit.disabled = true;
    T.postFile('image_metadata', file, {}).then(function (answer) {
      var line = names[answer.format] + ', ' + answer.width + ' x ' + answer.height + ' pixels. '
        + (answer.findings.length ? 'It carries ' + answer.findings.length + ' kinds of information about who, where, when or what.' : 'It carries nothing personal.');
      return T.showStored(result, answer, { summary: line, preview: true }).then(function (text) {
        var report = null;
        try { report = JSON.parse(text); } catch (e) { report = null; }
        if (report) { result.insertBefore(findings(report), result.children[1] || null); }
      });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });
})();''',
    [
        ('Is the image metadata API free?', FAQ_FREE),
        ('Does it show the GPS position?', 'Yes. The GPS tags are given as latitude and longitude in decimal degrees, with the altitude in metres and the time in UTC, and the privacy summary lists the position first.'),
        ('Is my image stored?', 'No. The image is read and dropped. Only the JSON report is stored, for 24 hours, at a link that anyone with the link can open.'),
        ('Can it read HEIC?', 'No. It reads JPEG, PNG and WebP. The image converter reads HEIC and removes the metadata on the way.')
    ],
    'Free image metadata viewer API'
)

# -- The EXIF remover -----------------------------------------------------------

STRIP = json.loads(RESULTS['image_strip']['answer'])

page(
    'free-exif-remover-api',
    'Free EXIF remover API: remove GPS and metadata from photos | AI SENSE',
    'Remove EXIF, GPS, XMP, IPTC and comments from a JPEG, PNG or WebP without saving it again: the pixels stay exactly as they were. In your browser or with one API call. No API key.',
    'Free EXIF remover: metadata out, pixels untouched',
    'Drop a JPEG, PNG or WebP and get the same picture back without EXIF, GPS, XMP, IPTC or comments. The image data is copied byte for byte, so nothing is lost. The form calls the same free API your code can call: one POST, no API key and no account.',
    ['No API key', 'No account', 'Not saved again', 'GPS removed', 'Colour profile kept'],
    'image_strip',
    '''  <form id="tool-form">
''' + DROP + '''
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Remove the metadata</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="how">How it works</h2>
<ul>
  <li><strong>The file is rewritten, not saved again.</strong> The endpoint walks the segments of a JPEG, the chunks of a PNG or the chunks of a WebP and writes them out again without the metadata. The compressed image data is copied byte for byte, so the pixels are exactly the ones you sent.</li>
  <li><strong>From a JPEG</strong> it removes EXIF with its GPS directory and thumbnail, XMP, IPTC and other Photoshop data, comments, the multi-picture index, other application segments, and whatever follows the end of the image, where phones keep depth maps and HDR gain maps.</li>
  <li><strong>From a PNG</strong> it removes the text chunks, XMP, EXIF and the time of last change.</li>
  <li><strong>From a WebP</strong> it removes the EXIF and XMP chunks.</li>
  <li><strong>The colour profile is kept</strong>, so the colours look the same, and so are the JFIF header and the Adobe colour transform of a JPEG.</li>
  <li><strong>The orientation is kept.</strong> A photo the camera marked as rotated gets a new EXIF with its orientation alone, so it still shows the right way up. Nothing else is written back.</li>
</ul>
<p>The <a href="/free-image-converter-api">image converter</a> and <a href="/free-image-compression-api">image compression</a> remove metadata too, but they save the image again. This endpoint does not, so it is the one to use when the pixels must not change. The <a href="/free-image-metadata-viewer-api">image metadata viewer</a> shows what a file carries before you remove it.</p>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_strip</code> with <code>multipart/form-data</code> and one field, <code>file</code>. Any other field is refused. The result is stored in the format of the upload, and the answer holds the Storage fields and what was done:</p>
''' + answer_table('''    <tr><td><code>content_type</code>, <code>filename</code></td><td>The image type, and <code>result.jpg</code>, <code>result.png</code> or <code>result.webp</code>.</td></tr>
    <tr><td><code>operation</code>, <code>format</code>, <code>width</code>, <code>height</code></td><td><code>image_strip</code>, and the format and size of the image.</td></tr>
    <tr><td><code>input_bytes</code></td><td>The size of the upload. <code>bytes</code> is the size without the metadata.</td></tr>
    <tr><td><code>removed</code></td><td>What was taken out, such as <code>EXIF</code>, <code>XMP</code> and <code>Comments</code>.</td></tr>
    <tr><td><code>kept</code></td><td><code>Colour profile</code> and <code>Orientation</code>, when the image had them.</td></tr>''') + '''
<p>The example at the top of the page comes from the same test photo as on the <a href="/free-image-metadata-viewer-api">metadata viewer</a>, with made-up EXIF data and a GPS position. What came back is the photo as it was before the EXIF data was added, %(bytes)s bytes. A GET on <code>storage_url</code> returns the image with its own image type.</p>
<p>Anyone with the link can open the image until it expires, so do not send pictures of people or anything confidential. Stored results count against the Storage budget of 80 MB per IP address per day.</p>

''' % {'bytes': '{:,}'.format(STRIP['bytes']).replace(',', ' ')} + LIMITS_READ % 'The result is at most 10 MB.' + '''

''' + ERRORS_READ,
    script_start(['jpeg', 'png', 'webp'], 'JPEG, PNG or WebP') + SCRIPT_CHOOSE + r'''

  // Comments becomes comments inside a sentence, while EXIF stays EXIF.
  function soft(item) {
    return /^[A-Z][a-z]/.test(item) ? item.charAt(0).toLowerCase() + item.slice(1) : item;
  }

  function list(items) {
    items = items.map(soft);
    return items.length < 2 ? items.join('') : items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1];
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, function () {});
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    T.busy(result, 'Removing...');
    submit.disabled = true;
    T.postFile('image_strip', file, {}).then(function (answer) {
      var line = answer.removed.length ? 'Removed ' + list(answer.removed) + '.' : 'There was nothing to remove.';
      if (answer.kept.length) { line += ' Kept ' + list(answer.kept) + '.'; }
      line += ' ' + T.bytes(answer.input_bytes) + ' became ' + T.bytes(answer.bytes) + '.';
      T.showStored(result, answer, { image: true, summary: line });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });
})();''',
    [
        ('Is the EXIF remover API free?', FAQ_FREE),
        ('Does removing the metadata lower the quality?', 'No. The image data is copied byte for byte, so the pixels are exactly the same as in the upload.'),
        ('Will the photo still show the right way up?', 'Yes. When the camera marked the photo as rotated, the orientation is written back on its own, and nothing else is.'),
        ('Can it remove metadata from HEIC?', 'No. It takes JPEG, PNG and WebP. The image converter reads HEIC and removes the metadata while it converts.')
    ],
    'Free EXIF remover API'
)

# -- The colour palette -----------------------------------------------------------

PALETTE = stored_json('image_colors')
PALETTE['placeholder'] = PALETTE['placeholder'][:48] + '...'
SWATCHES = '\n'.join('    <span class="tool-swatch-static" style="background:%s">%s, %s%%</span>' % (c['hex'], c['hex'], round(c['share'] * 100, 1)) for c in PALETTE['colors'])

page(
    'free-image-color-palette-api',
    'Free colour palette API: the dominant colours of an image | AI SENSE',
    'Get the dominant colours of a JPEG, PNG or WebP with the share each one covers, the average colour and a tiny placeholder image, in your browser or with one API call. No API key.',
    'Free colour palette from an image',
    'Drop an image and get its main colours as hex and RGB with the share of the picture each one covers, the average colour and a 16 pixel placeholder for lazy loading. The form calls the same free API your code can call: one POST, no API key and no account.',
    ['No API key', 'No account', '2 to 16 colours', 'Hex and RGB', 'Placeholder image'],
    'image_colors',
    '''  <form id="tool-form">
''' + DROP + '''
    <div class="tool-options">
      <div class="tool-field">
        <label for="tool-count">Colours: <output id="tool-count-value" for="tool-count">8</output></label>
        <input type="range" id="tool-count" min="2" max="16" step="1" value="8">
      </div>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Find the colours</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="how">How the colours are found</h2>
<ul>
  <li><strong>The image is made small first</strong>, at most 128 pixels on its longest side, so a large photo is as quick as a small one.</li>
  <li><strong>ImageMagick reduces it to the number of colours you ask for</strong>, 2 to 16 and 8 when you ask for none, without dithering, and counts the pixels of each. A colour's <code>share</code> is its part of the visible pixels. An image with fewer colours gives fewer.</li>
  <li><strong>Transparent pixels are left out</strong> and counted as <code>transparent_share</code>, so a logo on a transparent background gives the colours of the logo.</li>
  <li><strong>The average</strong> is the mean colour of the visible pixels of the reduced image.</li>
  <li><strong>The placeholder</strong> is the image at most 16 pixels on its longest side, as a PNG data URI, to show while the real image loads.</li>
  <li>The image is turned upright first, and a CMYK JPEG is converted to RGB.</li>
</ul>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_colors</code> with <code>multipart/form-data</code>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The image: JPEG, PNG or WebP.</td></tr>
    <tr><td><code>count</code></td><td>no</td><td>How many colours, 2 to 16. 8 when left out.</td></tr>
  </tbody>
</table>
<p>The palette is stored as <code>colors.json</code>, and the answer holds the Storage fields and the main points:</p>
''' + answer_table('''    <tr><td><code>content_type</code>, <code>filename</code></td><td><code>application/json</code> and <code>colors.json</code>.</td></tr>
    <tr><td><code>operation</code></td><td><code>image_colors</code>.</td></tr>
    <tr><td><code>average</code>, <code>dominant</code></td><td>The average colour and the colour with the largest share, as hex.</td></tr>
    <tr><td><code>count</code></td><td>How many colours the palette holds.</td></tr>''') + '''
<p>The example at the top of the page comes from a test run with a test image of 1600 x 1200 pixels and <code>count=6</code>. The stored palette, with the placeholder cut short here:</p>
<pre><code>''' + html.escape(json.dumps(PALETTE, indent=2, ensure_ascii=False), quote=False) + '''</code></pre>
<div class="tool-swatches-static" aria-label="The six colours of the example">
''' + SWATCHES + '''
</div>
<p>Anyone with the link can read the palette until it expires. Stored results count against the Storage budget of 80 MB per IP address per day.</p>

''' + LIMITS_DECODED + '''

''' + ERRORS_DECODED,
    script_start(['jpeg', 'png', 'webp'], 'JPEG, PNG or WebP', r'''  var count = document.getElementById('tool-count');
  var countValue = document.getElementById('tool-count-value');
''') + SCRIPT_CHOOSE + r'''

  function swatch(hex, label) {
    var box = T.make('div', 'tool-swatch');
    var colour = T.make('span');
    if (/^#[0-9A-F]{6}$/.test(hex)) { colour.style.background = hex; }
    box.appendChild(colour);
    box.appendChild(T.make('code', '', hex));
    box.appendChild(T.make('small', '', label));
    return box;
  }

  function palette(report) {
    var box = T.make('div', 'tool-palette');
    var grid = T.make('div', 'tool-swatches');
    (report.colors || []).forEach(function (colour) {
      grid.appendChild(swatch(colour.hex, (Math.round(colour.share * 1000) / 10) + '% of the picture'));
    });
    if (report.average) { grid.appendChild(swatch(report.average.hex, 'Average')); }
    box.appendChild(grid);
    if (report.transparent_share > 0) {
      box.appendChild(T.make('p', 'tool-meta', (Math.round(report.transparent_share * 1000) / 10) + '% of the image is transparent and is left out.'));
    }
    if (typeof report.placeholder === 'string' && report.placeholder.indexOf('data:image/png;base64,') === 0) {
      var figure = T.make('p', 'tool-meta', 'Placeholder, 16 pixels, shown large: ');
      var image = T.make('img', 'tool-placeholder');
      image.alt = 'The 16 pixel placeholder';
      image.src = report.placeholder;
      figure.appendChild(image);
      box.appendChild(figure);
    }
    return box;
  }

  function refresh() {
    countValue.textContent = count.value;
  }

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, refresh);
  });
  count.addEventListener('input', refresh);

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    T.busy(result, 'Finding the colours...');
    submit.disabled = true;
    T.postFile('image_colors', file, { count: count.value }).then(function (answer) {
      T.showStored(result, answer, { summary: answer.count + ' colours. The largest share is ' + answer.dominant + ', and the average is ' + answer.average + '.' });
      return T.stored(answer).then(function (blob) {
        return blob.text();
      }).then(function (text) {
        result.insertBefore(palette(JSON.parse(text)), result.children[1] || null);
      });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });

  refresh();
})();''',
    [
        ('Is the colour palette API free?', FAQ_FREE),
        ('How many colours can I get?', '2 to 16, and 8 when you do not say. An image with fewer colours gives fewer.'),
        ('What happens to transparent pixels?', 'They are left out of the palette and the average, and transparent_share says how much of the image they cover.'),
        ('Can I use the placeholder in an img tag?', 'Yes. It is a PNG data URI, so it works as the src of an img element or as a CSS background, with no extra request.')
    ],
    'Free colour palette API'
)

# -- The favicon generator ----------------------------------------------------------

HEAD_TAGS = '''<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">'''

page(
    'free-favicon-generator-api',
    'Free favicon generator API: favicon.ico, PNG icons and manifest | AI SENSE',
    'Turn a logo or a picture into favicon.ico, the PNG icons browsers, iPhones and Android use, a web app manifest and the HTML tags to paste, as one ZIP. In your browser or with one API call. No API key.',
    'Free favicon generator',
    'Drop a logo or a picture and get a ZIP with favicon.ico, the PNG icons for browsers, iPhone and Android, a web app manifest and the HTML to paste into your pages. The form calls the same free API your code can call: one POST, no API key and no account.',
    ['No API key', 'No account', 'favicon.ico and PNG', 'Web manifest', 'Fit, trim or center'],
    'image_favicon',
    '''  <form id="tool-form">
''' + DROP + '''
    <div class="tool-options">
      <div class="tool-field">
        <label for="tool-crop">Make it square by</label>
        <select id="tool-crop">
          <option value="fit" selected>Fit: all of it, on transparent</option>
          <option value="trim">Trim the border, then fit</option>
          <option value="center">Center: cut a square from the middle</option>
        </select>
      </div>
      <div class="tool-field">
        <label for="tool-name">Site name, for the manifest</label>
        <input type="text" id="tool-name" maxlength="60" placeholder="Optional">
      </div>
    </div>
    <div class="tool-actions">
      <button type="submit" class="button button-primary" id="tool-submit" disabled>Make the favicons</button>
    </div>
  </form>
  <div class="tool-result" id="tool-result" aria-live="polite"></div>''',
    '''<h2 id="files">What is in the ZIP</h2>
<table>
  <thead><tr><th>File</th><th>Size</th><th>For</th></tr></thead>
  <tbody>
    <tr><td><code>favicon.ico</code></td><td>16, 32 and 48 pixels</td><td>Every browser, and anything that asks for <code>/favicon.ico</code></td></tr>
    <tr><td><code>favicon-16x16.png</code>, <code>favicon-32x32.png</code></td><td>16 and 32 pixels</td><td>Browser tabs</td></tr>
    <tr><td><code>apple-touch-icon.png</code></td><td>180 pixels, on white</td><td>The home screen of an iPhone or iPad, which shows no transparency</td></tr>
    <tr><td><code>icon-192.png</code>, <code>icon-512.png</code></td><td>192 and 512 pixels</td><td>Android and installed web apps</td></tr>
    <tr><td><code>site.webmanifest</code></td><td></td><td>The web app manifest, with the name you give and the two large icons</td></tr>
    <tr><td><code>head.html</code></td><td></td><td>The tags to paste into the <code>&lt;head&gt;</code> of your pages</td></tr>
  </tbody>
</table>
<p>Put the files in the root of your site and paste the tags from <code>head.html</code>:</p>
<pre><code>''' + html.escape(HEAD_TAGS, quote=False) + '''</code></pre>
<p>Why each file is there, and the mistakes that leave an icon blurry or missing, is in <a href="/favicon-sizes-and-the-files-a-website-needs">the guide to favicon sizes</a>.</p>

<h2 id="crop">Fit, trim or center</h2>
<ul>
  <li><strong>fit</strong>, the default, shows all of the picture on a transparent square.</li>
  <li><strong>trim</strong> first cuts away a border of one colour, such as the white around a logo, and then fits what is left.</li>
  <li><strong>center</strong> cuts a square from the middle and fills the whole icon with it, which suits a photo.</li>
</ul>
<p>Icons look best from a square picture of at least 512 pixels. When the picture, or what is left after trimming, is smaller, the largest icons are enlarged and the answer says <code>upscaled: true</code>. The picture is turned upright first, and its metadata is not copied into the icons.</p>

<h2 id="api">The API</h2>
<p><code>POST https://aisenseapi.com/services/v1/image_favicon</code> with <code>multipart/form-data</code>.</p>
<table>
  <thead><tr><th>Field</th><th>Required</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>file</code></td><td>yes</td><td>The picture: JPEG, PNG or WebP.</td></tr>
    <tr><td><code>crop</code></td><td>no</td><td><code>fit</code>, <code>trim</code> or <code>center</code>. <code>fit</code> when left out.</td></tr>
    <tr><td><code>name</code></td><td>no</td><td>The site name for the manifest, at most 60 characters of plain text.</td></tr>
  </tbody>
</table>
<p>The icons are stored as <code>favicon.zip</code>, and the answer holds the Storage fields and what the ZIP holds:</p>
''' + answer_table('''    <tr><td><code>content_type</code>, <code>filename</code></td><td><code>application/zip</code> and <code>favicon.zip</code>.</td></tr>
    <tr><td><code>operation</code>, <code>crop</code></td><td><code>image_favicon</code>, and the crop that was used.</td></tr>
    <tr><td><code>files</code></td><td>The names of the files in the ZIP.</td></tr>
    <tr><td><code>upscaled</code></td><td><code>true</code> when the picture was smaller than 512 pixels, so the largest icons are enlarged.</td></tr>''') + '''
<p>The example at the top of the page comes from a test run with a logo of 600 x 200 pixels, <code>crop=trim</code> and <code>name=Example site</code>. What was left after trimming was 301 pixels wide, so the answer says it was enlarged.</p>
<p>Anyone with the link can download the ZIP until it expires. Stored results count against the Storage budget of 80 MB per IP address per day.</p>

''' + LIMITS_DECODED + '''

''' + ERRORS_DECODED,
    script_start(['jpeg', 'png', 'webp'], 'JPEG, PNG or WebP', r'''  var crop = document.getElementById('tool-crop');
  var name = document.getElementById('tool-name');
''') + SCRIPT_CHOOSE + r'''

  T.imageDrop(document.getElementById('tool-drop'), document.getElementById('tool-file'), function (picked) {
    choose(picked, function () {});
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!file) { return; }
    var fields = { crop: crop.value };
    if (name.value.trim()) { fields.name = name.value.trim(); }
    T.busy(result, 'Making the favicons...');
    submit.disabled = true;
    T.postFile('image_favicon', file, fields).then(function (answer) {
      var line = 'A ZIP with ' + answer.files.length + ' files: ' + answer.files.join(', ') + '.';
      if (answer.upscaled) { line += ' The picture was smaller than 512 pixels, so the largest icons are enlarged and may look soft.'; }
      T.showStored(result, answer, { summary: line });
    }).catch(function (error) {
      T.showError(result, error);
    }).then(function () {
      submit.disabled = false;
    });
  });
})();''',
    [
        ('Is the favicon generator API free?', FAQ_FREE),
        ('What size should my logo be?', 'Square and at least 512 pixels. A smaller one works, but the largest icons are then enlarged.'),
        ('Do I need to give a name?', 'No. Without one the manifest has an empty name, which you can fill in yourself.'),
        ('Does it make an SVG favicon?', 'No. The icons are PNG, and favicon.ico holds the three small sizes as PNG images.')
    ],
    'Free favicon generator API'
)
