"""Write the post on photo location and EXIF, and list it on the posts page
and in the sitemap. The example answers come from results-more.json.

Usage: python make_post_photo_location.py <web> <results-more.json>
"""
import html
import io
import json
import sys
from collections import OrderedDict

WEB = sys.argv[1]
RESULTS = json.load(io.open(sys.argv[2], encoding='utf-8'), object_pairs_hook=OrderedDict)
B = chr(92)
SLUG = 'remove-gps-location-and-exif-data-from-photos'
URL = 'https://aisense.no/' + SLUG
DATE = '2026-09-29'
H1 = 'How to See and Remove the Location Hidden in Your Photos'
TITLE = 'Remove GPS and EXIF Data From Photos for Free - AI SENSE'
DESCRIPTION = ('Phone photos can carry your GPS position, camera serial number and an uncropped thumbnail. '
               'Check any photo for free and remove it without losing quality.')
OG_DESCRIPTION = ('See what a JPEG, PNG or WebP gives away, remove EXIF and GPS without saving the picture again, '
                  'and turn iPhone HEIC into JPEG with the location removed. Free, no account.')

source = io.open(WEB + '/a-name-that-answers-for-24-hours.html', encoding='utf-8').read()
BODY_START = source[source.index('<body>'):source.index('<main id="main-content"')]
FOOTER = source[source.index('<footer class="site-footer">'):]
CSS = source.split('<link rel="stylesheet" href="', 1)[1].split('"', 1)[0]


def example(operation):
    run = RESULTS[operation]
    request = (' ' + B + '\n  ').join(['curl -s -X POST https://aisenseapi.com/services/v1/' + operation, '-F "file=@photo.jpg"'])
    answer = json.dumps(json.loads(run['answer'], object_pairs_hook=OrderedDict), indent=2, ensure_ascii=False)
    return html.escape(request + '\n\n' + answer, quote=False)


STRIP = json.loads(RESULTS['image_strip']['answer'])
SAVED = STRIP['input_bytes'] - STRIP['bytes']


def number(n):
    return '{:,}'.format(n).replace(',', ' ')


FAQ = [
    ('Can someone see where a photo was taken?',
     'If the file carries a GPS position, yes. Any metadata viewer shows it, often to within a few metres, together with the time. '
     'The free image metadata viewer shows whether a photo has one.'),
    ('Does removing EXIF data lower the quality of a photo?',
     'Not with the free EXIF remover, which copies the compressed image data byte for byte. Saving the photo again in an editor '
     'compresses a JPEG again, and some detail is lost each time.'),
    ('Will the photo still be the right way up?',
     'Yes. When the camera marked the photo as turned, the EXIF remover writes the orientation back on its own, and nothing else.'),
    ('How do I remove the location from an iPhone photo?',
     'Turn Location off under Options in the share sheet when you share from Photos, or convert the HEIC file to JPEG with the free '
     'HEIC to JPG converter, which removes EXIF and GPS on the way.'),
    ('Is it free?',
     'Yes. No account and no API key. The limit is 5000 requests per IP address per 24 hours.')
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
                ('name', 'Image metadata viewer and EXIF remover'),
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
                OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', 'Remove the location from photos'), ('item', URL)])
            ])
        ])
    ])
])

