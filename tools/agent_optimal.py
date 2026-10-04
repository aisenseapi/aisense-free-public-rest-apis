"""The seven Agent Optimal labels selected for the website.

This is an AI SENSE editorial label for agent workflows, not a certification
or a production health signal. Used by site_nav.py after rendering the header.
Only service-name links and the selected services' h1 get the mark. Prose,
code samples, JSON-LD, page titles and descriptions are left alone.
"""
import re
from urllib.parse import urlsplit


SERVICES = {
    '/free-public-api-agent-wake-api-endpoint': 'Agent Wake',
    '/free-public-api-agent-queue-api-endpoint': 'Agent Queue',
    '/free-public-api-agent-inbox-api-endpoint': 'Agent Inbox',
    '/free-public-api-heartbeat-api-endpoint': 'Heartbeat',
    '/free-public-api-lease-api-endpoint': 'Lease',
    '/free-public-api-decide-api-endpoint': 'Decide',
    '/free-public-api-webhook-action-api-endpoint': 'Webhook action',
}

# Other names a name link to a service may use, such as the endpoint page's own title.
ALIASES = {
    '/free-public-api-decide-api-endpoint': ['Decision'],
    '/free-public-api-webhook-action-api-endpoint': ['Webhook Action', 'Human Approval'],
}

BADGE = ('<img class="agent-optimal-mark" src="/assets/agent-optimal.svg?v=20261003f" '
         'width="16" height="16" alt="Agent Optimal" '
         'title="Agent Optimal - Built for agent workflows. An AI SENSE label.">')

PROTECTED = re.compile(r'(<script\b[^>]*>.*?</script>|<pre\b[^>]*>.*?</pre>|<!--.*?-->)', re.S | re.I)
LINK = re.compile(r'(<a\b[^>]*>)(.*?)(</a>)', re.S | re.I)
HREF = re.compile(r'\bhref="([^"]+)"')
TITLE = re.compile(r'(<h1\b[^>]*>)([^<]+)(</h1>)', re.I)
OLD_MARK = re.compile(r'<span class="agent-optimal-tail">([^<]+)<img class="agent-optimal-mark"[^>]*></span>')


def marked_label(label):
    """Keep the last word with the icon, without making a long title unbreakable."""
    before, separator, last = label.rpartition(' ')
    return before + separator + '<span class="agent-optimal-tail">' + last + BADGE + '</span>'


def service_path(href):
    url = urlsplit(href)
    if url.scheme not in ('', 'https') or url.netloc not in ('', 'aisense.no', 'www.aisense.no'):
        return None
    return url.path.rstrip('/')


def mark_link(match):
    opening, body, closing = match.groups()
    href = HREF.search(opening)
    path = service_path(href.group(1)) if href else None
    service = SERVICES.get(path)
    if not service:
        return match.group(0)
    label = re.fullmatch(r'(<strong>)?([^<]+)(</strong>)?(<span\b.*)?', body, re.S)
    if not label or bool(label[1]) != bool(label[3]):
        return match.group(0)
    # Do not decorate prose links such as "Read the Agent Queue guide".
    names = '|'.join(re.escape(name) for name in [service] + ALIASES.get(path, []))
    if not re.fullmatch(r'(?:Free )?(?:' + names + r')(?: (?:REST )?API(?: Endpoint)?)?', label[2]):
        return match.group(0)
    return opening + (label[1] or '') + marked_label(label[2]) + (label[3] or '') + (label[4] or '') + closing


def decorate(source, filename):
    parts = PROTECTED.split(source)
    for index in range(0, len(parts), 2):
        # Rebuild our own labels, so removing a service also removes its mark.
        content = OLD_MARK.sub(r'\1', parts[index])
        content = LINK.sub(mark_link, content)
        if '/' + filename.removesuffix('.html') in SERVICES:
            content = TITLE.sub(lambda m: m[1] + marked_label(m[2]) + m[3], content)
        parts[index] = content
    return ''.join(parts)
