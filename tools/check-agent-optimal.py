"""Offline checks for the Agent Optimal mark. No network or file writes."""
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree

from agent_optimal import BADGE, SERVICES, decorate, marked_label

WEB = Path(__file__).resolve().parents[1] / 'web'


class AgentOptimalTests(unittest.TestCase):
    def test_only_the_five_approved_services(self):
        self.assertEqual(list(SERVICES.values()), ['Agent Wake', 'Agent Queue', 'Agent Inbox', 'Heartbeat', 'Lease'])

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

    def test_svg_is_self_contained_and_keeps_the_approved_a(self):
        asset = WEB / 'assets/agent-optimal.svg'
        root = ElementTree.parse(asset).getroot()
        self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
        for node in root.iter():
            self.assertNotIn(node.tag.rsplit('}', 1)[-1], ('script', 'image', 'foreignObject'))
            for name, value in node.attrib.items():
                if name.rsplit('}', 1)[-1] == 'href':
                    self.assertTrue(value.startswith('#'))
        svg = asset.read_text(encoding='utf-8')
        self.assertIn('rotate(-5 6.5 9)', svg)
        self.assertIn('#b6bfc8', svg)
        ring = root.find('{http://www.w3.org/2000/svg}circle')
        self.assertIsNotNone(ring)
        self.assertEqual(ring.get('stroke'), '#046bd2')
        self.assertEqual(ring.get('stroke-width'), '3.5')

    def test_round_icon_has_no_old_square_background(self):
        css = (WEB / 'assets/aisense.css').read_text(encoding='utf-8')
        rule = re.search(r'\.agent-optimal-mark\s*\{([^}]+)\}', css)[1]
        self.assertIn('padding: 0;', rule)
        self.assertIn('background: transparent;', rule)
        self.assertIn('border-radius: 50%;', rule)
        self.assertIn('v=20261003c', BADGE)

    def test_generated_pages_are_current(self):
        pages = list(WEB.glob('*.html'))
        self.assertGreater(len(pages), 100)
        for page in pages:
            source = page.read_text(encoding='utf-8')
            with self.subTest(page=page.name):
                self.assertEqual(decorate(source, page.name), source)
                header = re.search(r'<header class="site-header">.*?</header>', source, re.S)
                if header:
                    self.assertEqual(header[0].count(BADGE), 5)
                title = re.search(r'<h1\b[^>]*>.*?</h1>', source, re.S)
                if title:
                    expected = 1 if '/' + page.stem in SERVICES else 0
                    self.assertEqual(title[0].count(BADGE), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
