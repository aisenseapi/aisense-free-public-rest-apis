# aisense.no - static pages

Developer documentation. It is deliberately NOT part of the published
`website` branch: served from the live domain it would sit one guessable
URL away from `/terms` and `/privacy` while openly discussing their
weaknesses, which reads very differently on the company's own domain than
it does in a repository. Keep it out of the deployed tree.

Plain HTML. No build step, no framework, no third-party requests. Open any file
in a browser and it renders.

71 pages. The 49 endpoint pages share one naming pattern and are collapsed
into a single row here; each one is listed individually in `sitemap.xml`.

| File | URL |
|------|-----|
| `index.html` | `/` |
| `free-public-apis.html` | `/free-public-apis` - generated from [`../API.md`](../API.md), see Editing |
| `free-public-api-<name>-api-endpoint.html` | one page per endpoint, 49 of them, each at its matching URL |
| `free-qr-code-decoder-api.html` | `/free-qr-code-decoder-api` - browser tool for the QR decode endpoint |
| `free-public-mcp-server.html` | `/free-public-mcp-server` |
| `hashing-apis.html` | `/hashing-apis` |
| `encoding-apis.html` | `/encoding-apis` |
| `random-generator-apis.html` | `/random-generator-apis` |
| `time-apis.html` | `/time-apis` |
| `custom-apis.html` | `/custom-apis` |
| `upload.html` | `/upload` |
| `tokenizer-cost-study.html` | `/tokenizer-cost-study` |
| `verifyum.html` | `/verifyum` |
| `verifyum-private-file-proofs.html` | `/verifyum-private-file-proofs` |
| `make-your-data-available-for-ai.html` | `/make-your-data-available-for-ai` |
| `ai-sense-posts.html` | `/ai-sense-posts` |
| `smart-beehive-monitoring-system.html` | `/smart-beehive-monitoring-system` |
| `about.html` | `/about` |
| `contact-us.html` | `/contact-us` |
| `login.html` | `/login` - static shadow page, excluded from search indexing |
| `privacy.html` | `/privacy` - **needs legal review, see below** |
| `terms.html` | `/terms` - **needs legal review, see below** |
| `assets/aisense.css` | shared stylesheet |
| `assets/posts/smart-beehive-monitoring-system.jpg` | image for the beehive post |
| `404.html` | served by `ErrorDocument` for any unknown path, noindex |
| `.htaccess` | 301 redirects from the old URL scheme, error page |
| `robots.txt` | crawler directives and sitemap location |
| `sitemap.xml` | canonical URLs for search engines |

## Deploying

**This directory is not what deploys.** The site is published from the
`website` branch, which carries these same files at the repository root,
without this README, on a history of its own -
`git merge-base --is-ancestor origin/website origin/main` answers no.

So every change here needs a second commit on `website` before it reaches the
live site. There is no publish script; the two sides are kept in step by hand,
with the same commit message on each. Pushing a fix to `main` alone changes
nothing on aisense.no, and the symptom is indistinguishable from a failed
deploy - you pull on the web host, the HTML is unchanged, and the search goes
looking for caching or a wrong document root. Check parity instead:

```bash
diff <(git ls-tree -r origin/website | awk '{print $3, $4}' | sort) \
     <(git ls-tree -r origin/main -- web | awk '{print $3, substr($4,5)}' \
       | grep -v README.md | sort)
```

Empty output means both branches carry the same site. Any line is a file that
exists on one side only - on the `main` side, that is a page written but not
published.

What is checked out on the web host, read from its own config on 2026-08-25:

```
remote.origin.url=https://github.com/aisenseapi/aisense-free-public-rest-apis.git
remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*
branch.website.remote=origin
branch.website.merge=refs/heads/website
```

A full clone with `website` checked out, at `/var/www/htdocs/www.aisense.no`,
which is also the DocumentRoot. The repository is public, so that machine needs
no credentials at all - unlike the one holding the service source. Publishing is
then the whole of:

```bash
git pull --ff-only
```

One caveat on keeping this README off the live host. The branch split keeps it
out of the *working tree*, but the refspec above fetches every branch, so all of
`main` - this file included - sits in `.git` on that machine. What makes it
unreachable is the `Require all denied` on `.git` in the vhost, not the branch
split. Cloning with `--single-branch -b website` would fetch `website` alone and
let the split carry its own weight.

## Three things the webserver has to do

**Serve extensionless URLs.** Every link here points at `/about`, not
`/about.html`, because those are the URLs the site already has and the ones
search engines have indexed. Files on disk carry the `.html` extension, so the
server has to bridge the two. In Apache:

```apache
Options +MultiViews
```

