"""Write the endpoint pages for /decide and /chaos into web/.

The page around the content, from the head to the footer, is taken from
web/free-public-api-dns-name-api-endpoint.html. The /decide examples and their
answers are in data/decide-examples.json, worked out by the Python reference
the service is tested against, so the pages show what the service answers.

Usage: python make_logic_pages.py <web> <decide-examples.json>
"""
import html
import io
import json
import sys
from collections import OrderedDict

WEB = sys.argv[1]
EXAMPLES = json.load(io.open(sys.argv[2], encoding='utf-8'), object_pairs_hook=OrderedDict)
API = 'https://aisenseapi.com/services/v1'
TEMPLATE = io.open(WEB + '/free-public-api-dns-name-api-endpoint.html', encoding='utf-8').read()
B = chr(92)

STYLE = '''<style>
.try-api textarea, .try-api select { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: #fff; color: var(--ink); }
.try-api textarea { font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.try-api select { min-height: 48px; font: inherit; }
.try-api .button-row { margin: 14px 0; }
.try-api pre { margin: 0; max-height: 520px; overflow: auto; }
</style>'''


def fmt(value, indent=0):
    """Two-space JSON, with anything short enough kept on one line."""
    one = json.dumps(value, ensure_ascii=False, separators=(', ', ': '))
    if len(one) + indent <= 92 or not isinstance(value, (dict, list)):
        return one
    pad = ' ' * (indent + 2)
    if isinstance(value, dict):
        items = [pad + json.dumps(key, ensure_ascii=False) + ': ' + fmt(item, indent + 2) for key, item in value.items()]
        return '{\n' + ',\n'.join(items) + '\n' + ' ' * indent + '}'
    items = [pad + fmt(item, indent + 2) for item in value]
    return '[\n' + ',\n'.join(items) + '\n' + ' ' * indent + ']'


def pre(text):
    return '<pre><code>' + html.escape(text, quote=False) + '</code></pre>'


def decide_curl(request):
    return ('curl -s -X POST ' + API + '/decide ' + B + '\n  -H "Content-Type: application/json" ' + B
            + "\n  -d '" + fmt(request) + "'")


def example(key):
    run = EXAMPLES[key]
    return pre(decide_curl(run['request'])) + pre(fmt(run['answer']))


