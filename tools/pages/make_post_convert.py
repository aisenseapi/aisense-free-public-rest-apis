"""Write the guide to converting HEIC, WebP, PNG and JPG, and list it on the
posts page and in the sitemap. The numbers come from the recorded answers in
data/, so the guide says what the service measured.

Usage: python make_post_convert.py <web> <data dir>
"""
import html
import io
import json
import sys
from collections import OrderedDict

WEB = sys.argv[1]
DATA = sys.argv[2]
SLUG = 'convert-heic-webp-png-and-jpg-images'
URL = 'https://aisense.no/' + SLUG
DATE = '2026-09-30'
H1 = 'How to Convert HEIC, WebP, PNG and JPG Images for Free'
TITLE = 'Convert HEIC, WebP, PNG and JPG Images for Free - AI SENSE'
DESCRIPTION = ('HEIC to JPG, WebP to JPG, PNG to JPG, JPG to WebP, smaller files and new sizes: which free tool does '
               'each, and what each conversion keeps and loses.')
OG_DESCRIPTION = ('iPhone photos that will not open, WebP that will not upload, PNG that is too heavy: the free tool '
                  'for each, with measured sizes.')


def answer(file, key):
    run = json.load(io.open(DATA + '/' + file, encoding='utf-8'), object_pairs_hook=OrderedDict)[key]
    return json.loads(run['answer'])


def number(n):
    return '{:,}'.format(n).replace(',', ' ')


def smaller(before, after):
    return round((1 - after / before) * 100)


WEBP = answer('results-images.json', 'image_convert')
COMPRESS = answer('results-images.json', 'image_compress')
HEIC = answer('results-heic.json', 'heic_convert')
RESIZE = answer('results-resize.json', 'image_resize')
PHOTO = WEBP['input_bytes']

source = io.open(WEB + '/a-name-that-answers-for-24-hours.html', encoding='utf-8').read()
BODY_START = source[source.index('<body>'):source.index('<main id="main-content"')]
FOOTER = source[source.index('<footer class="site-footer">'):]
CSS = source.split('<link rel="stylesheet" href="', 1)[1].split('"', 1)[0]

FAQ = [
    ('How do I convert HEIC to JPG on Windows?',
     'Drop the photo on the free HEIC to JPG converter in any browser. Nothing has to be installed, and the JPG keeps '
     'its colours, comes out the right way up and leaves the GPS position behind.'),
    ('How do I convert WebP to JPG?',
     'Choose JPG on the free image converter and drop the WebP on it. For a picture with transparent parts choose PNG '
     'instead, since JPG turns transparency white.'),
    ('Does converting an image lose quality?',
     'Saving as JPG or lossy WebP compresses the picture again and removes a little detail, which at the default '
     'quality of 82 is hard to see on a screen. PNG and lossless WebP keep every pixel. Converting a JPG to PNG cannot '
     'bring back detail the JPG already lost.'),
    ('Is PNG or JPG better?',
     'JPG for photos, which it stores far smaller. PNG for screenshots, text, logos and anything with transparency, '
     'which JPG blurs or cannot hold.'),
    ('How do I make an image file smaller?',
     'Resize it to the size it is shown at, then compress it. Our 1600 x 1200 test photo went from %s to %s bytes '
     'at half the width.' % (number(PHOTO), number(RESIZE['bytes']))),
    ('Are these converters free?',
     'Yes. No account and no API key. The limit is 5000 requests per IP address per 24 hours, and 80 MB of stored '
     'results per IP address per day.')
]

