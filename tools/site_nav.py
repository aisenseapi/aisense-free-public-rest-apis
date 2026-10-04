"""Write the site header, with its menus, into every page in web/.

The header is inline in each page, so a menu change touches every page. This
script is the one place the menu is defined: run it after adding an endpoint
page or a post, and it rewrites the header of every page that has one.

    python tools/site_nav.py           rewrite the headers that differ
    python tools/site_nav.py --check   change nothing, exit 1 if any differ

Desktop shows four menus on hover and keyboard focus: the endpoints by
category, the MCP pages, the latest posts, and the company with every service
it offers. Phones and touch tablets get the
same links in the menu panel, one level at a time. Both are CSS only, styled in
web/assets/aisense.css under "Primary navigation".

The latest posts are read from the blogPost list in web/ai-sense-posts.html,
newest first, so adding a post there and running this updates every menu.
It also sets the version on each page's link to assets/aisense.css, see
CSS_VERSION. Each page keeps the top-level item it marks as current, and the home page its
current wordmark; a page that marks none stays that way. Every link must point at a page in web/, or the script stops.

Python 3, standard library only. Run from anywhere.
"""
import html
import json
import os
import re
import sys

from agent_optimal import decorate as decorate_agent_optimal

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), 'web')

LATEST_POSTS = 5

# The version on every page's link to assets/aisense.css. The CSS is served with
# no Cache-Control, so a browser may keep an old copy for hours; a new header
# with the old CSS would show every menu open. Change this whenever the CSS
# changes in a way the pages depend on, and run the script.
CSS_VERSION = '20261004a'

