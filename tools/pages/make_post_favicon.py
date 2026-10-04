"""Write the guide to favicon sizes, and list it on the posts page and in the
sitemap. The example answer comes from results-more.json.

Usage: python make_post_favicon.py <web> <results-more.json>
"""
import html
import io
import json
import sys
from collections import OrderedDict

WEB = sys.argv[1]
RESULTS = json.load(io.open(sys.argv[2], encoding='utf-8'), object_pairs_hook=OrderedDict)
B = chr(92)
SLUG = 'favicon-sizes-and-the-files-a-website-needs'
URL = 'https://aisense.no/' + SLUG
DATE = '2026-09-29'
H1 = 'Favicon Sizes: The Files a Website Needs, and How to Make Them'
TITLE = 'Favicon Sizes: The Files Every Website Needs - AI SENSE'
DESCRIPTION = ('Which favicon sizes a site needs: favicon.ico, 32 px PNG, the 180 px Apple touch icon, 192 and 512 px for '
               'Android. Make them all free from one image.')
OG_DESCRIPTION = ('favicon.ico, the PNG sizes, the Apple touch icon, the web manifest and the HTML to paste, explained, '
                  'and made from one logo in a single free call.')

source = io.open(WEB + '/a-name-that-answers-for-24-hours.html', encoding='utf-8').read()
BODY_START = source[source.index('<body>'):source.index('<main id="main-content"')]
FOOTER = source[source.index('<footer class="site-footer">'):]
CSS = source.split('<link rel="stylesheet" href="', 1)[1].split('"', 1)[0]

RUN = RESULTS['image_favicon']
ANSWER = json.loads(RUN['answer'], object_pairs_hook=OrderedDict)
REQUEST = (' ' + B + '\n  ').join(['curl -s -X POST https://aisenseapi.com/services/v1/image_favicon', '-F "file=@logo.png"']
                                   + ['-F "%s=%s"' % item for item in RUN['fields'].items()])
EXAMPLE = html.escape(REQUEST + '\n\n' + json.dumps(ANSWER, indent=2, ensure_ascii=False), quote=False)

HEAD_TAGS = '''<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">'''

MANIFEST = '''{
  "name": "Example site",
  "short_name": "Example site",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "display": "standalone"
}'''

FAQ = [
    ('What size should a favicon be?',
     'There is no single size. Browser tabs use 16 and 32 pixels, favicon.ico holds 16, 32 and 48, an iPhone home screen uses 180, '
     'and Android and installed web apps use 192 and 512. Start from a square image of at least 512 pixels and make the rest from it.'),
    ('Do I still need favicon.ico?',
     'Yes. Browsers ask for /favicon.ico when a page names no icon, and many other programs ask for it directly. It costs one file.'),
    ('What size is the Apple touch icon?',
     '180 by 180 pixels, on a solid background, since an iPhone shows no transparency on the home screen.'),
    ('Can a favicon be an SVG?',
     'Most browsers read an SVG favicon, and it stays sharp at any size. Not every browser and tool does, so keep the PNG and ICO files beside it.'),
    ('Is the favicon generator free?',
     'Yes. No account and no API key. It makes all the files from one image and gives them back as a ZIP.')
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
                ('name', 'Favicon generator'),
                ('documentation', 'https://aisense.no/free-favicon-generator-api'),
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
                OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', 'Favicon sizes'), ('item', URL)])
            ])
        ])
    ])
])

