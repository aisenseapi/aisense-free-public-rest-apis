# aisense.no — static pages

Plain HTML. No build step, no framework, no third-party requests. Open any file
in a browser and it renders.

| File | URL |
|------|-----|
| `index.html` | `/` |
| `free-public-apis.html` | `/free-public-apis` |
| `custom-apis.html` | `/custom-apis` |
| `make-your-data-available-for-ai.html` | `/make-your-data-available-for-ai` |
| `about.html` | `/about` |
| `contact-us.html` | `/contact-us` |
| `privacy.html` | `/privacy` — **needs legal review, see below** |
| `terms.html` | `/terms` — **needs legal review, see below** |
| `assets/aisense.css` | shared stylesheet |

## Deploying

Pull only this directory onto the aisense.no host with a sparse checkout. This
repository is public, so that machine needs no credentials at all — unlike the
one holding the service source.

```bash
git clone --filter=blob:none --sparse https://github.com/aisenseapi/aisense-free-public-rest-apis.git .
git sparse-checkout set web
```

`--filter=blob:none` is the part that matters. `sparse-checkout` alone decides
what gets written to the working tree; without the filter the rest of the
repository is still downloaded. With it, blobs are fetched only for paths in the
sparse set.

After that, `git pull` is the whole deploy.

## Two things the webserver has to do

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

**Point the document root at `web/`,** not at the repository root — otherwise
the pages sit one directory down and `assets/aisense.css` resolves to the wrong
place. A symlink works if changing the vhost is awkward.

## Editing

`free-public-apis.html` is generated from [`../API.md`](../API.md), which is the
verified source of truth for every request and response format — each one was
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
silently discard the message — worse than no form. `contact-us.html` shows the
email address instead, with the options for restoring a working form written up
in a comment in that file.

**The wordmark is CSS text, not the logo file.** Drop the real asset into
`assets/` and replace the `<span class="wordmark">` in each page's header with
an `<img>`. The place to change is marked in `assets/aisense.css`.

**`privacy.html` and `terms.html` have not been reviewed by a lawyer.** Every
factual claim in them was read out of the service source on 2026-08-16 — the
rate limit, the 24-hour expiry, the third parties, what the access log records —
so they describe this system honestly rather than repeating a template. That is
not the same as being a sound legal document. Each file opens with an HTML
comment naming the specific points that need a qualified decision: the lawful
basis asserted for logging IP addresses, whether the liability limitation
survives Norwegian law, and whether a data processing agreement is needed with
the four named third parties.

They also state retention periods that are only true once
`tools/logrotate-aisense.conf` from the service repository is installed. Until
then the honest answer is "until the host reboots", and the privacy page is
wrong. Install the rotation before publishing, or change the numbers.

Both pages describe the service. When the service changes, they have to change
with it, or they become promises nobody is keeping.

**`/ai-sense-posts` is linked but not built.** It is in the site navigation. If
`web/` becomes the whole site rather than sitting alongside WordPress, that link
will 404.

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