def table(head, rows):
    return ('<div class="table-wrap field-table"><table><thead><tr>' + ''.join('<th>%s</th>' % h for h in head)
            + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>%s</td>' % c for c in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def page(slug, title, description, og_title, og_description, api_name, api_description, crumb, main, script):
    out = TEMPLATE
    head_end = out.index('<main')
    main_end = out.index('</main>') + len('</main>')
    top, bottom = out[:head_end], out[main_end:]

    def swap(text, start, end, value):
        i = text.index(start) + len(start)
        j = text.index(end, i)
        return text[:i] + value + text[j:]

    top = swap(top, '<title>', '</title>', html.escape(title, quote=False))
    top = swap(top, '<meta name="description" content="', '">', html.escape(description))
    top = swap(top, '<link rel="canonical" href="', '">', 'https://aisense.no/' + slug)
    top = swap(top, '<meta property="og:title" content="', '">', html.escape(og_title))
    top = swap(top, '<meta property="og:description" content="', '">', html.escape(og_description))
    top = swap(top, '<meta property="og:url" content="', '">', 'https://aisense.no/' + slug)
    ld = OrderedDict([('@context', 'https://schema.org'), ('@graph', [
        OrderedDict([('@type', 'WebAPI'), ('name', api_name), ('description', api_description),
                     ('url', 'https://aisense.no/' + slug), ('documentation', 'https://aisense.no/free-public-apis#logic'),
                     ('provider', OrderedDict([('@type', 'Organization'), ('name', 'AI SENSE AS'), ('url', 'https://aisense.no/')]))]),
        OrderedDict([('@type', 'BreadcrumbList'), ('itemListElement', [
            OrderedDict([('@type', 'ListItem'), ('position', 1), ('name', 'Home'), ('item', 'https://aisense.no/')]),
            OrderedDict([('@type', 'ListItem'), ('position', 2), ('name', 'Free public REST APIs'), ('item', 'https://aisense.no/free-public-apis')]),
            OrderedDict([('@type', 'ListItem'), ('position', 3), ('name', crumb), ('item', 'https://aisense.no/' + slug)])])])])])
    top = swap(top, '<script type="application/ld+json">\n', '\n</script>', json.dumps(ld, indent=2, ensure_ascii=False))
    stylesheet_end = top.index('>', top.index('<link rel="stylesheet"')) + 1
    top = top[:stylesheet_end] + '\n' + STYLE + top[stylesheet_end:]
    body = top + main + '\n<script>\n' + script.strip('\n') + '\n</script>' + bottom
    io.open(WEB + '/' + slug + '.html', 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote', slug + '.html', len(body.encode('utf-8')), 'bytes')


def hero(eyebrow, h1, lede, badges, label, sig, url):
    return ('<section class="api-detail-hero" aria-labelledby="page-title"><div><p class="eyebrow">%s</p><h1 id="page-title">%s</h1>'
            '<p class="lede">%s</p><ul class="badges">%s</ul></div><div class="endpoint-banner"><p class="endpoint-banner-label">%s</p>%s'
            '<code>%s</code></div></section>') % (eyebrow, h1, lede, ''.join('<li>%s</li>' % b for b in badges), label, sig, url)


def crumbs(name):
    return ('<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/free-public-apis">'
            'Free public REST APIs</a></li><li aria-current="page">%s</li></ol></nav>') % name


def cards(items):
    return '<div class="use-case-grid">' + ''.join('<article><h3>%s</h3><p>%s</p></article>' % item for item in items) + '</div>'


def related(items):
    return '<div class="related-api-grid">' + ''.join('<a href="%s">%s<span>%s</span></a>' % item for item in items) + '</div>'


# -- /decide ------------------------------------------------------------------

TICKET = EXAMPLES['ticket']['request']
DECIDE_TRY = json.dumps(TICKET, indent=2, ensure_ascii=False)

DECIDE_MAIN = '''<main id="main-content" class="api-detail-main">
''' + crumbs('Decision API endpoint') + '''

''' + hero('Logic - Decisions', 'Free Decision API Endpoint',
           'Send the facts and your rules, and get typed decisions back: yes or no, one of several options, or a level on a scale. '
           'Rules are the default and explain each answer. Optional model selection uses the same endpoint with a separate question format '
           'and strict capacity limits. Clef is available only when enabled by the operator.',
           ['No API key', 'One POST', 'Rules by default', 'Optional model selection'],
           'Decide', '<p class="sig"><span class="method post">POST</span><span class="path">/decide</span></p>', API + '/decide') + '''

<div class="api-detail-body">

<section id="quick-start"><h2>Call the free Decision API endpoint</h2><p>Send a <code>state</code>, the facts to decide on, and named <code>questions</code>. Each question has rules, and each rule is a condition and a weight. This one routes a support ticket and decides whether the refund can go through at once:</p>''' + example('ticket') + '''<p>The refund gets &minus;2 + 2 + 1 + 1 + 1 = 3, and sigmoid(3) = 0.9526. Its confidence, 0.9051, is above 0.9, so the action is <code>act</code>: it can go through without anyone looking. The team gets softmax over 3, 1 and 0, and a confidence of 0.7657 says <code>review</code>. <code>because</code> lists the rules that held, including the word "money" that pulled a little towards billing.</p></section>

<section id="questions"><h2>Three kinds of rule question</h2><p>Omit <code>model</code> or send <code>"model":"rules"</code> for the existing rule format. Its response is unchanged.</p>''' + table(['Type', 'Answers with', 'How it is worked out'], [
    ['<code>yes_no</code>', '<code>answer</code>, <code>probability</code>', 'sigmoid(<code>bias</code> + the weights of the rules that held)'],
    ['<code>choice</code>', '<code>choice</code>, <code>probabilities</code>', 'softmax over each option: its prior plus the weights of its rules that held'],
    ['<code>scale</code>', '<code>level</code>, <code>expected</code>, <code>probabilities</code>', 'a choice over ordered levels; <code>expected</code> counts the first level as 0'],
]) + '''<p>Every answer also has <code>confidence</code>, <code>action</code> and <code>because</code>. A weight is evidence in log-odds: positive pulls towards the answer, negative away, and 1 multiplies the odds by about 2.7. <code>bias</code> is where a yes_no starts, 0 unless you set it, and <code>priors</code> give options or levels a head start.</p></section>

<section id="conditions"><h2>Conditions</h2><p>A condition is an object of fields and tests, and every field must hold. A field is a dotted path into the state, where a number picks from a list: <code>items.0.sku</code>. <code>any</code> is a list of conditions of which one must hold, and <code>not</code> holds when its condition does not.</p>''' + table(['Test', 'Holds when the value'], [
    ['<code>eq</code>, <code>ne</code>', 'equals, or does not equal, the given text, number, true, false or null. 1 equals 1.0; true is not 1'],
    ['<code>gt</code>, <code>gte</code>, <code>lt</code>, <code>lte</code>', 'is a number above, at least, below or at most the given number'],
    ['<code>in</code>', 'equals one of a list of up to 100 values'],
    ['<code>exists</code>', 'is there (<code>true</code>) or is not (<code>false</code>)'],
    ['<code>prefix</code>', 'is text that starts with the given text, whatever the case'],
    ['<code>contains</code>', 'is text that contains the given text, whatever the case, or a list that holds the given item'],
]) + '''<p>A path that leads nowhere fails every test except <code>exists: false</code>, so <code>ne</code> on a missing field does not hold. There are no regular expressions, so no condition can make the server spend minutes on one match.</p></section>

<section id="confidence"><h2>Confidence and the action</h2><p>Confidence is (n &times; the largest probability &minus; 1) / (n &minus; 1): 1 when everything is on one answer, 0 when it is spread evenly. For yes_no it is |2p &minus; 1|. The action is <code>act</code> from <code>act_at</code>, 0.9 unless you set it, <code>review</code> from <code>review_at</code>, 0.5 unless you set it, and <code>hold</code> below. Set the thresholds by what a wrong answer costs: a refund of a few euros can act at 0.9, a deletion should not act at all. When two options tie at the top, the first one listed wins and <code>tied</code> names them, so a split is never hidden.</p></section>

<section id="examples"><h2>More examples</h2><h3>Can an agent run this command without asking?</h3><p>A cheap gate in front of an agent that runs commands. The default is yes, and dangerous patterns pull it down.</p>''' + example('command') + '''<p>3 &minus; 4 &minus; 1 + 1 = &minus;1 gives 0.2689: no, with a confidence of 0.46, so <code>hold</code> and ask a person. The same request with <code>git status</code> answers yes at 0.982 and <code>act</code>.</p><h3>How bad is this alert?</h3><p>A scale with four levels, acting at 0.8, because paging the person on call is right a little more often than it is wrong.</p>''' + example('alert') + '''<h3>Who should take the job?</h3><p>The cheapest layer first: rules, a small model, a large one, a person. Here the large model and the person tie, and the answer says so.</p>''' + example('route') + '''<p>A confidence of 0.20 gives <code>hold</code>. The rules say plainly that they cannot tell, and the code can then send the job to the safer of the two.</p></section>

<section id="try"><h2>Try it</h2><p>Write the request yourself below, or build it in a form with examples and read the answer in plain words on <a href="/try-decide">Try Decide</a>.</p><div class="try-card try-api"><label for="decide-body">Request body</label><textarea id="decide-body" rows="20" spellcheck="false">''' + html.escape(DECIDE_TRY, quote=False) + '''</textarea><div class="button-row"><button type="button" class="button button-primary" id="decide-run">Decide</button></div><p class="try-status" id="decide-status" aria-live="polite"></p><pre><code id="decide-out"></code></pre></div></section>

<section id="models"><h2>Optional Clef model</h2><p>Send <code>"model":"clef"</code> with instructions and criteria instead of weighted rules. This mode is disabled by default until the operator has measured the backend. A disabled model returns 503. An unknown model returns 400. Neither falls back to rules.</p>''' + pre(json.dumps({
    "model": "clef",
    "state": {"message": "The production API returns HTTP 500 and blocks checkout."},
    "questions": {"urgent": {
        "type": "noul", "instructions": "Does this need urgent attention?",
        "criteria": {"true": "An active production failure blocks business.", "false": "The issue can wait."}
    }}
}, indent=2)) + '''<p>This is a request example, not a measured production result. The response has <code>model</code>, <code>model_version</code>, <code>answers</code> and optional token <code>usage</code>.</p>''' + table(['Model type', 'Criteria', 'Answer'], [
    ['<code>noul</code>', 'An object with descriptions named <code>true</code> and <code>false</code>', 'Numeric <code>noul</code> from 0 to 1, not a Boolean'],
    ['<code>choice</code>', 'An object of named descriptions', '<code>choice</code>, <code>probabilities</code> and <code>confidence</code>'],
    ['<code>score</code>', 'An ordered list of labels', '<code>score</code>, <code>legend</code>, <code>probabilities</code> and <code>confidence</code>'],
]) + '''<p>A score starts at zero for the first label and can be fractional. Model confidence comes from the backend and does not use the rule formula above. Model answers have no <code>action</code> or <code>because</code>. Do not mix model criteria with <code>rules</code>, <code>act_at</code> or <code>review_at</code>. Model output can be wrong. Keep human approval for consequential actions.</p><h3>Model capacity limits</h3><p>Default limits are 8 KiB of JSON, 4 questions, 8 choices or score levels, 1024 UTF-8 bytes per instruction and 512 per criterion. Per IP, at most 2 starts per UTC minute and 20 per UTC calendar day. All callers and models share 6 starts per minute and 300 per UTC day. One model call can run at a time, with no waiting queue and at least 10 seconds between starts. The connection deadline is 2 seconds, the total deadline 30 seconds and the reply cap 32 KiB. Failed admitted calls count too. The operator can change these limits after measurement.</p><p>Respect <code>Retry-After</code> on timed refusals. Do not retry in a loop. If a timeout leaves the remote computation uncertain, model calls stay closed until an operator checks it. Rules remain available. Callers cannot choose the backend URL, model version or limits.</p></section>

<section id="errors"><h2>Errors</h2><p>Refusals include <code>error</code> and <code>fix</code>. No request or answer body is saved by the Decide API. Model mode records counters and timing aggregates.</p>''' + table(['Status', 'When'], [
    ['400', 'A field is missing, of the wrong kind or out of range, or the body is not valid JSON. The error names the place, such as <code>questions.team.options.returns[0].weight</code>'],
    ['405', 'Any method but POST'],
    ['413', 'The body is over 64 KiB for rules or the configured model byte limit, or the rules hold more than 5000 tests'],
    ['415', 'The body is not sent as <code>application/json</code>'],
    ['429', 'The service-wide limit of 5000 requests per IP per day, or a model quota'],
    ['502', 'The model backend returned an error, a malformed reply or a broken transfer'],
    ['503', 'The model is disabled, busy, pacing new calls, unavailable or awaiting operator recovery'],
    ['504', 'The model transport deadline was reached'],
]) + '''</section>

<section id="use-cases"><h2>When rules fit</h2>''' + cards([
    ('Guardrails for agents', 'Decide whether an action may run on its own, needs a look, or has to wait for a person.'),
    ('Routing and triage', 'Send tickets, alerts and jobs to the right place, and see why they went there.'),
    ('Confidence-gated automation', 'Act only when the evidence is strong, with a threshold that fits what a mistake costs.'),
    ('A cheap first layer', 'Answer the clear cases with rules, and hand only the uncertain ones to a model or a person.'),
]) + '''</section>

<section id="privacy"><h2>Privacy and limits</h2><p>Rules run inside the API worker without sending the state to another service or saving the request body. Rule limits are 64 KiB of JSON, 64 questions, 100 options, 20 levels, 50 rules per list, weights from &minus;100 to 100, 5000 tests and 8 levels of <code>any</code> and <code>not</code>. The service-wide ceiling is 5000 requests per IP per Norwegian day.</p><p>Model mode sends state and questions to the configured external inference machine. The API keeps quota counters keyed by an IP HMAC and aggregate timings, not input or answer bodies. The backend has separate data handling that must be confirmed before public activation. Keep credentials and sensitive personal data out. Ordinary access logs still record IP addresses and other request metadata. See <a href="/privacy">Privacy</a>.</p></section>

<section id="related"><h2>Related endpoints</h2>''' + related([
    ('/free-public-apis', 'Free public REST APIs', 'The full endpoint reference'),
    ('/free-public-api-chaos-api-endpoint', 'Chaos API Endpoint', 'Test clients against failures'),
    ('/free-public-api-webhook-action-api-endpoint', 'Human Approval API Endpoint', 'Ask a person when the answer is review'),
    ('/free-public-api-agent-queue-api-endpoint', 'Agent Queue API Endpoint', 'Hand decided work to workers'),
]) + '''</section>

</div>
</main>'''

DECIDE_SCRIPT = r'''
(function () {
  var body = document.getElementById('decide-body');
  var run = document.getElementById('decide-run');
  var status = document.getElementById('decide-status');
  var out = document.getElementById('decide-out');

  function show(text, state) {
    status.textContent = text;
    status.className = 'try-status' + (state ? ' is-' + state : '');
  }

  run.addEventListener('click', function () {
    var parsed;

    try {
      parsed = JSON.parse(body.value);
    } catch (error) {
      show('The body is not valid JSON: ' + error.message, 'bad');
      out.textContent = '';
      return;
    }

    run.disabled = true;
    show('Deciding');
    fetch('https://aisenseapi.com/services/v1/decide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed)
    }).then(function (response) {
      return response.json().then(function (json) {
        show('HTTP ' + response.status, response.ok ? 'ok' : 'bad');
        out.textContent = JSON.stringify(json, null, 2);
      });
    }).catch(function (error) {
      show('The request failed: ' + error.message, 'bad');
    }).then(function () {
      run.disabled = false;
    });
  });
})();
'''

page('free-public-api-decide-api-endpoint',
     'Free Decision API Endpoint: Rules and Model Selection | AI SENSE',
     'Send facts and weighted rules, get typed decisions back: yes or no, a choice or a scale, with probabilities, confidence and the rules that fired. Free, no key.',
     'Free Decision API Endpoint',
     'Typed decisions from your own rules. Optional Clef model selection uses separate questions and capacity limits, when enabled.',
     'Free Decision API Endpoint',
     'Answers weighted rule questions by default. Optional Clef model mode supports noul, choice and score questions when enabled, with separate capacity limits.',
     'Decision API endpoint', DECIDE_MAIN, DECIDE_SCRIPT)

# -- /chaos -------------------------------------------------------------------

STATUS_ROWS = [
    ['200, 201', '<code>{"ok": true, "chaos": {...}}</code>'],
    ['204', 'No body'],
    ['400, 403, 404, 409, 410, 422', '<code>{"error": "Not Found", "chaos": {...}}</code>, with the status\'s own reason phrase'],
    ['401', 'The same, with <code>WWW-Authenticate: Bearer realm="chaos"</code>'],
    ['429, 503', 'The same, with <code>Retry-After: 2</code>'],
    ['500, 502, 504', 'The same'],
]

PYTHON_TEST = '''import time, urllib.request, urllib.error

BASE = "https://aisenseapi.com/services/v1/chaos"

def get(url, tries=3, timeout=2):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status
        except urllib.error.HTTPError as error:
            if error.code in (429, 503) and attempt < tries - 1:
                time.sleep(int(error.headers.get("Retry-After", "1")))
                continue
            raise

start = time.time()
try:
    get(BASE + "/503")
    raise AssertionError("503 never reached the caller")
except urllib.error.HTTPError as error:
    assert error.code == 503 and time.time() - start >= 4, "gave up too early"

try:
    get(BASE + "/200/3000")
    raise AssertionError("no timeout")
except (TimeoutError, urllib.error.URLError):
    pass

print("client handles 503 and slow answers")'''

CHAOS_MAIN = '''<main id="main-content" class="api-detail-main">
''' + crumbs('Chaos API endpoint') + '''

''' + hero('Logic - Testing', 'Free Chaos API Endpoint',
           'Point a client at <code>/chaos</code> and it gets the failure you picked: a 503 with <code>Retry-After</code>, a 429, an answer that comes '
           'late, a proxy&#39;s HTML error page, an empty body or JSON labelled as text. Test retries, timeouts and parsing against the failures '
           'you otherwise meet only in production.',
           ['No API key', 'Any method', '15 statuses', 'Delays up to 10 s', 'Nothing stored'],
           'Answer with a failure', '<p class="sig"><span class="method">ANY</span><span class="path">/chaos/{status}[/{ms}]</span></p>',
           API + '/chaos/503') + '''

<div class="api-detail-body">

<section id="quick-start"><h2>Call the free Chaos API endpoint</h2><p>Put the status you want in the path. The answer comes at once, with any method, and neither the body nor the query string is read, so the client under test can call the way it always does.</p>''' + pre('curl -s ' + API + '/chaos/503') + pre('{"error":"Service Unavailable","chaos":{"status":503,"delay_ms":0}}') + '''<p>Add a delay in milliseconds as one more segment, up to 10000:</p>''' + pre('curl -s ' + API + '/chaos/200/3000') + pre('{"ok":true,"chaos":{"status":200,"delay_ms":3000}}') + '''<p>The answer arrives after three seconds. A client with a shorter deadline should give up, which is what the test checks; curl reports 28 for a timeout:</p>''' + pre('curl -s --max-time 1 ' + API + '/chaos/200/3000; echo "exit $?"') + '''</section>

<section id="statuses"><h2>Statuses</h2><p>200, 201, 204, 400, 401, 403, 404, 409, 410, 422, 429, 500, 502, 503 and 504, each with the headers a real service would send with it:</p>''' + table(['Status', 'Answer'], STATUS_ROWS) + pre('curl -si ' + API + '/chaos/429') + pre('HTTP/2 429\nretry-after: 2\ncontent-type: application/json\nx-chaos: 429\n\n{"error":"Too Many Requests","chaos":{"status":429,"delay_ms":0}}') + '''</section>

<section id="events"><h2>Broken answers</h2><p>Three answers that break a client which assumes everything is JSON. Each takes a delay the same way, for example <code>/chaos/html/2000</code>.</p>''' + table(['Path', 'Answer', 'What goes wrong in a naive client'], [
    ['<code>/chaos/html</code>', '502 with an HTML page, as a proxy answers when the service behind it is down', 'Parsing JSON fails on <code>&lt;html&gt;</code>'],
    ['<code>/chaos/empty</code>', '200 labelled <code>application/json</code>, with no body', '"Unexpected end of JSON input"'],
    ['<code>/chaos/wrongtype</code>', '200 with valid JSON labelled <code>text/plain</code>', 'A client that trusts the type treats the answer as text'],
]) + pre('curl -s ' + API + '/chaos/wrongtype') + pre('{"ok":true,"chaos":{"event":"wrongtype","delay_ms":0}}') + '''</section>

<section id="real-or-chosen"><h2>A chosen failure, or a real one</h2><p>Every chosen answer carries <code>X-Chaos</code> with what the path asked for, such as <code>503</code> or <code>200/3000</code>, and a <code>chaos</code> object in the JSON body. A real refusal never has either, and has <code>fix</code> instead.</p><p>A delay holds a place while it waits, at most four at a time from one address. When none is free the answer is a real 503 with <code>Retry-After: 1</code> and no <code>X-Chaos</code>, and nothing waits. An answer without a delay needs no place.</p></section>

<section id="client-test"><h2>A client test in Python, with nothing to install</h2>''' + pre(PYTHON_TEST) + '''<p>It passes when the client tries three times with the two-second pause <code>Retry-After</code> asks for, and gives up on an answer slower than its deadline.</p></section>

<section id="try"><h2>Try it</h2><div class="try-card try-api"><label for="chaos-path">Answer</label><select id="chaos-path"><option value="503">503 Service Unavailable</option><option value="429">429 Too Many Requests</option><option value="401">401 Unauthorized</option><option value="500">500 Internal Server Error</option><option value="204">204 No Content</option><option value="200/3000">200 after 3 seconds</option><option value="html">html: a proxy&#39;s error page</option><option value="empty">empty: 200 with no body</option><option value="wrongtype">wrongtype: JSON labelled text/plain</option></select><div class="button-row"><button type="button" class="button button-primary" id="chaos-run">Call</button></div><p class="try-status" id="chaos-status" aria-live="polite"></p><pre><code id="chaos-out"></code></pre></div></section>

<section id="errors"><h2>Errors</h2>''' + table(['Status', 'When'], [
    ['404', 'A path that is not one of the forms, or a status chaos does not answer with. The <code>fix</code> lists the statuses and events'],
    ['400', 'A delay over 10000 milliseconds'],
    ['503 without <code>X-Chaos</code>', 'No place free for a delay, with <code>Retry-After: 1</code>'],
    ['429', 'The service-wide limit of 5000 requests per IP per day, which chaos calls count towards'],
]) + '''</section>

<section id="use-cases"><h2>What to test with it</h2>''' + cards([
    ('Retries', 'That a client retries 503 and 429, waits what Retry-After says, and stops after a fixed number of tries.'),
    ('Timeouts', 'That a slow answer ends in a timeout the client handles, not a hung job.'),
    ('Parsers', 'That an HTML error page, an empty body or a wrong content type gives a clear error, not a crash.'),
    ('Agents and tools', 'That an agent reads an error, backs off and reports it, instead of trying the same thing forever.'),
]) + '''</section>

<section id="privacy"><h2>Privacy and limits</h2><p>Nothing is written or stored. The body and the query string are not read, but the access log line records the path and any query string, as it does for every request, so keep anything private out of the query. Delays run up to 10000 milliseconds, four at a time from one address, and every call counts towards the service-wide 5000 requests per IP per day.</p></section>

<section id="related"><h2>Related endpoints</h2>''' + related([
    ('/free-public-apis', 'Free public REST APIs', 'The full endpoint reference'),
    ('/free-public-api-decide-api-endpoint', 'Decision API Endpoint', 'Typed decisions from your rules'),
    ('/free-public-api-webhook-capture-api-endpoint', 'Webhook Capture API Endpoint', 'See the request a client sends'),
    ('/free-public-api-heartbeat-api-endpoint', 'Heartbeat API Endpoint', 'Notice when a job stops checking in'),
]) + '''</section>

</div>
</main>'''

CHAOS_SCRIPT = r'''
(function () {
  var path = document.getElementById('chaos-path');
  var run = document.getElementById('chaos-run');
  var status = document.getElementById('chaos-status');
  var out = document.getElementById('chaos-out');

  run.addEventListener('click', function () {
    var started = performance.now();
    run.disabled = true;
    status.className = 'try-status';
    status.textContent = 'Calling /chaos/' + path.value;
    out.textContent = '';
    fetch('https://aisenseapi.com/services/v1/chaos/' + path.value).then(function (response) {
      return response.text().then(function (text) {
        var parts = ['HTTP ' + response.status, Math.round(performance.now() - started) + ' ms'];
        var type = response.headers.get('Content-Type');
        var retry = response.headers.get('Retry-After');
        if (type) { parts.push('Content-Type: ' + type); }
        if (retry) { parts.push('Retry-After: ' + retry); }
        status.textContent = parts.join(' - ');
        out.textContent = text === '' ? '(no body)' : text;
      });
    }).catch(function (error) {
      status.className = 'try-status is-bad';
      status.textContent = 'The request failed: ' + error.message;
    }).then(function () {
      run.disabled = false;
    });
  });
})();
'''

page('free-public-api-chaos-api-endpoint',
     'Free Chaos API Endpoint: Test Clients Against Failures | AI SENSE',
     'Answers with the failure you ask for: any of 15 statuses, a delay up to 10 seconds, an HTML error page, an empty body or JSON with the wrong type. Free.',
     'Free Chaos API Endpoint',
     'Test retries, timeouts and parsing: pick a status, a delay or a broken answer, and point your client at it. No key, nothing stored.',
     'Free Chaos API Endpoint',
     'Answers with a chosen HTTP status or a broken response, at once or after a delay of up to 10 seconds, for testing how clients handle failures. Nothing is stored.',
     'Chaos API endpoint', CHAOS_MAIN, CHAOS_SCRIPT)