or explicitly:

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME}.html -f
RewriteRule ^(.*)$ $1.html [L]
```

In nginx: `try_files $uri $uri.html $uri/ =404;`

The live vhost does neither - it maps extensionless URLs with an `AliasMatch`
on a single path segment. Two behaviours follow from that, both measured
against the live site on 2026-08-25 and both worth knowing before diagnosing
anything here.

An unknown path maps to a missing `.html` file rather than reaching a router,
so a wrong URL 404s instead of being handled. And the alias tolerates a
trailing slash: `/about/` returns 200 with the same bytes as `/about`, with no
redirect between them, so the canonical tag is the only thing telling search
engines which of the two counts. That second one is why the stylesheet had to
become root-relative - as a relative path it resolved to
`/about/assets/aisense.css` from the slash form, and the page rendered
unstyled.

**Point the document root at the site root** - the top of the `website`
checkout, where `index.html` and `assets/` sit. Every path in these pages,
including the stylesheet, is root-relative, so mounting them one directory
down breaks `/assets/aisense.css` on every page at once. A symlink works if
changing the vhost is awkward.

**Let `.htaccess` apply.** `.htaccess` here holds the 301 redirects from the
pre-rebuild URL scheme plus `ErrorDocument 404 /404.html`. Apache ignores the
file unless the vhost allows it:

```apache
<Directory "/path/to/document/root">
    AllowOverride FileInfo
</Directory>
```

`FileInfo` is the minimum that covers `Redirect*` and `ErrorDocument`; `None`
makes the file inert with no warning anywhere - it is present, readable, and
has no effect, which is a genuinely confusing failure to diagnose. After
changing a vhost, run `apachectl configtest` before `apachectl graceful`.

The redirects matter: the site was rebuilt from a WordPress install that
published one page per endpoint at `/free-public-api-<name>-api-endpoint`.
Those 36 URLs plus the feed, category, author and embed paths are all still in
search indexes, and each one 301s to the page that now covers its content.
Verify after any server change - `curl -sI https://aisense.no/free-public-api-storage-api-endpoint`
must answer 301, not 404.

## Editing

`free-public-mcp-server.html` documents the remote MCP endpoint. Its complete
protocol notes and tool list live in [`../MCP.md`](../MCP.md). Update both when
the production tool list changes.

`free-public-apis.html` is generated from [`../API.md`](../API.md), which is the
verified source of truth for every request and response format - each one was
checked against the live service. **Change `API.md` first, then reflect it
here.** Letting the page drift from `API.md` recreates exactly the problem this
repository was cleaned up to fix: documentation describing an API that does not
exist.

`../test.sh` asserts the documented formats against production, so a drift
between `API.md` and reality shows up as a test failure rather than as a
confused user.

## Known gaps

**The contact form is not here.** The WordPress original used Contact Form 7.
These are static files with no backend, so a form would render, submit and
silently discard the message - worse than no form. `contact-us.html` shows the
email address instead, with the options for restoring a working form written up
in a comment in that file.

**The wordmark is CSS text, not the logo file.** Drop the real asset into
`assets/` and replace the `<span class="wordmark">` in each page's header with
an `<img>`. The place to change is marked in `assets/aisense.css`.

**`privacy.html` and `terms.html` have not been reviewed by a lawyer.** Every
factual claim in them was read out of the service source on 2026-08-16 - the
rate limit, the 24-hour expiry, the third parties, what the access log records -
so they describe this system honestly rather than repeating a template. That is
not the same as being a sound legal document. Each file opens with an HTML
comment naming the specific points that need a qualified decision: the lawful
basis asserted for logging IP addresses, whether the liability limitation
survives Norwegian law, and whether a data processing agreement is needed with
the four named third parties.

They also state retention periods that depend on
`tools/logrotate-aisense.conf` from the service repository being installed on
the API host. That is done - `deploy.sh` syncs the unit on every deploy and
reports it, last confirmed 2026-08-19 - so the retention numbers are now true.
If the rotation is ever removed, the honest answer becomes "until the host
reboots" and the privacy page is wrong again.

Both pages describe the service. When the service changes, they have to change
with it, or they become promises nobody is keeping.

**Posts are static.** Add each new article as a standalone HTML file, link it
from `ai-sense-posts.html`, and add its canonical URL to `sitemap.xml`.

## Style

Colours and typography come from the live site's own Astra/Elementor globals, so
these pages sit next to the WordPress ones without reading as a different
property:

| Token | Value | Use |
|-------|-------|-----|
| `--blue` | `#046bd2` | Links, primary accents |
| `--blue-dark` | `#045cb4` | Hover |
| `--ink` | `#1e293b` | Headings |
| `--body` | `#334155` | Body text |
| `--tint` | `#f0f5fa` | Panels, table headers |
| `--border` | `#d1d5db` | Rules |

Roboto and Roboto Slab are referenced by name rather than fetched from Google
Fonts. The pages therefore make no external requests, work offline, and set no
third-party cookies. Visitors without Roboto installed fall back to the system
sans-serif.
