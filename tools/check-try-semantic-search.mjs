// Checks web/assets/try-semantic-search.js against fake API answers: no call
// ever reaches the network, no collection is created, no model is used.
// It also checks the page itself: its JSON-LD, canonical URL, internal links
// and sitemap entry.
//
// Run from anywhere with: node tools/check-try-semantic-search.mjs

import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, '..', 'web');
const require = createRequire(import.meta.url);
const core = require(join(web, 'assets', 'try-semantic-search.js'));

let passed = 0;
let failed = 0;
function check(ok, label) {
  if (ok) { passed++; console.log('  ok    ' + label); } else { failed++; console.log('  FAIL  ' + label); }
}

const ID = 'a'.repeat(32);
const READ = 'b'.repeat(64);
const WRITE = 'c'.repeat(64);
const NOTE_IDS = ['1', '2', '3', '4', '5', '6', '7', '8'].map((d) => d.repeat(32));
const T0 = 1791400000;

function answer(status, json, headers = {}) {
  return { status, json, headers: { 'Content-Type': 'application/json', ...headers } };
}
function created(model = 'bge-m3', extra = {}) {
  return answer(201, { ok: true, collection_id: ID, model, created_at_timestamp: T0, expire_timestamp: T0 + 86400,
    notes: 0, notes_added: 0, notes_max: 500, read_token: READ, write_token: WRITE, ...extra });
}
function added(notes, extra = {}) {
  return answer(201, { ok: true, collection_id: ID, added: notes.map((n, i) => ({ note_id: NOTE_IDS[i], key: n.key === undefined ? null : n.key })),
    notes: notes.length, notes_added: notes.length, expire_timestamp: T0 + 86400, ...extra });
}
function found(hits, model = 'bge-m3') {
  return answer(200, { ok: true, collection_id: ID, model, results: hits, notes: 4, expire_timestamp: T0 + 86400 });
}

/** A fake fetch: answers in order, records every call. An entry may be 'network', 'hang' or a function. */
function fakeFetch(script) {
  const calls = [];
  const fetch = (url, init) => {
    calls.push({ url, init });
    const next = script.shift();
    if (next === undefined) { return Promise.reject(new Error('unexpected call ' + url)); }
    if (next === 'network') { return Promise.reject(new TypeError('Failed to fetch')); }
    if (next === 'hang') {
      return new Promise((resolve, reject) => { init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))); });
    }
    const raw = next.raw !== undefined ? next.raw : JSON.stringify(next.json);
    const headers = next.headers || {};
    return Promise.resolve({
      status: next.status,
      headers: { get: (name) => { const key = Object.keys(headers).find((k) => k.toLowerCase() === name.toLowerCase()); return key === undefined ? null : headers[key]; } },
      text: () => Promise.resolve(raw)
    });
  };
  return { fetch, calls };
}

function setup(script, extra = {}) {
  const fake = fakeFetch(script);
  let clock = T0 * 1000;
  const changes = [];
  const controller = core.createController({ fetch: fake.fetch, now: () => clock, onChange: (s) => changes.push(s), timeoutMs: extra.timeoutMs });
  return { controller, calls: fake.calls, changes, advance: (ms) => { clock += ms; }, clock: () => clock };
}

const SAMPLES = core.SAMPLE_NOTES.map((n) => ({ text: n.text, key: n.key }));
const sentNotes = SAMPLES.map((n) => ({ text: n.text, key: n.key }));