# The endpoint menu, one block per category: the category heading links to its
# guide or its section of the catalog, the items to the endpoint pages.
API_GROUPS = [
    ('agents', 'Agents and webhooks', '/free-public-apis#web', [
        ('/free-public-api-agent-wake-api-endpoint', 'Agent Wake'),
        ('/free-public-api-agent-queue-api-endpoint', 'Agent Queue'),
        ('/free-public-api-agent-inbox-api-endpoint', 'Agent Inbox'),
        ('/free-public-api-heartbeat-api-endpoint', 'Heartbeat'),
        ('/free-public-api-lease-api-endpoint', 'Lease'),
        ('/free-public-api-webhook-capture-api-endpoint', 'Webhook capture'),
        ('/free-public-api-webhook-action-api-endpoint', 'Webhook action'),
        ('/free-public-api-webhook-schedule-api-endpoint', 'Webhook schedule'),
        ('/free-public-api-dns-name-api-endpoint', 'Temporary DNS names'),
        ('/free-public-api-decide-api-endpoint', 'Decide'),
        ('/free-public-api-chaos-api-endpoint', 'Chaos'),
    ]),
    ('time', 'Time', '/time-apis', [
        ('/free-public-api-datetime-api-endpoint', 'Datetime'),
        ('/free-public-api-ip-datetime-api-endpoint', 'IP datetime'),
        ('/free-public-api-timestamp-api-endpoint', 'Timestamp'),
        ('/free-public-api-microtimestamp-api-endpoint', 'Microtimestamp'),
        ('/free-public-api-timezones-api-endpoint', 'Timezones'),
        ('/free-public-api-timestamp-convert-api-endpoint', 'Timestamp convert'),
        ('/free-public-api-swatchinternettime-api-endpoint', 'Swatch Internet Time'),
    ]),
    ('hashing', 'Hashing', '/hashing-apis', [
        ('/free-public-api-sha256-hash-api-endpoint', 'SHA256'),
        ('/free-public-api-sha512-hash-api-endpoint', 'SHA512'),
        ('/free-public-api-sha3-256-hash-api-endpoint', 'SHA3-256'),
        ('/free-public-api-sha3-512-hash-api-endpoint', 'SHA3-512'),
        ('/free-public-api-blake2b-hash-api-endpoint', 'BLAKE2b'),
        ('/free-public-api-blake3-hash-api-endpoint', 'BLAKE3'),
        ('/free-public-api-md5-hash-api-endpoint', 'MD5'),
        ('/free-public-api-sha1-hash-api-endpoint', 'SHA1'),
        ('/free-public-api-whirlpool-hash-api-endpoint', 'Whirlpool'),
        ('/free-public-api-crc32-checksum-api-endpoint', 'CRC32'),
        ('/free-public-api-argon2id-hash-api-endpoint', 'Argon2id'),
        ('/free-public-api-bcrypt-hash-api-endpoint', 'bcrypt'),
        ('/free-public-api-scrypt-hash-api-endpoint', 'scrypt'),
        ('/free-public-api-hash-verify-api-endpoint', 'Hash verify'),
    ]),
    ('encoding', 'Encoding', '/encoding-apis', [
        ('/free-public-api-base64-encode-api-endpoint', 'Base64 encode'),
        ('/free-public-api-base64-decode-api-endpoint', 'Base64 decode'),
        ('/free-public-api-base58-encode-api-endpoint', 'Base58 encode'),
        ('/free-public-api-base58-decode-api-endpoint', 'Base58 decode'),
        ('/free-public-api-base32-encode-api-endpoint', 'Base32 encode'),
        ('/free-public-api-base32-decode-api-endpoint', 'Base32 decode'),
        ('/free-public-api-base64url-encode-api-endpoint', 'base64url encode'),
        ('/free-public-api-base64url-decode-api-endpoint', 'base64url decode'),
        ('/free-public-api-hex-encode-api-endpoint', 'Hex encode'),
        ('/free-public-api-hex-decode-api-endpoint', 'Hex decode'),
        ('/free-public-api-url-encode-api-endpoint', 'URL encode'),
        ('/free-public-api-url-decode-api-endpoint', 'URL decode'),
        ('/free-public-api-html-encode-api-endpoint', 'HTML encode'),
        ('/free-public-api-html-decode-api-endpoint', 'HTML decode'),
    ]),
    ('text', 'Text and tokens', '/free-public-apis#transform', [
        ('/free-public-api-slugify-api-endpoint', 'Slugify'),
        ('/free-public-api-html-to-markdown-api-endpoint', 'HTML to Markdown'),
        ('/free-public-api-markdown-to-html-api-endpoint', 'Markdown to HTML'),
        ('/free-public-api-jwt-encode-api-endpoint', 'JWT encode'),
        ('/free-public-api-jwt-decode-api-endpoint', 'JWT decode'),
        ('/free-public-api-qr-code-encode-api-endpoint', 'QR code encode'),
        ('/free-public-api-qr-code-decode-api-endpoint', 'QR code decode'),
    ]),
    ('data', 'JSON and tables', '/free-public-apis#convert', [
        ('/free-json-to-csv-api', 'JSON to CSV'),
        ('/free-csv-to-json-api', 'CSV to JSON'),
        ('/free-json-formatter-api', 'JSON formatter'),
        ('/free-json-validator-api', 'JSON validator'),
        ('/free-table-matching-api', 'Table matching'),
    ]),
    ('images', 'Images', '/free-public-apis#images', [
        ('/free-image-converter-api', 'Image converter'),
        ('/free-heic-to-jpg-converter', 'HEIC to JPG'),
        ('/free-image-resizer-api', 'Image resizer'),
        ('/free-image-compression-api', 'Image compression'),
        ('/free-image-metadata-viewer-api', 'Image metadata'),
        ('/free-exif-remover-api', 'EXIF remover'),
        ('/free-image-color-palette-api', 'Colour palette'),
        ('/free-favicon-generator-api', 'Favicon generator'),
    ]),
    ('web', 'Web and network', '/free-public-apis#web', [
        ('/free-public-api-ping-api-endpoint', 'Ping'),
        ('/free-public-api-health-api-endpoint', 'Health'),
        ('/free-public-api-client-ip-api-endpoint', 'Client IP'),
        ('/free-public-api-user-agent-api-endpoint', 'User agent'),
        ('/free-public-api-ip-reverse-lookup-api-endpoint', 'IP reverse lookup'),
        ('/free-public-api-domain-ip-lookup-api-endpoint', 'Domain IP lookup'),
        ('/free-public-api-email-validate-api-endpoint', 'Email validation'),
        ('/free-public-api-validate-api-endpoint', 'Check digit validation'),
        ('/free-public-api-url-shortener-api-endpoint', 'URL shortener'),
        ('/free-public-api-html-to-pdf-api-endpoint', 'HTML to PDF'),
        ('/free-public-api-storage-api-endpoint', 'Storage'),
    ]),
    ('random', 'Random', '/random-generator-apis', [
        ('/free-public-api-uuid-api-endpoint', 'UUID'),
        ('/free-public-api-guid-api-endpoint', 'GUID'),
        ('/free-public-api-password-api-endpoint', 'Password'),
        ('/free-public-api-passphrase-api-endpoint', 'Passphrase'),
        ('/free-public-api-random-number-api-endpoint', 'Random number'),
        ('/free-public-api-random-color-api-endpoint', 'Random colour'),
    ]),
    ('crypto', 'Crypto', '/free-public-apis#crypto', [
        ('/free-public-api-bitcoin-balance-api-endpoint', 'Bitcoin balance'),
        ('/free-public-api-bitcoin-generate-new-wallet-api-endpoint', 'Bitcoin wallet'),
        ('/free-public-api-ethereum-balance-api-endpoint', 'Ethereum balance'),
        ('/free-public-api-ethereum-generate-new-wallet-api-endpoint', 'Ethereum wallet'),
        ('/free-public-api-solana-balance-api-endpoint', 'Solana balance'),
        ('/free-public-api-solana-generate-new-wallet-api-endpoint', 'Solana wallet'),
    ]),
]