ARTICLE = '''<main id="main-content" class="article-main">
<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/ai-sense-posts">Posts</a></li><li aria-current="page">Remove the location from photos</li></ol></nav>

<div class="article-shell">
<header class="article-header">
  <p class="eyebrow">Guide - 29 September 2026</p>
  <h1>%(h1)s</h1>
  <p class="article-deck">A photo from a phone can carry the place it was taken to within a few metres, the time, the camera's serial number and a small copy of the uncropped original. Here is how to see what yours holds, and how to take it out without losing a single pixel.</p>
</header>

<div class="article-body">
<p class="article-lead">Most people who share a photo think they are sharing a picture. The file holds more. When a phone takes a picture it writes a block of data next to the pixels, called EXIF, and with location turned on for the camera that block includes the latitude and longitude of where you stood. Anyone who gets the file itself can read it in seconds, with free tools, ours included.</p>

<h2>What a photo can carry</h2>

<p>We built a <a href="/free-image-metadata-viewer-api">free image metadata viewer</a> that reads every block a JPEG, PNG or WebP holds and sorts what it finds by how much it gives away. These are the items it looks for, most sensitive first:</p>

<div class="table-wrap"><table>
<thead><tr><th>Item</th><th>Level</th><th>What it tells</th></tr></thead>
<tbody>
<tr><td>GPS position</td><td>High</td><td>Where the picture was taken, often to within a few metres, with the altitude and the time in UTC</td></tr>
<tr><td>Location in XMP</td><td>High</td><td>A place an editing program recorded</td></tr>
<tr><td>Serial number or unique ID</td><td>High</td><td>Links the picture to every other picture from the same camera or lens</td></tr>
<tr><td>Names</td><td>Medium</td><td>An author, owner or copyright holder written into the file</td></tr>
<tr><td>Place names in IPTC</td><td>Medium</td><td>A city, region or country written by photo software</td></tr>
<tr><td>Camera or phone</td><td>Medium</td><td>Make and model of the device</td></tr>
<tr><td>Date and time</td><td>Medium</td><td>When the picture was taken or last changed</td></tr>
<tr><td>Thumbnails and extra images</td><td>Medium</td><td>A small copy made before any crop, or further images stored after the main one, such as depth maps and HDR gain maps</td></tr>
<tr><td>Descriptions and comments</td><td>Low</td><td>Free text written into the file</td></tr>
<tr><td>Software</td><td>Low</td><td>The program that made or edited the file</td></tr>
</tbody>
</table></div>

<p>Not every photo has all of it. A picture straight from a phone camera usually has the camera, the time and, if location was on, the position. A picture that has been through an editing program often picks up XMP and a software tag. The ones that hurt are the ones nobody knew were there: a position on a photo of a front door, or a thumbnail that still shows what was cropped away.</p>

<h2>When the data travels with the photo</h2>

<p>Many large social networks remove this data when a photo is uploaded. That is their choice, not something the file does. A photo usually keeps all of it when it is:</p>

<ul>
  <li>sent as a file or a document in a messaging app,</li>
  <li>attached to an email,</li>
  <li>shared through a cloud storage link,</li>
  <li>uploaded to a marketplace, a forum or your own website,</li>
  <li>handed to an API or a script that stores what it receives.</li>
</ul>

<p>If you do not know which of these a photo will go through, check it, and remove what it should not carry.</p>

<h2>Check a photo in a few seconds</h2>

<p>The <a href="/free-image-metadata-viewer-api">image metadata viewer</a> reads the file without decoding the picture, so it works on large photos and never changes them. Drop a JPEG, PNG or WebP on the page and it lists what it found, with the GPS position in plain decimal degrees if there is one.</p>

<p>Behind the page is one API call. This is what it answered for a test photo we gave made-up EXIF data, with a position at the Oslo Opera House:</p>

<pre><code>%(metadata)s</code></pre>

<p>The full report is stored as JSON for 24 hours. It has every EXIF tag by name, the XMP and IPTC fields, the colour profile, and the privacy list with a reason for each item.</p>

<div class="article-cta">
  <p class="eyebrow">Try it</p>
  <h2>Drop a photo and see what it says.</h2>
  <p>The metadata viewer is free, needs no account, and shows the GPS position if the file has one.</p>
  <div class="button-row"><a href="/free-image-metadata-viewer-api">Image metadata viewer</a></div>
</div>

<h2>Remove it without losing quality</h2>

<p>Most ways of removing metadata save the picture again. That works, but a JPEG saved again is compressed again, and some detail is lost each time.</p>

<p>The <a href="/free-exif-remover-api">free EXIF remover</a> does it differently. It walks the blocks of the file, leaves out EXIF, GPS, XMP, IPTC, comments, thumbnails and anything after the end of the image, and copies the compressed image data byte for byte. The pixels are exactly the ones you sent. We checked that by decoding a progressive JPEG before and after: not one pixel differed.</p>

<p>Two things are kept on purpose. The colour profile stays, so the colours look the same. And if the camera marked the photo as turned, a new EXIF block with the orientation alone is written back, so it still shows the right way up.</p>

<p>For the test photo above, the file went from %(before)s to %(after)s bytes. The %(saved)s bytes of EXIF were all that went, because that was all we had put in. A photo from a phone also carries a maker note and a thumbnail, so more goes.</p>

<pre><code>%(strip)s</code></pre>

<h2>iPhone photos and HEIC</h2>

<p>An iPhone saves photos as HEIC unless the setting is changed. HEIC carries the same EXIF, GPS included, and many websites and programs cannot open it at all.</p>

<p>The <a href="/free-heic-to-jpg-converter">free HEIC to JPG converter</a> takes HEIC and gives back a JPEG, PNG or WebP. On the way it removes EXIF, XMP and comments, keeps the colour profile, which on a recent iPhone is Display P3, and turns the picture the way the phone stored it. That last part is easy to get wrong. An iPhone records the turn twice, once for HEIC readers and once in EXIF, and a converter that applies both turns a portrait sideways. We test ours with a file built the way an iPhone builds one.</p>

<p>On the iPhone itself, two settings are worth knowing:</p>

<ul>
  <li>When you share from Photos, tap Options at the top of the share sheet and turn Location off. The copy you send leaves without the position.</li>
  <li>Settings, Privacy &amp; Security, Location Services, Camera, Never stops the position from being recorded at all.</li>
</ul>

<p>On Android the camera app has its own setting, usually called Location tags or Save location.</p>

<h2>For developers</h2>

<p>All three are free REST endpoints with no key and no account, limited to 5000 requests per IP address a day. They take the image as <code>multipart/form-data</code> in a field named <code>file</code> and answer with a link to the result in Storage, where it stays for 24 hours.</p>

<div class="table-wrap"><table>
<thead><tr><th>Endpoint</th><th>What it does</th></tr></thead>
<tbody>
<tr><td><code>POST /services/v1/image_metadata</code></td><td>The report: EXIF, GPS, XMP, IPTC, colour profile and the privacy list</td></tr>
<tr><td><code>POST /services/v1/image_strip</code></td><td>The same file without its metadata, pixels untouched</td></tr>
<tr><td><code>POST /services/v1/image_convert</code></td><td>HEIC, JPEG, PNG or WebP to JPEG, PNG or WebP, with the metadata removed</td></tr>
</tbody>
</table></div>

<p>The whole set, with limits and error codes, is in the <a href="/free-public-apis#images">image section of the API reference</a>.</p>

<h2>What happens to your photo</h2>

<p>The metadata viewer reads the photo and drops it; only the report is kept. The EXIF remover and the converter keep their result at a link that anyone with the link can open, so keep the link to yourself. Everything is deleted after 24 hours.</p>

<h2>Questions</h2>

%(faq)s

<div class="article-cta">
  <p class="eyebrow">Before you share</p>
  <h2>Check the photo, then send the clean copy.</h2>
  <p>Three free tools, no account and no API key: see what a photo holds, remove it without losing quality, or turn an iPhone HEIC into a JPEG with the location gone.</p>
  <div class="button-row"><a href="/free-image-metadata-viewer-api">Metadata viewer</a> <a href="/free-exif-remover-api">EXIF remover</a> <a href="/free-heic-to-jpg-converter">HEIC to JPG</a> <a href="/ai-sense-posts">More posts</a></div>
</div>
</div>
</div>
</main>

''' % {
    'h1': H1,
    'metadata': example('image_metadata'),
    'strip': example('image_strip'),
    'before': number(STRIP['input_bytes']),
    'after': number(STRIP['bytes']),
    'saved': number(SAVED),
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
    'title': TITLE, 'description': html.escape(DESCRIPTION), 'url': URL, 'h1': H1, 'og': html.escape(OG_DESCRIPTION),
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
      <p class="post-meta"><span>Guide</span><time datetime="%s">29 September 2026</time></p>
      <h2><a href="/%s">%s</a></h2>
      <p>A phone photo can carry the place it was taken, the camera's serial number and a small copy of the uncropped original. Check any photo for free and remove the metadata without losing a pixel, iPhone HEIC included.</p>
      <a class="card-link" href="/%s">Read the guide</a>
    </div>
  </article>

''' % (DATE, SLUG, H1, SLUG)

patch(WEB + '/ai-sense-posts.html', '  <article class="post-card">\n', CARD)
patch(WEB + '/sitemap.xml', '  <url><loc>https://aisense.no/a-name-that-answers-for-24-hours</loc>',
      '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' % (URL, DATE))