console.log('Page load and examples');
{
  const t = setup([]);
  check(t.calls.length === 0 && t.controller.state().phase === 'draft', 'a new page makes no call: the controller starts in draft with nothing sent');
  check(core.SAMPLE_QUERIES.length === 4 && core.SAMPLE_NOTES.length === 4, 'four example notes and four example searches, which only fill in fields');
  const source = readFileSync(join(web, 'assets', 'try-semantic-search.js'), 'utf8');
  const exampleHandler = source.match(/button\.addEventListener\('click', function \(\) \{ queryInput\.value = text; queryInput\.focus\(\); \}\);/);
  check(exampleHandler !== null, 'an example button sets the search text and focus, and sends nothing');
  check(!/innerHTML|insertAdjacentHTML|outerHTML|document\.write/.test(source), 'the script never writes markup: text goes to the page with textContent');
  check(!/console\./.test(source) && !/localStorage|sessionStorage|document\.cookie/.test(source), 'no console output, no storage and no cookies');
  check(!/setInterval/.test(source), 'no polling');
}

console.log('Create and add');
{
  const t = setup([created(), added(sentNotes)]);
  const first = t.controller.create(SAMPLES, 'bge-m3');
  const second = await t.controller.create(SAMPLES, 'bge-m3');
  const searchWhileBusy = await t.controller.search('x', 3);
  await first;
  const s = t.controller.state();
  check(second === false && searchWhileBusy === false, 'a second click or a search while busy sends nothing');
  check(t.calls.length === 2, 'one click makes exactly two calls: one collection, one call with all the notes');
  const [c1, c2] = t.calls;
  check(c1.url === core.API && c1.init.method === 'POST' && c1.init.body === '{"model":"bge-m3"}' && !('Authorization' in c1.init.headers),
    'the collection is created with POST and the model, without a token');
  check(c2.url === core.API + '/' + ID + '/notes' && c2.init.headers.Authorization === 'Bearer ' + WRITE && JSON.parse(c2.init.body).notes.length === 4,
    'the notes go in one call with the write token');
  check([c1, c2].every((c) => c.init.credentials === 'omit' && c.init.cache === 'no-store' && c.init.referrerPolicy === 'no-referrer'
    && c.init.redirect === 'error' && c.init.signal && c.init.headers['Content-Type'] === 'application/json'),
    'every call omits credentials, skips the cache, sends no referrer, follows no redirect and can be aborted');
  check(s.phase === 'ready' && s.collection.notes === 4 && s.collection.model === 'bge-m3' && s.collection.expires === T0 + 86400,
    'the collection is ready with its model, its four notes and the expiry the API gave');
  check(!JSON.stringify(s).includes(READ) && !JSON.stringify(s).includes(WRITE), 'the page state, the JSON view included, never holds a token');
  check(t.calls.every((c) => !c.url.includes(READ) && !c.url.includes(WRITE)), 'no token in any URL');
  const again = await t.controller.create(SAMPLES, 'qwen3-embedding-4b');
  check(again === false && t.calls.length === 2 && t.controller.state().collection.model === 'bge-m3', 'once created, the model and the notes are locked: a new create sends nothing');
}

console.log('Search');
{
  const hits = [
    { note_id: NOTE_IDS[0], key: 'incident:login', text: '<img src=x onerror=alert(1)>', score: 1.0823 },
    { note_id: NOTE_IDS[1], key: null, text: 'Mange mislykkede innlogginger', score: -0.0412 }
  ];
  const t = setup([created(), added(sentNotes), found(hits)]);
  await t.controller.create(SAMPLES, 'bge-m3');
  await t.controller.search('brute force attack on the admin login', 3);
  const s = t.controller.state();
  const c = t.calls[2];
  check(c.url === core.API + '/' + ID + '/search' && c.init.headers.Authorization === 'Bearer ' + READ
    && c.init.body === '{"query":"brute force attack on the admin login","limit":3}', 'a search reuses the collection and the read token');
  check(s.results.hits.length === 2 && s.results.hits[0].text === '<img src=x onerror=alert(1)>' && s.results.hits[1].key === null,
    'results keep the text as the API gave it, markup included, for the page to show as text');
  check(core.formatScore(1.0823) === '1.0823' && core.formatScore(-0.0412) === '-0.0412' && core.formatScore(0.5) === '0.5000',
    'scores are raw numbers with four decimals: above 1 and below 0 as they are, never a percentage');
  check(!JSON.stringify(s.exchange).includes(READ) && s.exchange.request.url.endsWith('/search'), 'the JSON view shows the last request and answer without a token');
}