LD = OrderedDict([
    ('@context', 'https://schema.org'),
    ('@graph', [
        OrderedDict([
            ('@type', 'TechArticle'),
            ('headline', H1),
            ('description', DESCRIPTION),
            ('url', URL),
            ('datePublished', DATE),
            ('inLanguage', 'en'),
            ('author', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS')])),
            ('publisher', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS'), ('url', 'https://aisense.no/')])),
            ('about', OrderedDict([
                ('@type', 'WebAPI'),
                ('name', 'Image converter, compression and resizer'),
                ('documentation', 'https://aisense.no/free-public-apis#images'),
                ('provider', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS')]))
            ]))
        ]),
        OrderedDict([
            ('@type', 'FAQPage'),
            ('mainEntity', [OrderedDict([('@type', 'Question'), ('name', q),
                                         ('acceptedAnswer', OrderedDict([('@type', 'Answer'), ('text', a)]))]) for q, a in FAQ])
        ]),
        OrderedDict([
            ('@type', 'BreadcrumbList'),
            ('itemListElement', [
                OrderedDict([('@type', 'ListItem'), ('position', 1), ('name', 'Home'), ('item', 'https://aisense.no/')]),
                OrderedDict([('@type', 'ListItem'), ('position', 2), ('name', 'Posts'), ('item', 'https://aisense.no/ai-sense-posts')]),
                OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', 'Convert images'), ('item', URL)])
            ])
        ])
    ])
])

B = chr(92)
CURLS = (' ' + B + '\n  ').join(['curl -s -X POST https://aisenseapi.com/services/v1/image_convert', '-F "file=@photo.webp"', '-F "format=jpeg"']) + '\n\n' \
    + (' ' + B + '\n  ').join(['curl -s -X POST https://aisenseapi.com/services/v1/image_resize', '-F "file=@photo.jpg"', '-F "width=800"']) + '\n\n' \
    + (' ' + B + '\n  ').join(['curl -s -X POST https://aisenseapi.com/services/v1/image_compress', '-F "file=@photo.jpg"', '-F "quality=70"'])

ARTICLE = '''<main id="main-content" class="article-main">
<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/ai-sense-posts">Posts</a></li><li aria-current="page">Convert images</li></ol></nav>

<div class="article-shell">
<header class="article-header">
  <p class="eyebrow">Guide - 30 September 2026</p>
  <h1>%(h1)s</h1>
  <p class="article-deck">Five image problems come up again and again: an iPhone photo in HEIC that will not open, a WebP a form will not take, a PNG too heavy to send, a JPG that has to be a PNG, and a picture that is simply too big. Each has a free tool here, and each conversion keeps some things and loses others.</p>
</header>

<div class="article-body">
<p class="article-lead">Pick the row that matches what you have and what you need. Every tool works in the browser without an account, and every one is also a single API call for code and agents.</p>

<div class="table-wrap"><table>
<thead><tr><th>You have</th><th>You need</th><th>Use</th></tr></thead>
<tbody>
<tr><td>An iPhone photo in HEIC</td><td>A JPG that opens everywhere</td><td><a href="/free-heic-to-jpg-converter">HEIC to JPG converter</a></td></tr>
<tr><td>A WebP</td><td>A JPG or a PNG</td><td><a href="/free-image-converter-api">Image converter</a></td></tr>
<tr><td>A PNG photo</td><td>A smaller JPG</td><td><a href="/free-image-converter-api">Image converter</a></td></tr>
<tr><td>A JPG</td><td>A PNG or a WebP</td><td><a href="/free-image-converter-api">Image converter</a></td></tr>
<tr><td>Any photo</td><td>A smaller file, same format</td><td><a href="/free-image-compression-api">Image compression</a></td></tr>
<tr><td>Any photo</td><td>A new size or a square thumbnail</td><td><a href="/free-image-resizer-api">Image resizer</a></td></tr>
<tr><td>Any photo</td><td>No GPS position or camera data</td><td><a href="/free-exif-remover-api">EXIF remover</a></td></tr>
<tr><td>A logo</td><td>Favicons for a website</td><td><a href="/free-favicon-generator-api">Favicon generator</a></td></tr>
</tbody>
</table></div>

<h2>HEIC to JPG: iPhone photos that open everywhere</h2>

<p>An iPhone has saved photos as HEIC since iOS 11, unless the camera is set to Most Compatible. HEIC is small, but many upload forms and programs cannot open it, and Windows needs extra extensions from the Microsoft Store to show it. A JPG opens everywhere.</p>

<p>The <a href="/free-heic-to-jpg-converter">HEIC to JPG converter</a> turns the photo the right way up once, although an iPhone records the turn twice, keeps the Display P3 colour profile so the colours stay the same, and removes the GPS position. The JPG is usually a little larger than the HEIC: in our test, %(heic_in)s bytes of HEIC became %(heic_out)s bytes of JPG at quality 82. That is the price of a format everything can read.</p>

<h2>WebP to JPG or PNG</h2>

<p>Many websites serve their pictures as WebP, so a saved image often ends up as a .webp file that an older program or an upload form will not take. The <a href="/free-image-converter-api">image converter</a> turns it into a JPG for a photo, or a PNG when the picture has transparent parts or sharp text.</p>

<h2>PNG to JPG, and JPG to PNG</h2>

<p><strong>PNG to JPG</strong> makes a photo far smaller, because JPG is built for photos and PNG is not. Two things change: transparent parts become white, since JPG has no transparency, and sharp edges in text and screenshots can blur a little. Keep PNG for screenshots, text and logos.</p>

<p><strong>JPG to PNG</strong> does not improve a picture. The detail JPG compression removed stays gone, and the file gets larger: a big photo as PNG can pass the 8 MB limit for a result. Convert only when a program insists on PNG, or before editing a picture many times over.</p>

<h2>JPG or PNG to WebP, for web pages</h2>

<p>WebP makes pages load faster. Our 1600 x 1200 test photo went from %(photo)s bytes as JPG to %(webp)s bytes as WebP at quality 82, about %(webp_pct)s percent smaller at the same size. For logos and screenshots, lossless WebP keeps every pixel and is usually smaller than the same picture as PNG.</p>

<div class="article-cta">
  <p class="eyebrow">Try it</p>
  <h2>Drop an image, pick the format.</h2>
  <p>JPEG, PNG, WebP or HEIC in, JPEG, PNG or WebP out. Free, no account.</p>
  <div class="button-row"><a href="/free-image-converter-api">Image converter</a> <a href="/free-heic-to-jpg-converter">HEIC to JPG</a></div>
</div>

<h2>Make an image smaller: resize or compress</h2>

<p>There are two ways, and they add up:</p>

<ul>
  <li><strong>Resize</strong> it to the size it is shown at. A photo shown 800 pixels wide does not need 1600. The <a href="/free-image-resizer-api">image resizer</a> made our test photo %(resize_w)s x %(resize_h)s, and %(photo)s bytes became %(resize)s, about %(resize_pct)s percent smaller.</li>
  <li><strong>Compress</strong> it at a lower quality, in the same format. The <a href="/free-image-compression-api">image compression</a> tool saved the same photo at quality 70 as %(compress)s bytes, about %(compress_pct)s percent smaller, at full size.</li>
</ul>

<p>For a photo on a web page or in an email, resizing usually saves the most. A square thumbnail is a resize with <code>fit=cover</code>, which fills the square and cuts the rest from the centre.</p>

<h2>What every conversion here does</h2>

<ul>
  <li><strong>Turns the picture upright</strong> from the orientation a phone writes in the EXIF data.</li>
  <li><strong>Removes EXIF, XMP, IPTC and comments</strong>, so the GPS position, the camera and the date do not follow the picture. The <a href="/remove-gps-location-and-exif-data-from-photos">guide to the location in photos</a> explains what that data can tell.</li>
  <li><strong>Keeps the colour profile</strong>, so the colours stay the same. A CMYK JPEG becomes RGB.</li>
  <li><strong>Takes the first frame</strong> of an animated image.</li>
  <li><strong>Never enlarges</strong> a picture on a resize unless you ask for it.</li>
</ul>

<p>The tools take JPEG, PNG and WebP up to 10 MB and 25 megapixels, and HEIC on the converter and the resizer. GIF, AVIF, SVG, TIFF, camera RAW and PDF are refused, and HEIC can be read but not written.</p>

<h2>Where your picture goes</h2>

<p>The picture is sent to aisenseapi.com and converted in a sandbox without network access, and the upload is deleted when the job ends. The result is kept for 24 hours at a link that anyone with the link can open, so do not send pictures of people or anything confidential.</p>

<h2>For developers</h2>

<p>Each tool is one POST with the picture in a field named <code>file</code>, no key and no account, and the answer is JSON with a link to the result:</p>

<pre><code>%(curls)s</code></pre>

<p>The fields, limits and answers are in the <a href="/free-public-apis#images">image section of the API reference</a>.</p>

<h2>Questions</h2>

%(faq)s

<div class="article-cta">
  <p class="eyebrow">The tools</p>
  <h2>Convert, resize or compress, free.</h2>
  <p>No account and no API key. The result waits for 24 hours.</p>
  <div class="button-row"><a href="/free-image-converter-api">Image converter</a> <a href="/free-heic-to-jpg-converter">HEIC to JPG</a> <a href="/free-image-resizer-api">Image resizer</a> <a href="/free-image-compression-api">Compression</a> <a href="/ai-sense-posts">More posts</a></div>
</div>
</div>
</div>
</main>

''' % {
    'h1': H1,
    'heic_in': number(HEIC['input_bytes']), 'heic_out': number(HEIC['bytes']),
    'photo': number(PHOTO), 'webp': number(WEBP['bytes']), 'webp_pct': smaller(PHOTO, WEBP['bytes']),
    'resize_w': RESIZE['width'], 'resize_h': RESIZE['height'], 'resize': number(RESIZE['bytes']), 'resize_pct': smaller(PHOTO, RESIZE['bytes']),
    'compress': number(COMPRESS['bytes']), 'compress_pct': smaller(PHOTO, COMPRESS['bytes']),
    'curls': html.escape(CURLS, quote=False),
    'faq': '\n\n'.join('<h3>%s</h3>\n<p>%s</p>' % (html.escape(q, quote=False), html.escape(a, quote=False)) for q, a in FAQ)
}

PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="canonical" href="%(url)s">

<meta property="og:type" content="article">
<meta property="og:site_name" content="AI SENSE">
<meta property="og:title" content="%(h1)s">
<meta property="og:description" content="%(og)s">
<meta property="og:url" content="%(url)s">
<meta property="article:published_time" content="%(date)s">
<meta name="twitter:card" content="summary">

<link rel="stylesheet" href="%(css)s">

<script type="application/ld+json">
%(ld)s
</script>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
</head>
%(body)s%(article)s%(footer)s''' % {
    'title': TITLE, 'description': html.escape(DESCRIPTION), 'url': URL, 'h1': html.escape(H1), 'og': html.escape(OG_DESCRIPTION),
    'date': DATE, 'css': CSS, 'ld': json.dumps(LD, indent=2, ensure_ascii=False), 'body': BODY_START, 'article': ARTICLE, 'footer': FOOTER
}

io.open(WEB + '/' + SLUG + '.html', 'w', encoding='utf-8', newline='\n').write(PAGE)
print('wrote', SLUG + '.html', len(PAGE.encode('utf-8')), 'bytes')


def patch(path, old, new):
    """Put new in front of the first old, once."""
    text = io.open(path, encoding='utf-8', newline='').read()
    if SLUG in text:
        print('already in', path.split('/')[-1])
        return
    if old not in text:
        raise SystemExit('%s: no match for %r' % (path, old[:60]))
    io.open(path, 'w', encoding='utf-8', newline='').write(text.replace(old, new + old, 1))
    print('updated', path.split('/')[-1])


CARD = '''  <article class="post-card">
    <div class="post-card-body">
      <p class="post-meta"><span>Guide</span><time datetime="%s">30 September 2026</time></p>
      <h2><a href="/%s">%s</a></h2>
      <p>HEIC to JPG, WebP to JPG, PNG to JPG, JPG to WebP, smaller files and new sizes. Which free tool fixes which image problem, what each conversion keeps and loses, and the sizes we measured.</p>
      <a class="card-link" href="/%s">Read the guide</a>
    </div>
  </article>

''' % (DATE, SLUG, html.escape(H1), SLUG)

patch(WEB + '/ai-sense-posts.html', '  <article class="post-card">\n', CARD)
patch(WEB + '/sitemap.xml', '  <url><loc>https://aisense.no/favicon-sizes-and-the-files-a-website-needs</loc>',
      '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' % (URL, DATE))