# The About menu: the company, then every service it offers, in the order the
# home page presents them, each with a line taken from its own page.
SERVICE_LINKS = [
    ('/free-public-apis', 'Free public REST APIs', 'Utility endpoints with no account or key'),
    ('/free-public-mcp-server', 'Free MCP server', 'Every endpoint as a tool for an AI agent'),
    ('/custom-apis', 'Custom APIs', 'APIs and integrations built to order'),
    ('/make-your-data-available-for-ai', 'AI data feed', 'Your text and documents in feeds AI can read'),
    ('/aamio', 'aamio', 'Where agents that have never met exchange messages'),
    ('/verifyum', 'Verifyum', 'Private file proofs on Solana Mainnet'),
]

MCP_LINKS = [
    ('/free-public-mcp-server', 'MCP server'),
    ('/free-public-a2a-agent-endpoint', 'Agent2Agent (A2A)'),
]

# Pages whose current top-level item is set here rather than kept from the page.
CURRENT_OVERRIDES = {
    'free-public-a2a-agent-endpoint.html': '/free-public-mcp-server',
}

HEADER_RE = re.compile(r'<header class="site-header">.*?</header>', re.S)
CSS_RE = re.compile(r'<link rel="stylesheet" href="/assets/aisense\.css(?:\?v=[^"]*)?">')
CSS_LINK = '<link rel="stylesheet" href="/assets/aisense.css?v=%s">' % CSS_VERSION


def esc(text):
    return html.escape(text, quote=True)