console.log('Refusals before writing keep the collection');
{
  const refused = answer(400, { error: 'Each note needs text, as nonempty UTF-8.', fix: 'Correct the field the message names and send the request again.' });
  const t = setup([created(), refused, added(sentNotes)]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const s1 = t.controller.state();
  check(s1.phase === 'notes-refused' && s1.collection !== null && /refused the notes before storing them/.test(s1.message.text),
    'notes the API refuses before storing them leave the collection and its tokens in place');
  await t.controller.create(SAMPLES, 'bge-m3');
  check(t.calls.length === 3 && t.calls[2].url === core.API + '/' + ID + '/notes' && t.controller.state().phase === 'ready',
    'the corrected notes go to the same collection: no second collection');
}
{
  const t = setup([created(), answer(429, { error: 'Model request limit reached.', fix: 'Respect Retry-After when present.' }, { 'Retry-After': '30' })]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const s = t.controller.state();
  check(s.phase === 'notes-refused' && s.waitMs === 30000, 'a 429 on the notes keeps the collection and waits the 30 seconds Retry-After gives');
  const early = await t.controller.create(SAMPLES, 'bge-m3');
  check(early === false && t.calls.length === 2, 'nothing is sent during the wait');
  t.advance(31000);
  t.controller.recheck();
  check(t.controller.state().waitMs === 0 && t.calls.length === 2, 'when the wait is over the button may be pressed again, and nothing was sent on its own');
}

console.log('Unknown outcomes are never sent again');
for (const [label, script] of [
  ['no answer at all', 'network'],
  ['a generic 503 after the collection exists', answer(503, { error: 'Search storage is unavailable', fix: 'Try again later. Nothing was changed.' })],
  ['a 500', answer(500, { error: 'Search failed', fix: 'A server error occurred. Try again later.' })],
  ['a 201 that does not look like success', answer(201, { ok: true, collection_id: ID, added: [] })],
  ['an HTML error page', { status: 502, raw: '<html><body>Bad gateway</body></html>', headers: { 'Content-Type': 'text/html' } }]
]) {
  const t = setup([created(), script]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const s = t.controller.state();
  const again = await t.controller.create(SAMPLES, 'bge-m3');
  check(s.phase === 'uncertain' && /cannot tell whether the notes were stored/.test(s.message.text) && again === false && t.calls.length === 2
    && !/<html/i.test(s.message.text), 'notes call with ' + label + ': uncertain, said so, and never sent again');
}
{
  const t = setup([created(), 'hang'], { timeoutMs: 40 });
  await t.controller.create(SAMPLES, 'bge-m3');
  const s = t.controller.state();
  check(s.phase === 'uncertain' && /no answer within/.test(JSON.stringify(s.exchange)), 'a notes call that hits the client time limit is uncertain, not refused');
  t.calls.length = 2;
}
{
  const t = setup([created(), 'network', found([])]);
  await t.controller.create(SAMPLES, 'bge-m3');
  await t.controller.search('anything', 3);
  check(t.calls.length === 3 && t.calls[2].url.endsWith('/search') && t.controller.state().phase === 'uncertain',
    'after an uncertain notes call the visitor can still search the collection');
}
for (const [label, script] of [
  ['no answer', 'network'],
  ['a 503', answer(503, { error: 'Search storage is unavailable', fix: 'Try again later. Nothing was changed.' })],
  ['a 201 without a write token', created('bge-m3', { write_token: undefined })],
  ['a 201 with another model', created('qwen3-embedding-4b')]
]) {
  const t = setup([script]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const s = t.controller.state();
  const again = await t.controller.create(SAMPLES, 'bge-m3');
  check(s.phase === 'create-uncertain' && s.collection === null && t.calls.length === 1 && again === false,
    'creation with ' + label + ': no notes sent, uncertain, not repeated');
}
{
  const t = setup([answer(429, { error: 'Collection limit reached for this 24-hour window', fix: 'Reuse a collection or wait.' },
    { 'Retry-After': new Date((T0 + 120) * 1000).toUTCString() })]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const s = t.controller.state();
  check(s.phase === 'draft' && s.waitMs === 120000 && /No collection was created/.test(s.message.text), 'a 429 on creation with an HTTP date waits until that date');
  const early = await t.controller.create(SAMPLES, 'bge-m3');
  check(early === false && t.calls.length === 1, 'and sends nothing before it');
}
{
  const t = setup([answer(429, { error: 'Collection limit reached for this 24-hour window' }, { 'Retry-After': 'soon' })]);
  await t.controller.create(SAMPLES, 'bge-m3');
  check(t.controller.state().waitMs === 0, 'a Retry-After the page cannot read invents no waiting time');
}

console.log('Same keys are not deduplicated');
{
  const twice = [{ text: 'The same note.', key: 'note:1' }, { text: 'The same note.', key: 'note:1' }];
  const t = setup([created(), added(twice)]);
  await t.controller.create(twice, 'bge-m3');
  check(JSON.parse(t.calls[1].init.body).notes.length === 2 && t.controller.state().collection.notes === 2, 'two notes with the same key are both sent and both stored');
}

console.log('Checked before anything is sent');
{
  const t = setup([]);
  const cases = [
    [[{ text: '   ', key: '' }], 'is empty'],
    [[{ text: 'x'.repeat(2001), key: '' }], 'has 2001 characters'],
    [[{ text: '\u{1F600}'.repeat(2001), key: '' }], 'has 2001 characters'],
    [[{ text: 'ok', key: '-bad' }], 'may hold letters'],
    [Array.from({ length: 9 }, () => ({ text: 'n', key: '' })), 'at most 8 notes'],
    [Array.from({ length: 8 }, () => ({ text: '\u0001'.repeat(2000), key: '' })), 'bytes as JSON']
  ];
  for (const [rows, expect] of cases) {
    const outcome = await t.controller.create(rows, 'bge-m3');
    check(Array.isArray(outcome) && outcome.some((p) => p.message.includes(expect)) && t.calls.length === 0, 'refused here, nothing sent: ' + expect);
  }
  check(core.checkNotes([{ text: '\u{1F600}'.repeat(2000), key: '' }]).problems.length === 0, '2000 emoji are 2000 characters, though JavaScript counts 4000 units');
  check(core.checkQuery(' ', 3).length === 1 && core.checkQuery('x'.repeat(501), 3).length === 1 && core.checkQuery('ok', 11).length === 1
    && core.checkQuery('ok', 3).length === 0, 'an empty or too long search and a limit outside 1 to 10 are refused here');
  check(core.checkNotes([{ text: 'Kunden fikk feil faktura', key: 'faktura:7' }]).problems.length === 0, 'Unicode text and a valid key pass');
}

console.log('Answers the page explains');
{
  const statuses = [401, 403, 404, 410, 413, 502, 503, 504];
  for (const status of statuses) {
    const t = setup([created(), added(sentNotes), answer(status, { error: 'Status ' + status + ' error', fix: 'The fix for ' + status + '.' })]);
    await t.controller.create(SAMPLES, 'bge-m3');
    await t.controller.search('anything', 3);
    const s = t.controller.state();
    check(s.message.text.includes('Status ' + status + ' error') && s.results === null, 'a search answered ' + status + ' says what the API said and shows no results');
  }
  const t = setup([created(), added(sentNotes), { status: 504, raw: '<!DOCTYPE html><html><body>Gateway Timeout</body></html>', headers: { 'Content-Type': 'text/html' } }]);
  await t.controller.create(SAMPLES, 'bge-m3');
  await t.controller.search('anything', 3);
  check(/HTTP 504 in a form this page does not read/.test(t.controller.state().message.text), 'an HTML error page is never shown: a short line with the status instead');
}

console.log('Old results and expiry');
{
  const t = setup([created(), added(sentNotes), found([{ note_id: NOTE_IDS[0], key: 'k', text: 't', score: 0.5 }]),
    answer(503, { error: 'The selected model is temporarily unavailable.', fix: 'Do not retry automatically.' })]);
  await t.controller.create(SAMPLES, 'bge-m3');
  await t.controller.search('first', 3);
  const p = t.controller.search('second', 3);
  check(t.controller.state().results === null, 'a new search clears the old results as it starts');
  await p;
  check(t.controller.state().results === null, 'and a failed search shows none, so the old results are never read as its answer');
}
{
  const t = setup([created(), added(sentNotes)]);
  await t.controller.create(SAMPLES, 'bge-m3');
  t.advance(86401 * 1000);
  const outcome = await t.controller.search('late', 3);
  check(outcome === false && t.calls.length === 2 && t.controller.state().phase === 'expired', 'past the expiry a search is stopped here, without a call');
}
{
  const t = setup([created(), added(sentNotes), answer(410, { error: 'Collection has expired', fix: 'Create a new collection.' })]);
  await t.controller.create(SAMPLES, 'bge-m3');
  await t.controller.search('still there?', 3);
  check(t.controller.state().phase === 'expired', 'a 410 from the API ends the collection even when the local clock disagrees');
}

console.log('Starting again');
{
  const t = setup([created(), added(sentNotes)]);
  await t.controller.create(SAMPLES, 'bge-m3');
  const ok = t.controller.reset();
  const s = t.controller.state();
  check(ok && s.collection === null && s.phase === 'draft' && t.calls.length === 2 && /stays on the server until it expires/.test(s.message.text),
    'a new test forgets the collection here, sends nothing, and says the collection stays on the server');
}

console.log('The page');
{
  const html = readFileSync(join(web, 'try-semantic-search.html'), 'utf8');
  const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  let ld = null;
  try { ld = JSON.parse(blocks[0]); } catch (e) { ld = null; }
  check(blocks.length === 1 && ld && ld['@graph'].some((n) => n['@type'] === 'WebPage') && ld['@graph'].some((n) => n['@type'] === 'BreadcrumbList'),
    'the JSON-LD parses, with a WebPage and a BreadcrumbList');
  check(html.includes('<link rel="canonical" href="https://aisense.no/try-semantic-search">') && html.includes('<meta property="og:url" content="https://aisense.no/try-semantic-search">'),
    'canonical and Open Graph name https://aisense.no/try-semantic-search');
  const missing = [...html.matchAll(/(?:href|src)="(\/[^"#?]*)/g)].map((m) => m[1]).filter((href) => {
    const path = href.replace(/^\//, '');
    if (path === '') { return false; }
    return !existsSync(join(web, path)) && !existsSync(join(web, path + '.html'));
  });
  check(missing.length === 0, 'every internal link points at a file in web/' + (missing.length ? ': missing ' + missing.join(', ') : ''));
  check(/<noscript>/.test(html) && /role="status"/.test(html) && /aria-live="polite"/.test(html) && /aria-busy=/.test(html), 'noscript, a live status line and aria-busy are there');
  check(!/[0-9a-f]{64}|Bearer [A-Za-z0-9]/.test(html), 'no token value and no Authorization header in the HTML');
  const sitemap = readFileSync(join(web, 'sitemap.xml'), 'utf8');
  check(sitemap.includes('<loc>https://aisense.no/try-semantic-search</loc>'), 'the sitemap lists the page');
}

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed === 0 ? 0 : 1);
