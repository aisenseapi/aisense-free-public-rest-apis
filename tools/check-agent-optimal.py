"""Offline checks for the Agent Optimal mark. No network or file writes."""
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree

from agent_optimal import BADGE, SERVICES, decorate, marked_label

WEB = Path(__file__).resolve().parents[1] / 'web'


class AgentOptimalTests(unittest.TestCase):
    def test_only_the_approved_services(self):
        self.assertEqual(list(SERVICES.values()), ['Agent Wake', 'Agent Queue', 'Agent Inbox', 'Heartbeat', 'Lease', 'Decide', 'Webhook action', 'Semantic search', 'AI SENSE AIQ'])
        for label in ('AIQ agent tests', 'AIQ API Endpoint', 'AI SENSE AIQ'):
            marked = decorate('<a href="/aisense-aiq">' + label + '</a>', 'index.html')
            self.assertEqual(marked.count(BADGE), 1)
        for prose in ('<a href="/aisense-aiq">Read the product note</a>', '<a href="/aisense-aiq-versions#ard">ard, 100 tasks</a>',
                      '<a href="/aisense-aiq">AI SENSE AIQ: How Smart Is Your Agent?</a>'):
            self.assertEqual(decorate(prose, 'index.html'), prose)

    def test_an_alias_is_marked_and_prose_is_not(self):
        marked = decorate('<a href="/free-public-api-decide-api-endpoint">Decision API Endpoint</a>', 'index.html')
        self.assertEqual(marked.count(BADGE), 1)
        prose = '<a href="/free-public-api-decide-api-endpoint">Read the Decision guide</a>'
        self.assertEqual(decorate(prose, 'index.html'), prose)
        for label in ('Webhook Action REST API Endpoint', 'Human Approval API Endpoint'):
            marked = decorate('<a href="/free-public-api-webhook-action-api-endpoint">' + label + '</a>', 'index.html')
            self.assertEqual(marked.count(BADGE), 1)
        prose = '<a href="/free-public-api-webhook-action-api-endpoint">Read the Webhook Action API guide</a>'
        self.assertEqual(decorate(prose, 'index.html'), prose)
        for label in ('Semantic Search API', 'Semantic Search REST API Endpoint', 'Free Semantic Search API Endpoint'):
            marked = decorate('<a href="/free-public-api-semantic-search-api-endpoint">' + label + '</a>', 'index.html')
            self.assertEqual(marked.count(BADGE), 1)
        prose = '<a href="/free-public-api-semantic-search-api-endpoint">Read the semantic search guide</a>'
        self.assertEqual(decorate(prose, 'index.html'), prose)

    def test_name_links(self):
        for href, name in SERVICES.items():
            for label in (name, name + ' API', name + ' REST API Endpoint', 'Free ' + name + ' API Endpoint'):
                with self.subTest(label=label):
                    original = '<a href="' + href + '">' + label + '</a>'
                    marked = decorate(original, 'index.html')
                    self.assertEqual(marked.count(BADGE), 1)
                    self.assertEqual(decorate(marked, 'index.html'), marked)

    def test_card_mark_precedes_the_description(self):
        source = '<a href="/free-public-api-agent-queue-api-endpoint"><strong>Agent Queue API</strong><span>Share jobs.</span></a>'
        result = decorate(source, 'free-public-apis.html')
        self.assertIn(marked_label('Agent Queue API') + '</strong><span>Share jobs.</span>', result)

    def test_relative_and_our_absolute_links(self):
        for origin in ('', 'https://aisense.no', 'https://www.aisense.no'):
            self.assertIn(BADGE, decorate('<a href="' + origin + '/free-public-api-lease-api-endpoint#usage">Lease</a>', 'index.html'))

    def test_unapproved_prose_and_external_links_stay_unchanged(self):
        for source in (
            '<a href="/free-public-api-dns-name-api-endpoint">Temporary DNS names</a>',
            '<a href="/free-public-api-agent-queue-api-endpoint">Read the Agent Queue guide</a>',
            '<a href="https://example.com/free-public-api-lease-api-endpoint">Lease</a>',
        ):
            self.assertEqual(decorate(source, 'index.html'), source)

    def test_only_service_page_headings(self):
        source = '<h1 id="page-title">Free Agent Wake API Endpoint</h1>'
        self.assertIn(BADGE, decorate(source, 'free-public-api-agent-wake-api-endpoint.html'))
        self.assertEqual(decorate(source, 'index.html'), source)

    def test_scripts_code_comments_and_metadata_are_not_changed(self):
        link = '<a href="/free-public-api-lease-api-endpoint">Lease</a>'
        source = ('<script>' + link + '</script><pre><code>' + link + '</code></pre><!--' + link + '-->'
                  '<title>Agent Wake</title><meta name="description" content="Agent Wake">')
        self.assertEqual(decorate(source, 'free-public-api-agent-wake-api-endpoint.html'), source)

    def test_last_word_and_mark_stay_together(self):
        self.assertTrue(marked_label('Agent Queue').startswith('Agent <span class="agent-optimal-tail">Queue'))
        self.assertIn('alt="Agent Optimal"', BADGE)
        self.assertIn('title="Agent Optimal', BADGE)

    def test_removed_service_loses_its_mark(self):
        href = '/free-public-api-lease-api-endpoint'
        marked = decorate('<a href="' + href + '">Lease</a>', 'index.html')
        label = SERVICES.pop(href)
        try:
            self.assertNotIn(BADGE, decorate(marked, 'index.html'))
        finally:
            SERVICES[href] = label

    def test_svg_is_self_contained_and_uses_selected_16px_variant(self):
        asset = WEB / 'assets/agent-optimal.svg'
        root = ElementTree.parse(asset).getroot()
        self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
        self.assertEqual(root.get('width'), '16')
        self.assertEqual(root.get('height'), '16')
        self.assertEqual(root.get('viewBox'), '0 0 16 16')
        for node in root.iter():
            self.assertIn(node.tag.rsplit('}', 1)[-1], ('svg', 'title', 'path'))
            for name, value in node.attrib.items():
                if name.rsplit('}', 1)[-1] == 'href':
                    self.assertTrue(value.startswith('#'))
        paths = root.findall('{http://www.w3.org/2000/svg}path')
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0].get('fill'), '#046bd2')
        self.assertEqual(paths[0].get('d'), 'M6 0h4v2H9v1h3l2 2v1h2v5h-2v2l-2 2H4l-2-2v-2H0V6h2V5l2-2h3V2H6z')
        self.assertEqual(paths[1].get('fill'), '#fff')
        self.assertEqual(paths[1].get('d'), 'M4 6h3v3H4zM9 6h3v3H9zM6 11h4v1H6z')

    def test_16px_icon_has_no_padding_background_or_clipping(self):
        css = (WEB / 'assets/aisense.css').read_text(encoding='utf-8')
        rule = re.search(r'\.agent-optimal-mark\s*\{([^}]+)\}', css)[1]
        self.assertIn('padding: 0;', rule)
        self.assertIn('background: transparent;', rule)
        self.assertIn('border-radius: 0;', rule)
        self.assertIn('width: 16px;', rule)
        self.assertIn('height: 16px;', rule)
        self.assertIn('width="16" height="16"', BADGE)
        self.assertIn('v=20261003f', BADGE)

    def test_generated_pages_are_current(self):
        pages = list(WEB.glob('*.html'))
        self.assertGreater(len(pages), 100)
        for page in pages:
            source = page.read_text(encoding='utf-8')
            with self.subTest(page=page.name):
                self.assertEqual(decorate(source, page.name), source)
                header = re.search(r'<header class="site-header">.*?</header>', source, re.S)
                if header:
                    self.assertEqual(header[0].count(BADGE), len(SERVICES))
                title = re.search(r'<h1\b[^>]*>.*?</h1>', source, re.S)
                if title:
                    expected = 1 if '/' + page.stem in SERVICES else 0
                    self.assertEqual(title[0].count(BADGE), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
