"""Write the endpoint pages for HTML to Markdown and Markdown to HTML into
web/, the two added on 3 October 2026.

The page around the content, from the head to the footer, is taken from
web/free-public-api-dns-name-api-endpoint.html, as make_codec_pages.py does.
Every example answer was worked out with the service's own functions
(libs/func_markdown.php in the service repository), so the pages show what the
service answers.

Usage: python make_markdown_pages.py <web>
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


def curl(path, data):
    # Quoted for the shell, so any example can be copied and run as it is.
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
    return table(['Status', 'error', 'When'], rows) + '<p>Each refusal also carries <code>fix</code>, a sentence saying what to send instead.</p>'


def privacy(name, limits):
    return ('<section id="privacy"><h2>Privacy and limits</h2><div class="api-note warning-note"><p>Nothing is stored. The '
            + name + ' answer is worked out while the request is open and the data is gone with it. The access log records '
            'the path and the status, not the body.</p></div><p>The base URL is <code>https://aisenseapi.com/services/v1</code>. '
            'There is no key, no account and no sign-up step. ' + limits + ' The service-wide limit is 5000 requests per IP '
            'address per day. Every endpoint in the collection is listed on the '
            '<a href="/free-public-apis">Free public REST APIs</a> reference.</p></section>')


INPUT = ('<p>Send the text as <code>{"data": "..."}</code> with <code>Content-Type: application/json</code>, or as the raw '
         'request body with any other content type, such as <code>%s</code>. It has to be UTF-8.</p>')

HTML_ANSWER = {'markdown': '# Version 2\n\nNow with **tables** and [links](https://aisense.no).', 'title': 'Release notes'}

REPORT = '# Report\n\n- **3** jobs done\n- [ ] one left\n\n| Job | Time |\n|---|--:|\n| sync | 2.1 s |'
REPORT_HTML = ('<h1>Report</h1>\n<ul>\n<li><strong>3</strong> jobs done</li>\n<li><input type="checkbox" disabled="" /> one left</li>\n'
               '</ul>\n<table>\n<thead>\n<tr>\n<th>Job</th>\n<th style="text-align: right">Time</th>\n</tr>\n</thead>\n<tbody>\n'
               '<tr>\n<td>sync</td>\n<td style="text-align: right">2.1 s</td>\n</tr>\n</tbody>\n</table>')


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
                     ('url', 'https://aisense.no/' + slug), ('documentation', 'https://aisense.no/free-public-apis#transform'),
                     ('provider', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS'), ('url', 'https://aisense.no/')]))]),
        OrderedDict([('@type', 'BreadcrumbList'), ('itemListElement', [
            OrderedDict([('@type', 'ListItem'), ('position', 1), ('name', 'Home'), ('item', 'https://aisense.no/')]),
            OrderedDict([('@type', 'ListItem'), ('position', 2), ('name', 'Free public REST APIs'), ('item', 'https://aisense.no/free-public-apis')]),
            OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', spec['crumb']), ('item', 'https://aisense.no/' + slug)])])])])])
    top = swap(top, '<script type="application/ld+json">\n', '\n</script>', json.dumps(ld, indent=2, ensure_ascii=False))

    sections = spec['sections'] + [privacy(spec['short'], spec['limits']), '<section id="related"><h2>Related APIs</h2>' + related(spec['related']) + '</section>']
    toc = spec['toc'] + [('privacy', 'Privacy'), ('related', 'Related')]
    main = ('<main id="main-content" class="api-detail-main">\n'
            '<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/free-public-apis">'
            'Free public REST APIs</a></li><li aria-current="page">' + spec['crumb'] + '</li></ol></nav>\n'
            '<section class="api-detail-hero" aria-labelledby="page-title"><div><p class="eyebrow">Transform - Text</p>'
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
        'slug': 'html-to-markdown', 'path': 'html_to_markdown', 'crumb': 'HTML to Markdown API Endpoint', 'short': 'HTML to Markdown',
        'title': 'Free HTML to Markdown API Endpoint - Read Web Pages as Markdown | AI SENSE',
        'h1': 'Free HTML to Markdown API Endpoint',
        'description': 'The free HTML to Markdown API endpoint turns a web page or any HTML into CommonMark, without scripts, styles or forms, and gives the page title. No API key.',
        'lede': 'The free HTML to Markdown API endpoint turns a web page or any HTML into CommonMark with GitHub tables. Scripts, styles, '
                'forms and media are left out, so an agent reads the text, the links and the structure without the markup around them.',
        'badges': ['No API key', 'CommonMark', 'Page title', 'One POST request'],
        'label': 'Convert HTML to Markdown',
        'limits': 'One request carries at most 1 MiB of HTML and 40000 start and end tags. Scripts and styles are skipped whole, and tags inside them do not count.',
        'toc': [('quick-start', 'Quick start'), ('what', 'What becomes what'), ('input', 'Input'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free HTML to Markdown API endpoint</h2><p>Post the HTML under a <code>data</code> key:</p>'
            + curl('html_to_markdown', '<title>Release notes</title><h1>Version 2</h1><p>Now with <b>tables</b> and '
                                       '<a href="https://aisense.no">links</a>.</p><script>track()</script>')
            + answer(HTML_ANSWER)
            + '<p><code>title</code> is the page title, or <code>null</code> when the HTML has none. The script is gone, and so would '
              'a style sheet, a form or an embedded video be. To go the other way, use the '
              '<a href="/free-public-api-markdown-to-html-api-endpoint">Markdown to HTML API endpoint</a>.</p>'
              '<p>A page fetched with curl can go straight in as the body:</p>'
            + pre('curl -s https://aisense.no/free-public-apis | curl -X POST ' + API + '/html_to_markdown ' + B
                  + '\n  -H "Content-Type: text/html" --data-binary @-') + '</section>',
            '<section id="what"><h2>What becomes what</h2>' + table(['HTML', 'Markdown'], [
                ['<code>&lt;h1&gt;</code> to <code>&lt;h6&gt;</code>', '<code>#</code> to <code>######</code>'],
                ['<code>&lt;b&gt;</code>, <code>&lt;strong&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;em&gt;</code>, <code>&lt;s&gt;</code>',
                 '<code>**bold**</code>, <code>*italic*</code>, <code>~~struck~~</code>'],
                ['<code>&lt;a href&gt;</code>, <code>&lt;img&gt;</code>', '<code>[text](url)</code> and <code>![alt](src)</code>, title kept'],
                ['<code>&lt;ul&gt;</code>, <code>&lt;ol start&gt;</code>, a checkbox first in an item', '<code>-</code>, <code>3.</code> and <code>- [x]</code>, nested by indentation'],
                ['<code>&lt;table&gt;</code>', 'a GitHub table, or plain text when the table only lays out a page'],
                ['<code>&lt;pre&gt;</code>, <code>&lt;code&gt;</code>', 'a fenced code block with the language from a <code>language-</code> class, inline code in backticks'],
                ['<code>&lt;blockquote&gt;</code>, <code>&lt;br&gt;</code>, <code>&lt;hr&gt;</code>', '<code>&gt;</code>, a line break, <code>---</code>'],
                ['<code>&lt;script&gt;</code>, <code>&lt;style&gt;</code>, the head, forms, <code>&lt;svg&gt;</code>, video, audio, comments', 'left out'],
            ]) + '<p>Text that would read as Markdown is escaped, so it reads back as the same text: <code>2 * 3</code> becomes '
            '<code>2 ' + B + '* 3</code>, and <code>[a link]</code> that is not one becomes <code>' + B + '[a link' + B + ']</code>. '
            'Links keep their URLs as written, relative ones included, and links with a <code>javascript:</code> or other '
            'unlisted scheme become their text. Images given as data URLs are left out, since their bytes are no use as text.</p></section>',
            '<section id="input"><h2>Sending the input</h2>' + (INPUT % 'text/html')
            + '<p>The HTML is read the way a browser forgives it: a <code>&lt;p&gt;</code> or <code>&lt;li&gt;</code> left open closes '
              'itself, a stray end tag is ignored, and nesting deeper than a hundred levels is flattened.</p></section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No HTML to convert.', 'No <code>data</code> string and no body'],
                ['400', 'The HTML is not UTF-8 text.', 'A page in another encoding, sent as it is'],
                ['413', 'Data over 1 MiB.', 'More than 1 MiB in one request'],
                ['413', 'Too many HTML tags.', 'More than 40000 start and end tags outside scripts and styles']]) + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Agents reading pages', 'Fetch a page and hand an agent Markdown instead of HTML: the same text and links, without class names and scripts.'),
                ('Context for a model', 'Headings, lists and tables survive as Markdown, which helps a language model find its way through a long page.'),
                ('Archive and compare', 'Keep pages as Markdown and compare two versions as text, without the markup changing underneath.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-markdown-to-html-api-endpoint', 'Markdown to HTML API Endpoint', 'The other way, safe to show'),
            ('/free-public-api-html-decode-api-endpoint', 'HTML Decode API Endpoint', 'Entities back to characters'),
            ('/free-public-api-html-to-pdf-api-endpoint', 'HTML to PDF API Endpoint', 'Render a page to a PDF'),
            ('/free-public-apis', 'Free public REST APIs', 'Every endpoint in one place'),
        ],
    },
    {
        'slug': 'markdown-to-html', 'path': 'markdown_to_html', 'crumb': 'Markdown to HTML API Endpoint', 'short': 'Markdown to HTML',
        'title': 'Free Markdown to HTML API Endpoint - Safe CommonMark Rendering | AI SENSE',
        'h1': 'Free Markdown to HTML API Endpoint',
        'description': 'The free Markdown to HTML API endpoint renders CommonMark with GitHub tables, task lists and strikethrough into HTML that is safe to put in a page. No API key.',
        'lede': 'The free Markdown to HTML API endpoint renders CommonMark, with the GitHub tables, strikethrough, task lists and bare '
                'links agents write, into an HTML fragment. Raw HTML in the Markdown is shown as text and an unsafe link as its text, '
                'so the answer can go into a page as it is.',
        'badges': ['No API key', 'CommonMark and GitHub', 'Safe by design', 'One POST request'],
        'label': 'Render Markdown',
        'limits': 'One request carries at most 256 KiB of Markdown and 20000 lines.',
        'toc': [('quick-start', 'Quick start'), ('safe', 'Safe to show'), ('supported', 'What it reads'), ('pdf', 'Markdown to PDF'),
                ('input', 'Input'), ('errors', 'Errors'), ('use-cases', 'Use cases')],
        'sections': [
            '<section id="quick-start"><h2>Call the free Markdown to HTML API endpoint</h2><p>Post the Markdown under a <code>data</code> key:</p>'
            + curl('markdown_to_html', REPORT) + answer({'html': REPORT_HTML})
            + '<p>The <code>html</code> value is a fragment, with no <code>&lt;html&gt;</code> or <code>&lt;body&gt;</code> around it:</p>'
            + pre(REPORT_HTML)
            + '<p>To go the other way, use the <a href="/free-public-api-html-to-markdown-api-endpoint">HTML to Markdown API endpoint</a>.</p></section>',
            '<section id="safe"><h2>Safe to show</h2><p>The HTML can go into a page as it is, even when the Markdown came from someone '
            'else. Raw HTML in the Markdown is shown as text, never passed through, and a link or image whose scheme is not on a short '
            'list is shown as its text:</p>'
            + curl('markdown_to_html', '<script>alert(1)</script> and [click](javascript:alert(1))')
            + answer({'html': '<p>&lt;script&gt;alert(1)&lt;/script&gt; and click</p>'})
            + table(['Allowed', 'Where'], [
                ['<code>http:</code>, <code>https:</code> and relative URLs', 'links and images'],
                ['<code>mailto:</code>, <code>tel:</code>, <code>ftp:</code>', 'links'],
                ['PNG, GIF, JPEG and WebP data URLs', 'images'],
            ]) + '<p>Anything else, <code>javascript:</code>, <code>vbscript:</code>, <code>data:text/html</code> and SVG data '
            'included, however it is spelled or escaped, becomes text. Attribute values are escaped, so a title or URL cannot add '
            'an attribute of its own.</p></section>',
            '<section id="supported"><h2>What it reads</h2>' + table(['Markdown', 'HTML'], [
                ['<code>#</code> to <code>######</code>, or a line underlined with <code>===</code> or <code>---</code>', '<code>&lt;h1&gt;</code> to <code>&lt;h6&gt;</code>'],
                ['<code>*em*</code>, <code>**strong**</code>, <code>~~struck~~</code>, <code>`code`</code>', '<code>&lt;em&gt;</code>, <code>&lt;strong&gt;</code>, <code>&lt;del&gt;</code>, <code>&lt;code&gt;</code>, by the CommonMark rules'],
                ['<code>[text](url "title")</code>, <code>[text][ref]</code>, <code>&lt;https://...&gt;</code>, a bare <code>www.</code> or <code>https://</code> link', '<code>&lt;a href&gt;</code>'],
                ['<code>![alt](src)</code>', '<code>&lt;img&gt;</code> with its alt text'],
                ['<code>-</code>, <code>*</code>, <code>+</code>, <code>1.</code>, <code>1)</code>, <code>- [ ]</code> and <code>- [x]</code>', 'lists, tight or loose, with start numbers and checkboxes'],
                ['<code>| a | b |</code> over <code>|:--|--:|</code>', 'a table with its column alignment'],
                ['fenced code with a language, indented code', '<code>&lt;pre&gt;&lt;code class="language-..."&gt;</code>'],
                ['<code>&gt;</code>, <code>---</code>, two spaces or a backslash at a line end', '<code>&lt;blockquote&gt;</code>, <code>&lt;hr /&gt;</code>, <code>&lt;br /&gt;</code>'],
            ]) + '</section>',
            '<section id="pdf"><h2>Markdown to PDF in one pipe</h2><p>The <a href="/free-public-api-html-to-pdf-api-endpoint">HTML to PDF '
            'API endpoint</a> takes the html as its data and stores the PDF for 24 hours:</p>'
            + pre('curl -s -X POST ' + API + '/markdown_to_html ' + B + '\n  -H "Content-Type: text/markdown" --data-binary @report.md ' + B
                  + "\n  | jq '{data: .html}' " + B + '\n  | curl -s -X POST ' + API + '/html2pdf ' + B
                  + '\n      -H "Content-Type: application/json" --data-binary @-')
            + '<p>The answer carries the <code>storage_url</code> of the PDF.</p></section>',
            '<section id="input"><h2>Sending the input</h2>' + (INPUT % 'text/markdown')
            + '<p>Windows and old Mac line ends are read as line ends.</p></section>',
            '<section id="errors"><h2>Errors</h2>' + errors([
                ['400', 'No Markdown to convert.', 'No <code>data</code> string and no body'],
                ['400', 'The Markdown is not UTF-8 text.', 'Text in another encoding, sent as it is'],
                ['413', 'Data over 256 KiB.', 'More than 256 KiB in one request'],
                ['413', 'Too many Markdown lines.', 'More than 20000 lines in one request']]) + '</section>',
            '<section id="use-cases"><h2>Common uses</h2>' + cards([
                ('Reports from agents', 'An agent writes Markdown, people read HTML: put its report in a page or an email as it comes back.'),
                ('Text people wrote', 'Show comments and notes with their formatting, and without any HTML or script they slipped in.'),
                ('Documents to PDF', 'Render a Markdown file here and hand the HTML to the HTML to PDF endpoint for a printable copy.'),
            ]) + '</section>',
        ],
        'related': [
            ('/free-public-api-html-to-markdown-api-endpoint', 'HTML to Markdown API Endpoint', 'The other way, for reading pages'),
            ('/free-public-api-html-to-pdf-api-endpoint', 'HTML to PDF API Endpoint', 'Render the HTML to a PDF'),
            ('/free-public-api-html-encode-api-endpoint', 'HTML Encode API Endpoint', 'Escape one value for a page'),
            ('/free-public-apis', 'Free public REST APIs', 'Every endpoint in one place'),
        ],
    },
]

for spec in PAGES:
    page(spec)