ARTICLE = '''<main id="main-content" class="article-main">
<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/ai-sense-posts">Posts</a></li><li aria-current="page">Favicon sizes</li></ol></nav>

<div class="article-shell">
<header class="article-header">
  <p class="eyebrow">Guide - 29 September 2026</p>
  <h1>%(h1)s</h1>
  <p class="article-deck">A favicon is no longer one file. Browser tabs, iPhones, Android phones and installed web apps each look for their own size. The set that covers them all is small: six images, a manifest and five lines of HTML, all made from one picture.</p>
</header>

<div class="article-body">
<p class="article-lead">The little icon in a browser tab is the most repeated piece of branding a website has. It sits in every tab, every bookmark and every history list, beside the site in search results, and on the home screen of every phone that saved a shortcut. Each of those places asks for a different file, and a site that only has one gets a blurry or missing icon in the others.</p>

<h2>The sizes, and who asks for each</h2>

<div class="table-wrap"><table>
<thead><tr><th>File</th><th>Size</th><th>Who asks for it</th></tr></thead>
<tbody>
<tr><td><code>favicon.ico</code></td><td>16, 32 and 48 px in one file</td><td>Every browser when a page names no icon, and many other programs directly at <code>/favicon.ico</code></td></tr>
<tr><td><code>favicon-32x32.png</code></td><td>32 x 32</td><td>Browser tabs and bookmarks on sharp screens</td></tr>
<tr><td><code>favicon-16x16.png</code></td><td>16 x 16</td><td>Browser tabs on ordinary screens</td></tr>
<tr><td><code>apple-touch-icon.png</code></td><td>180 x 180, solid background</td><td>An iPhone or iPad that saves the site to the home screen</td></tr>
<tr><td><code>icon-192.png</code></td><td>192 x 192</td><td>Android home screens, through the web manifest</td></tr>
<tr><td><code>icon-512.png</code></td><td>512 x 512</td><td>Installed web apps and their splash screens, through the web manifest</td></tr>
<tr><td><code>site.webmanifest</code></td><td>text</td><td>Android and installed web apps: the name, the icons and the colors</td></tr>
</tbody>
</table></div>

<p>That is the whole list for most sites. Old guides list twenty sizes or more, for tiles on Windows 8, old Android versions and every iPad generation. Current systems scale from the files above.</p>

<h2>The HTML to put in the head</h2>

<p>Put the files in the root of the site and these five lines in the <code>&lt;head&gt;</code> of every page:</p>

<pre><code>%(head)s</code></pre>

<p>The paths start with a slash on purpose. A relative path such as <code>favicon.ico</code> works on the front page and breaks on every page one folder down.</p>

<p>The manifest is a small JSON file beside them, with the name of the site, the two large icons and two colors:</p>

<pre><code>%(manifest)s</code></pre>

<p><code>theme_color</code> colors the title bar when the site is installed as an app. The generator writes white for both colors. To match the logo, put its main color in <code>theme_color</code>; the <a href="/free-image-color-palette-api">color palette tool</a> reads it from the image.</p>

<h2>Start from the right picture</h2>

<ul>
  <li><strong>Square, and at least 512 pixels.</strong> Every size is made from the largest. A smaller picture has to be enlarged, and the large icons look soft.</li>
  <li><strong>Simple enough for 16 pixels.</strong> A full logo with a name in small letters turns into a smudge in a tab. The symbol alone, or the first letter, usually reads better.</li>
  <li><strong>No empty border.</strong> White space around a logo makes the icon look small next to other tabs. Cut it away first, or let the generator trim it.</li>
  <li><strong>Transparent for browsers, solid for the iPhone.</strong> A tab looks best with a transparent background. The home screen of an iPhone shows no transparency, so its icon needs a background of its own.</li>
</ul>

<div class="article-cta">
  <p class="eyebrow">Try it</p>
  <h2>One logo in, every favicon out.</h2>
  <p>The favicon generator makes all seven files and head.html from one picture, and gives them back as a ZIP.</p>
  <div class="button-row"><a href="/free-favicon-generator-api">Favicon generator</a></div>
</div>

<h2>Make them all from one image</h2>

<p>The <a href="/free-favicon-generator-api">free favicon generator</a> takes a JPEG, PNG or WebP and makes the whole set: favicon.ico with 16, 32 and 48 pixels inside, the two PNGs for tabs, the 180 pixel iPhone icon on white, the 192 and 512 pixel icons, the manifest, and <code>head.html</code> with the five lines above. It gives them back as one ZIP.</p>

<p>It has three ways to make a picture square:</p>

<ul>
  <li><strong>fit</strong> shows all of the picture on a transparent square. Right for a logo that is already square, or nearly.</li>
  <li><strong>trim</strong> first cuts away a border of one color, such as the white around a logo, and then fits what is left.</li>
  <li><strong>center</strong> cuts a square from the middle and fills the whole icon with it. Right for a photo.</li>
</ul>

<p>We gave it a logo of 600 x 200 pixels with white around it, trimmed. The ZIP came back at %(zip)s bytes with all eight files. The answer also said <code>upscaled: true</code>: what was left after trimming was 301 pixels wide, less than 512, so the largest icons were enlarged. That is the sign to start from a bigger picture.</p>

<pre><code>%(example)s</code></pre>

<h2>Common mistakes</h2>

<ul>
  <li><strong>Only a 16 pixel favicon.ico.</strong> It looks blurry on every sharp screen, which is most of them.</li>
  <li><strong>A transparent iPhone icon.</strong> The transparent parts do not stay transparent on the home screen.</li>
  <li><strong>No manifest, or no 192 and 512 pixel icons in it.</strong> Android may then put a small, blurry icon or just the first letter of the site on the home screen instead of the logo.</li>
  <li><strong>Relative paths.</strong> The icon shows on the front page and disappears one folder down.</li>
  <li><strong>Waiting for the old icon to go away.</strong> Browsers keep favicons for a long time. After a change, give the files a new name or add <code>?v=2</code> to the links, and browsers fetch the new icon on the next visit.</li>
</ul>

<h2>Search results</h2>

<p>Google Search shows a site's favicon beside its results. It reads the icon links on the home page, the Apple touch icon among them, and asks for a square icon, preferably larger than 48 pixels. The set above has one of 180. After a change it can take days or weeks before the new icon shows there, and Google does not promise to show one at all.</p>

<h2>For developers</h2>

<p>The generator is a free REST endpoint with no key and no account: <code>POST https://aisenseapi.com/services/v1/image_favicon</code> with the picture in a field named <code>file</code>, and optionally <code>crop</code> and <code>name</code> for the manifest. The ZIP is stored for 24 hours at a link in the answer. The details are on the <a href="/free-favicon-generator-api">favicon generator page</a> and in the <a href="/free-public-apis#images">image section of the API reference</a>.</p>

<h2>Questions</h2>

%(faq)s

<div class="article-cta">
  <p class="eyebrow">Make yours</p>
  <h2>Every favicon a website needs, from one picture.</h2>
  <p>Free, no account and no API key. Drop a logo, choose how to make it square, and download the ZIP.</p>
  <div class="button-row"><a href="/free-favicon-generator-api">Favicon generator</a> <a href="/free-image-color-palette-api">Color palette</a> <a href="/ai-sense-posts">More posts</a></div>
</div>
</div>
</div>
</main>

''' % {
    'h1': H1,
    'head': html.escape(HEAD_TAGS, quote=False),
    'manifest': html.escape(MANIFEST, quote=False),
    'zip': '{:,}'.format(ANSWER['bytes']).replace(',', ' '),
    'example': EXAMPLE,
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
      <p class="post-meta"><span>Guide</span><time datetime="%s">29 September 2026</time></p>
      <h2><a href="/%s">%s</a></h2>
      <p>Browser tabs, iPhones, Android phones and installed web apps each ask for their own favicon. The whole set is six images, a manifest and five lines of HTML, all made from one picture with a free generator.</p>
      <a class="card-link" href="/%s">Read the guide</a>
    </div>
  </article>

''' % (DATE, SLUG, html.escape(H1), SLUG)

patch(WEB + '/ai-sense-posts.html', '  <article class="post-card">\n', CARD)
patch(WEB + '/sitemap.xml', '  <url><loc>https://aisense.no/remove-gps-location-and-exif-data-from-photos</loc>',
      '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' % (URL, DATE))