def find_key(data, key):
    """The first value stored under key anywhere in parsed JSON-LD, @graph included."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        data = list(data.values())
    if isinstance(data, list):
        for value in data:
            found = find_key(value, key)
            if found is not None:
                return found
    return None


def latest_posts():
    source = open(os.path.join(WEB, 'ai-sense-posts.html'), encoding='utf-8').read()
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', source, re.S):
        posts = find_key(json.loads(block), 'blogPost')
        if posts:
            return [(post['url'].replace('https://aisense.no', ''), post['headline']) for post in posts[:LATEST_POSTS]]
    sys.exit('site_nav: no blogPost list found in ai-sense-posts.html')


def toggle(key, label):
    """A checkbox and its label: the open/close control on phones and touch tablets."""
    return ('<input class="nav-sub-toggle" type="checkbox" id="nav-sub-%s">'
            '<label class="nav-sub-button" for="nav-sub-%s"><span class="visually-hidden">%s</span></label>') % (key, key, esc(label))


def link_list(links):
    return '<ul class="nav-list">' + ''.join('<li><a href="%s">%s</a></li>' % (esc(href), esc(text)) for href, text in links) + '</ul>'


def described_list(links):
    return '<ul class="nav-list">' + ''.join(
        '<li><a href="%s">%s<span class="nav-desc">%s</span></a></li>' % (esc(href), esc(text), esc(desc))
        for href, text, desc in links) + '</ul>'


def item(href, label, current, panel=None):
    attrs = ' aria-current="page"' if href == current else ''
    top = '<a class="nav-top" href="%s"%s>%s</a>' % (esc(href), attrs, esc(label))
    if panel is None:
        return '<div class="nav-item">' + top + '</div>'
    key, toggle_label, body, place = panel
    classes = 'nav-item nav-has-panel' + {'wide': ' nav-item-wide', 'end': ' nav-item-end'}.get(place, '')
    return '<div class="%s">%s%s<div class="nav-panel">%s</div></div>' % (classes, top, toggle(key, toggle_label), body)


def render(current, home=False):
    groups = ''.join(
        '<div class="nav-group"><a class="nav-group-title" href="%s">%s</a>%s%s</div>' % (
            esc(href), esc(title), toggle(key, 'Show the %s endpoints' % title.lower()), link_list(links))
        for key, title, href, links in API_GROUPS)
    api_body = ('<div class="nav-groups">' + groups + '</div><p class="nav-panel-foot">'
                '<a href="/free-public-apis">Every endpoint in one list</a>'
                '<a href="/free-public-mcp-server">The same endpoints as MCP tools</a></p>')
    posts = latest_posts()
    posts_body = link_list(posts) + '<p class="nav-panel-foot"><a href="/ai-sense-posts">All posts</a></p>'
    about_body = (described_list([('/about', 'About AI SENSE AS', 'The company in Oslo behind the services')])
                  + '<p class="nav-panel-label">Services</p>' + described_list(SERVICE_LINKS))

    items = [
        item('/free-public-apis', 'Free public REST APIs', current, ('apis', 'Show the API categories', api_body, 'wide')),
        item('/free-public-mcp-server', 'Free MCP server', current, ('mcp', 'Show the agent protocol pages', link_list(MCP_LINKS), 'start')),
        item('/custom-apis', 'Custom APIs', current),
        item('/make-your-data-available-for-ai', 'AI data feed', current),
        item('/ai-sense-posts', 'Posts', current, ('posts', 'Show the latest posts', posts_body, 'end')),
        item('/contact-us', 'Contact us', current),
        item('/about', 'About', current, ('about', 'Show the company and its services', about_body, 'end')),
    ]
    wordmark = '<a class="wordmark" href="/"%s>AISENSE</a>' % (' aria-current="page"' if home else '')
    return ('<header class="site-header"><div class="inner">' + wordmark +
            '<nav class="site-nav" aria-label="Primary"><input class="site-menu-toggle" type="checkbox" id="site-menu-toggle">'
            '<label class="site-menu-button" for="site-menu-toggle"><span class="site-menu-bars"></span>Menu</label>'
            '<div class="site-menu-links">' + ''.join(items) + '</div></nav></div></header>')


def check_links(header):
    missing = []
    for href in re.findall(r'href="([^"]+)"', header):
        path = href.split('#', 1)[0].strip('/')
        if path and not os.path.isfile(os.path.join(WEB, path + '.html')):
            missing.append(href)
    if missing:
        sys.exit('site_nav: these menu links have no page in web/: ' + ', '.join(sorted(set(missing))))


def main():
    check = '--check' in sys.argv[1:]
    check_links(render(None))
    differ = []
    for name in sorted(os.listdir(WEB)):
        if not name.endswith('.html'):
            continue
        path = os.path.join(WEB, name)
        source = open(path, encoding='utf-8', newline='').read()
        found = HEADER_RE.search(source)
        if not found:
            continue
        marked = re.findall(r'<a (?:class="nav-top" )?href="([^"]+)" aria-current="page">', found.group(0))
        current = CURRENT_OVERRIDES.get(name, marked[0] if marked else None)
        home = 'class="wordmark" href="/" aria-current="page"' in found.group(0)
        updated = source[:found.start()] + render(current, home) + source[found.end():]
        updated = CSS_RE.sub(CSS_LINK, updated)
        updated = decorate_agent_optimal(updated, name)
        if updated == source:
            continue
        differ.append(name)
        if not check:
            with open(path, 'w', encoding='utf-8', newline='') as out:
                out.write(updated)
    if check:
        if differ:
            print('site_nav: %d page(s) carry an old header: %s' % (len(differ), ', '.join(differ)))
            sys.exit(1)
        print('site_nav: every header is current')
    else:
        print('site_nav: %d page(s) rewritten' % len(differ))


if __name__ == '__main__':
    main()
