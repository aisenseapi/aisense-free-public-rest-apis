/*
 * Try semantic search: pick an example or write a few notes, put them in a new
 * collection on the free Semantic Search API, and search them by meaning.
 *
 * As on /try-decide, the page writes the JSON it will send and shows it. The
 * notes JSON can be edited by hand; an edited JSON is sent as it stands until
 * it is written again from the form.
 *
 * Nothing is sent until a button is pressed: no collection, model call or
 * search on page load, and no polling. One collection per test. Its id and
 * tokens live only in this script's memory, never in the page, a URL, storage
 * or the console, so a reload loses the page's access without deleting
 * anything on the server. The requests on the page show the tokens as
 * WRITE_TOKEN and READ_TOKEN.
 *
 * A write whose outcome cannot be known (a timeout, a broken connection, a
 * generic server error, an answer that does not look like success) is never
 * sent again by this page: the visitor is told it is uncertain. Only a refusal
 * that the API makes before it writes (a field it rejects, a limit) leaves the
 * notes open for correction, and they then go to the same collection.
 *
 * Everything a visitor types or the API answers is put on the page as text,
 * never as markup. The core below has no DOM, so tools/check-try-semantic-search.mjs
 * runs it in Node against fake API answers.
 */
(function () {
  'use strict';

  var API = 'https://aisenseapi.com/services/v1/semantic_search';
  var MODELS = ['bge-m3', 'qwen3-embedding-4b'];
  var LIFETIME = 86400;
  var LIMITS = { formNotes: 8, noteChars: 2000, queryChars: 500, resultsMax: 10, bodyBytes: 65536 };
  var KEY = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
  var HEX32 = /^[0-9a-f]{32}$/;
  var HEX64 = /^[0-9a-f]{64}$/;
  var TIMEOUT_MS = 45000;

  // Example notes and searches. The last search of each set has no note
  // written for it: a search always ranks the notes there are.
  var EXAMPLES = [
    {
      id: 'support', title: 'Support tickets',
      notes: [
        { key: 'incident:login', text: 'Suspicious login attempts from many addresses on the admin page.' },
        { key: 'incident:checkout', text: 'The checkout API returns HTTP 500 for every customer since 08:10.' },
        { key: 'request:invoice', text: 'A customer needs the address corrected on an invoice PDF.' },
        { key: 'request:password', text: 'A user never receives the email to reset their password.' },
        { key: 'incident:search', text: 'Product search takes more than ten seconds since the last release.' }
      ],
      searches: ['brute force attack on the admin login', 'customers cannot pay', 'change the billing address', 'where is my parcel']
    },
    {
      id: 'memory', title: 'Agent memory',
      notes: [
        { key: 'decision:database', text: 'We chose PostgreSQL over MongoDB because the reports need joins.' },
        { key: 'todo:backup', text: 'Set up nightly backups of the order database before Friday.' },
        { key: 'fact:deploys', text: 'Deploys go out on Tuesdays and Thursdays after 14:00.' },
        { key: 'contact:billing', text: 'Questions about invoices go to the finance team, not to support.' },
        { key: 'fact:staging', text: 'The staging server gets fresh test data every Monday morning.' }
      ],
      searches: ['which database did we pick and why', 'when can I release a change', 'who answers billing questions', 'the office coffee machine is broken']
    },
    {
      id: 'shop', title: 'Shop questions',
      notes: [
        { key: 'faq:returns', text: 'Items can be returned within 30 days with the receipt.' },
        { key: 'faq:shipping', text: 'Orders ship within two working days, and tracking comes by email.' },
        { key: 'faq:warranty', text: 'Electronics have a two-year warranty against defects.' },
        { key: 'faq:payment', text: 'We accept cards, invoices and bank transfers.' },
        { key: 'faq:gift-cards', text: 'Gift cards are valid for three years and cannot be exchanged for cash.' }
      ],
      searches: ['can I send it back', 'how long does delivery take', 'my headphones broke after a year', 'do you sell bicycles']
    },
    {
      id: 'ids', title: 'Order and ticket numbers',
      notes: [
        { key: 'order:4711', text: 'Order 4711 was delivered to the wrong address.' },
        { key: 'order:4712', text: 'Order 4712 is still waiting for payment.' },
        { key: 'ticket:TKT-77', text: 'Ticket TKT-77 is about a broken gate sensor at dock 4.' },
        { key: 'ticket:TKT-78', text: 'Ticket TKT-78 asks for a new parking permit.' }
      ],
      searches: ['what happened to order 4711', 'TKT-78', 'a package went to the wrong place', 'order 4713']
    }
  ];

  // ---------- the core: no DOM ----------

  function chars(text) { return Array.from(text).length; }

  function bodyBytes(body) { return new TextEncoder().encode(JSON.stringify(body)).length; }

  function isInt(value) { return typeof value === 'number' && Number.isSafeInteger(value); }

  /** The notes as the API takes them: text, and a key only when there is one. */
  function notesBody(rows) {
    return {
      notes: rows.map(function (row) {
        var note = { text: typeof row.text === 'string' ? row.text : '' };
        var key = typeof row.key === 'string' ? row.key.trim() : '';
        if (key !== '') { note.key = key; }
        return note;
      })
    };
  }

  /**
   * The notes of the form as the API takes them, or the problems, one per
   * field. Text is never cut: a note over the limit is refused here.
   */
  function checkNotes(rows) {
    var problems = [];
    if (!Array.isArray(rows) || rows.length < 1) {
      return { notes: [], problems: [{ index: -1, field: 'notes', message: 'Write at least one note.' }] };
    }
    if (rows.length > LIMITS.formNotes) {
      problems.push({ index: -1, field: 'notes', message: 'This test takes at most ' + LIMITS.formNotes + ' notes. Remove ' + (rows.length - LIMITS.formNotes) + '.' });
    }
    rows.forEach(function (row, i) {
      var text = typeof row.text === 'string' ? row.text : '';
      var key = typeof row.key === 'string' ? row.key.trim() : '';
      var count = chars(text);
      if (text.trim() === '') {
        problems.push({ index: i, field: 'text', message: 'Note ' + (i + 1) + ' is empty. Write a short text or remove the note.' });
      } else if (count > LIMITS.noteChars) {
        problems.push({ index: i, field: 'text', message: 'Note ' + (i + 1) + ' has ' + count + ' characters. The limit is ' + LIMITS.noteChars + '. Shorten it; nothing is cut for you.' });
      }
      if (key !== '' && !KEY.test(key)) {
        problems.push({ index: i, field: 'key', message: 'The key of note ' + (i + 1) + ' may hold letters, digits, dots, underscores, colons and hyphens, must start with a letter or digit, and be at most 64 characters. Or leave it empty.' });
      }
    });
    var body = notesBody(rows);
    if (problems.length === 0 && bodyBytes(body) > LIMITS.bodyBytes) {
      problems.push({ index: -1, field: 'notes', message: 'The notes come to ' + bodyBytes(body) + ' bytes as JSON. The limit is ' + LIMITS.bodyBytes + '. Shorten them.' });
    }
    return { notes: problems.length === 0 ? body.notes : [], problems: problems };
  }

  /**
   * The rows of a notes JSON edited by hand: exactly {"notes": [...]}, each
   * note an object with text and an optional key, as the API takes them.
   */
  function parseNotesJson(text) {
    var data;
    try { data = JSON.parse(text); } catch (e) {
      return { rows: null, problems: [{ index: -1, field: 'json', message: 'The notes JSON does not parse: ' + e.message }] };
    }
    var shape = 'The notes JSON must be {"notes": [{"text": "...", "key": "..."}]}, with an optional key and nothing else.';
    if (!data || typeof data !== 'object' || Array.isArray(data) || Object.keys(data).join(',') !== 'notes' || !Array.isArray(data.notes)) {
      return { rows: null, problems: [{ index: -1, field: 'json', message: shape }] };
    }
    var rows = [];
    for (var i = 0; i < data.notes.length; i++) {
      var note = data.notes[i];
      var names = note && typeof note === 'object' && !Array.isArray(note) ? Object.keys(note) : null;
      if (!names || names.some(function (n) { return n !== 'text' && n !== 'key'; }) || typeof note.text !== 'string'
        || (note.key !== undefined && note.key !== null && typeof note.key !== 'string')) {
        return { rows: null, problems: [{ index: i, field: 'json', message: 'Note ' + (i + 1) + ' in the JSON: ' + shape }] };
      }
      rows.push({ text: note.text, key: typeof note.key === 'string' ? note.key : '' });
    }
    return { rows: rows, problems: [] };
  }

  function checkQuery(query, limit) {
    var problems = [];
    var text = typeof query === 'string' ? query : '';
    if (text.trim() === '') {
      problems.push({ field: 'query', message: 'Write what you are looking for.' });
    } else if (chars(text) > LIMITS.queryChars) {
      problems.push({ field: 'query', message: 'The search has ' + chars(text) + ' characters. The limit is ' + LIMITS.queryChars + '. Shorten it; nothing is cut for you.' });
    }
    if (!isInt(limit) || limit < 1 || limit > LIMITS.resultsMax) {
      problems.push({ field: 'limit', message: 'Ask for 1 to ' + LIMITS.resultsMax + ' results.' });
    }
    return problems;
  }

  /** Retry-After in seconds or as an HTTP date, as a time in ms, or null when it cannot be read. */
  function parseRetryAfter(value, nowMs) {
    if (typeof value !== 'string' || value.trim() === '') { return null; }
    var text = value.trim();
    if (/^\d+$/.test(text)) {
      var seconds = parseInt(text, 10);
      return seconds > 0 && seconds <= 7 * 86400 ? nowMs + seconds * 1000 : null;
    }
    var at = Date.parse(text);
    if (!isFinite(at)) { return null; }
    return at > nowMs ? Math.min(at, nowMs + 7 * 86400 * 1000) : null;
  }

  /** The error text of an answer, or a short fallback with the status: never an HTML page. */
  function errorText(answer) {
    var json = answer.json;
    if (json && typeof json.error === 'string' && json.error.length <= 300) {
      var fix = typeof json.fix === 'string' && json.fix.length <= 400 ? ' ' + json.fix : '';
      return (/[.!?]$/.test(json.error) ? json.error : json.error + '.') + fix;
    }
    return 'The API answered HTTP ' + answer.status + ' in a form this page does not read.';
  }

  function validCreate(data, model) {
    return !!data && data.ok === true && HEX32.test(String(data.collection_id)) && HEX64.test(String(data.read_token))
      && HEX64.test(String(data.write_token)) && data.read_token !== data.write_token && data.model === model
      && isInt(data.created_at_timestamp) && isInt(data.expire_timestamp) && data.expire_timestamp === data.created_at_timestamp + LIFETIME
      && data.notes === 0 && data.notes_added === 0 && isInt(data.notes_max) && data.notes_max > 0;
  }

  function validAdd(data, session, sent) {
    if (!data || data.ok !== true || data.collection_id !== session.id || !Array.isArray(data.added) || data.added.length !== sent.length
      || !isInt(data.notes) || !isInt(data.notes_added) || data.notes_added < sent.length || data.expire_timestamp !== session.expires) {
      return false;
    }
    return data.added.every(function (item, i) {
      var key = sent[i].key === undefined ? null : sent[i].key;
      return item && HEX32.test(String(item.note_id)) && item.key === key;
    });
  }

  function validSearch(data, session, limit) {
    if (!data || data.ok !== true || data.collection_id !== session.id || data.model !== session.model || !Array.isArray(data.results)
      || data.results.length > limit || !isInt(data.notes) || data.expire_timestamp !== session.expires) {
      return false;
    }
    return data.results.every(function (hit) {
      return hit && HEX32.test(String(hit.note_id)) && (hit.key === null || typeof hit.key === 'string') && typeof hit.text === 'string'
        && typeof hit.score === 'number' && isFinite(hit.score);
    });
  }

  /** A score as the API ranks it: four decimals, any sign, never a percentage. */
  function formatScore(score) { return typeof score === 'number' && isFinite(score) ? score.toFixed(4) : String(score); }

  /** An answer for the JSON view with every token value hidden. */
  function hideTokens(value) {
    if (Array.isArray(value)) { return value.map(hideTokens); }
    if (value && typeof value === 'object') {
      var out = {};
      Object.keys(value).forEach(function (name) {
        out[name] = /token/i.test(name) && typeof value[name] === 'string' ? '(hidden: kept in this tab only)' : hideTokens(value[name]);
      });
      return out;
    }
    return value;
  }

  /**
   * One HTTP call to the public API. The answer is read to the end within the
   * time limit; a timeout or a broken connection comes back as kind 'network',
   * never as a failure the API confirmed.
   */
  function call(fetchImpl, method, path, token, body, timeoutMs) {
    var controller = new AbortController();
    var timedOut = false;
    var timer = setTimeout(function () { timedOut = true; controller.abort(); }, timeoutMs || TIMEOUT_MS);
    var init = { method: method, headers: {}, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: controller.signal };
    if (body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    if (token) { init.headers.Authorization = 'Bearer ' + token; }
    var done = function (answer) { clearTimeout(timer); return answer; };
    return Promise.resolve().then(function () {
      return fetchImpl(API + path, init);
    }).then(function (response) {
      return response.text().then(function (text) {
        var json = null;
        try { json = text === '' ? null : JSON.parse(text); } catch (e) { json = null; }
        var type = response.headers && response.headers.get ? String(response.headers.get('Content-Type') || '') : '';
        if (!/^application\/json/i.test(type)) { json = null; }
        return done({ kind: 'http', status: response.status, json: json, retryAfter: response.headers && response.headers.get ? response.headers.get('Retry-After') : null });
      });
    }).catch(function () {
      return done({ kind: 'network', status: 0, json: null, retryAfter: null, timedOut: timedOut });
    });
  }

  /**
   * The test: one collection, its notes and its searches. All state is here,
   * private to this closure; the page reads a copy through state().
   */
  function createController(options) {
    var fetchImpl = options.fetch;
    var now = options.now || function () { return Date.now(); };
    var onChange = options.onChange || function () {};
    var timeoutMs = options.timeoutMs || TIMEOUT_MS;
    var session = null;
    var phase = 'draft';
    var busy = false;
    var retryUntil = 0;
    var message = { text: 'Nothing has been sent. Pick an example or write your own notes, then press Create collection and add notes.', tone: '' };
    var results = null;
    var lastExchange = null;
    var clockOffset = 0;

    function serverNow() { return Math.floor((now() + clockOffset) / 1000); }

    function say(text, tone) { message = { text: text, tone: tone || '' }; }

    function expiredLocally() {
      if (session && serverNow() >= session.expires) {
        phase = 'expired';
        say('The collection expired at ' + new Date(session.expires * 1000).toLocaleString() + ' and the API no longer answers for it. Start a new test to try again.', 'bad');
        return true;
      }
      return false;
    }

    function waitLeft() { return Math.max(0, retryUntil - now()); }

    function noteWait(answer) {
      var until = parseRetryAfter(answer.retryAfter, now());
      if (until !== null) { retryUntil = until; }
      return until;
    }

    function changed() { onChange(state()); }

    function state() {
      return {
        phase: phase, busy: busy, waitMs: waitLeft(), retryUntil: retryUntil, message: { text: message.text, tone: message.tone },
        collection: session ? { id: session.id, model: session.model, expires: session.expires, notes: session.notes, notesAdded: session.notesAdded } : null,
        results: results ? { query: results.query, limit: results.limit, hits: results.hits.slice() } : null,
        exchange: lastExchange
      };
    }

    function record(method, path, body, answer) {
      lastExchange = {
        request: { method: method, url: API + path, body: body === undefined ? null : hideTokens(body) },
        response: answer.kind === 'network' ? { error: answer.timedOut ? 'no answer within ' + Math.round(timeoutMs / 1000) + ' seconds' : 'the connection failed' }
          : { status: answer.status, body: answer.json === null ? '(not JSON)' : hideTokens(answer.json) }
      };
    }

    function begin(nextPhase, text) {
      busy = true;
      phase = nextPhase;
      say(text, '');
      changed();
    }

    function addNotes(notes) {
      begin('adding', 'Adding ' + notes.length + ' note' + (notes.length === 1 ? '' : 's') + ' to the collection...');
      var path = '/' + session.id + '/notes';
      return call(fetchImpl, 'POST', path, session.writeToken, { notes: notes }, timeoutMs).then(function (answer) {
        record('POST', path, { notes: notes }, answer);
        busy = false;
        if (answer.kind === 'http' && answer.status === 201 && validAdd(answer.json, session, notes)) {
          session.notes = answer.json.notes;
          session.notesAdded = answer.json.notes_added;
          answer.json.added.forEach(function (item) { session.noteIds.push(item.note_id); });
          phase = 'ready';
          say('The collection holds ' + session.notes + ' note' + (session.notes === 1 ? '' : 's') + '. Write a search, or pick one of the examples, and press Search.', 'ok');
        } else if (answer.kind === 'http' && [400, 413, 415].indexOf(answer.status) >= 0) {
          phase = 'notes-refused';
          say('The API refused the notes before storing them: ' + errorText(answer) + ' Correct them and press Add the notes again. They go to the same collection.', 'bad');
        } else if (answer.kind === 'http' && answer.status === 429) {
          phase = 'notes-refused';
          var until = noteWait(answer);
          say('The API turned the notes away for now: ' + errorText(answer) + (until !== null ? ' Wait until ' + new Date(until).toLocaleTimeString() + ', then press Add the notes again.' : ''), 'bad');
        } else if (answer.kind === 'http' && (answer.status === 404 || answer.status === 410)) {
          phase = 'expired';
          say('The collection is gone: ' + errorText(answer) + ' Start a new test.', 'bad');
        } else if (answer.kind === 'http' && (answer.status === 401 || answer.status === 403)) {
          phase = 'stopped';
          say('The API did not accept this page\'s access to the collection: ' + errorText(answer) + ' Start a new test.', 'bad');
        } else {
          phase = 'uncertain';
          say((answer.kind === 'network' ? 'No answer came back' : 'The API answered HTTP ' + answer.status) + ', so this page cannot tell whether the notes were stored. It will not send them again. You can still search the collection, or start a new test; a new test makes a new collection, and this one stays on the server until it expires.', 'bad');
        }
        changed();
      });
    }

    function create(rows, model) {
      if (busy) { return Promise.resolve(false); }
      if (waitLeft() > 0) { say('Wait until ' + new Date(retryUntil).toLocaleTimeString() + ' before sending again.', 'bad'); changed(); return Promise.resolve(false); }
      var checked = checkNotes(rows);
      if (checked.problems.length > 0) {
        say(checked.problems[0].message, 'bad');
        changed();
        return Promise.resolve(checked.problems);
      }
      if (phase === 'notes-refused' && session) {
        if (expiredLocally()) { changed(); return Promise.resolve(false); }
        return addNotes(checked.notes);
      }
      if (phase !== 'draft') { return Promise.resolve(false); }
      if (MODELS.indexOf(model) < 0) { say('Pick bge-m3 or qwen3-embedding-4b.', 'bad'); changed(); return Promise.resolve(false); }
      begin('creating', 'Creating the collection with ' + model + '...');
      var sentAt = now();
      return call(fetchImpl, 'POST', '', '', { model: model }, timeoutMs).then(function (answer) {
        record('POST', '', { model: model }, answer);
        if (answer.kind === 'http' && answer.status === 201 && validCreate(answer.json, model)) {
          var data = answer.json;
          clockOffset = data.created_at_timestamp * 1000 - Math.round((sentAt + now()) / 2);
          session = { id: data.collection_id, model: data.model, readToken: data.read_token, writeToken: data.write_token,
            expires: data.expire_timestamp, notes: 0, notesAdded: 0, noteIds: [] };
          return addNotes(checked.notes);
        }
        busy = false;
        if (answer.kind === 'http' && answer.status === 429) {
          phase = 'draft';
          var until = noteWait(answer);
          say('No collection was created: ' + errorText(answer) + (until !== null ? ' Wait until ' + new Date(until).toLocaleTimeString() + '.' : ''), 'bad');
        } else if (answer.kind === 'http' && [400, 413, 415].indexOf(answer.status) >= 0) {
          phase = 'draft';
          say('No collection was created: ' + errorText(answer), 'bad');
        } else {
          phase = 'create-uncertain';
          say((answer.kind === 'network' ? 'No answer came back' : answer.kind === 'http' && answer.status === 201 ? 'The answer did not look like a new collection' : 'The API answered HTTP ' + answer.status)
            + ', so this page cannot tell whether a collection was created. It will not send again on its own. If one was made, it expires within 24 hours and counts toward the 20 new collections per address. Start a new test to try once more.', 'bad');
        }
        changed();
        return true;
      });
    }

    function search(query, limit) {
      if (busy) { return Promise.resolve(false); }
      if (!session || ['ready', 'uncertain'].indexOf(phase) < 0) { return Promise.resolve(false); }
      if (waitLeft() > 0) { say('Wait until ' + new Date(retryUntil).toLocaleTimeString() + ' before searching again.', 'bad'); changed(); return Promise.resolve(false); }
      var problems = checkQuery(query, limit);
      if (problems.length > 0) { say(problems[0].message, 'bad'); changed(); return Promise.resolve(problems); }
      if (expiredLocally()) { results = null; changed(); return Promise.resolve(false); }
      var resumePhase = phase;
      results = null;
      begin('searching', 'Searching ' + session.notes + ' note' + (session.notes === 1 ? '' : 's') + ' with ' + session.model + '...');
      var path = '/' + session.id + '/search';
      var body = { query: query, limit: limit };
      return call(fetchImpl, 'POST', path, session.readToken, body, timeoutMs).then(function (answer) {
        record('POST', path, body, answer);
        busy = false;
        phase = resumePhase;
        if (answer.kind === 'http' && answer.status === 200 && validSearch(answer.json, session, limit)) {
          session.notes = answer.json.notes;
          results = { query: query, limit: limit, hits: answer.json.results.map(function (hit, i) {
            return { rank: i + 1, noteId: hit.note_id, key: hit.key, text: hit.text, score: hit.score };
          }) };
          say(results.hits.length === 0 ? 'The collection holds no notes to rank.' : 'Ranked ' + results.hits.length + ' of ' + session.notes + ' note' + (session.notes === 1 ? '' : 's') + ' for this search.', 'ok');
        } else if (answer.kind === 'http' && (answer.status === 404 || answer.status === 410)) {
          phase = 'expired';
          say('The collection is gone: ' + errorText(answer) + ' Start a new test.', 'bad');
        } else if (answer.kind === 'http' && (answer.status === 401 || answer.status === 403)) {
          phase = 'stopped';
          say('The API did not accept this page\'s access to the collection: ' + errorText(answer) + ' Start a new test.', 'bad');
        } else if (answer.kind === 'http' && answer.status === 429) {
          var until = noteWait(answer);
          say('The search was turned away for now: ' + errorText(answer) + (until !== null ? ' Wait until ' + new Date(until).toLocaleTimeString() + ', then search again.' : ''), 'bad');
        } else if (answer.kind === 'http' && [400, 413, 415].indexOf(answer.status) >= 0) {
          say('The API refused the search: ' + errorText(answer), 'bad');
        } else if (answer.kind === 'http' && answer.status === 200) {
          say('The answer did not look like search results, so none are shown. Nothing was changed by a search; you can try again.', 'bad');
        } else {
          say((answer.kind === 'network' ? 'No answer came back' : 'The search failed: ' + errorText(answer)) + ' No results are shown. A search changes nothing, so you can try again.', 'bad');
        }
        changed();
        return true;
      });
    }

    /** Forgets the collection and its tokens here. Deletes nothing on the server. */
    function reset() {
      if (busy) { return false; }
      session = null;
      phase = 'draft';
      results = null;
      lastExchange = null;
      clockOffset = 0;
      say('A new test. Nothing has been sent. The previous collection, if there was one, stays on the server until it expires.', '');
      changed();
      return true;
    }

    /** Checks the deadline again without any call, for example when the tab gets focus. */
    function recheck() {
      if (phase === 'ready' || phase === 'uncertain' || phase === 'notes-refused') {
        if (expiredLocally()) { results = null; changed(); }
      }
      if (retryUntil && waitLeft() === 0) { retryUntil = 0; changed(); }
    }

    return { state: state, create: create, search: search, reset: reset, recheck: recheck };
  }

  var core = {
    API: API, MODELS: MODELS, LIMITS: LIMITS, EXAMPLES: EXAMPLES,
    chars: chars, bodyBytes: bodyBytes, notesBody: notesBody, checkNotes: checkNotes, parseNotesJson: parseNotesJson, checkQuery: checkQuery,
    parseRetryAfter: parseRetryAfter, errorText: errorText, validCreate: validCreate, validAdd: validAdd, validSearch: validSearch,
    formatScore: formatScore, hideTokens: hideTokens, createController: createController
  };

  if (typeof module === 'object' && module && module.exports) {
    module.exports = core;
  }

  // ---------- the page ----------

  if (typeof document === 'undefined' || !document.getElementById('semantic-try')) {
    return;
  }

  function $(id) { return document.getElementById(id); }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (name) {
      if (name === 'className') { node.className = attrs[name]; } else { node.setAttribute(name, attrs[name]); }
    });
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  var root = $('semantic-try');
  var status = $('semantic-status');
  var errorBox = $('semantic-errors');
  var setsBox = $('semantic-sets');
  var notesBox = $('semantic-notes');
  var addNoteButton = $('semantic-add-note');
  var modelSelect = $('semantic-model');
  var createRequest = $('semantic-create-request');
  var notesRequest = $('semantic-notes-request');
  var jsonBox = $('semantic-json');
  var jsonNote = $('semantic-json-note');
  var rewriteButton = $('semantic-rewrite');
  var createButton = $('semantic-create');
  var collectionLine = $('semantic-collection');
  var examplesBox = $('semantic-examples');
  var queryInput = $('semantic-query');
  var limitSelect = $('semantic-limit');
  var searchButton = $('semantic-search');
  var searchRequest = $('semantic-search-request');
  var resultFor = $('semantic-result-for');
  var resultList = $('semantic-results');
  var rawBox = $('semantic-raw');
  var resetButton = $('semantic-reset');
  var waitTimer = null;
  var noteCounter = 0;
  var jsonEdited = false;
  var current = null;

  function formRows() {
    return Array.prototype.map.call(notesBox.querySelectorAll('.semantic-note'), function (row) {
      return { text: row.querySelector('textarea').value, key: row.querySelector('input').value };
    });
  }

  /** Writes the notes JSON from the form, unless it was edited by hand and force is not set. */
  function writeJson(force) {
    if (jsonEdited && !force) { return; }
    jsonBox.value = JSON.stringify(notesBody(formRows()), null, 2);
    jsonEdited = false;
    jsonNote.textContent = 'Written from the notes above. You can edit it here too.';
    jsonNote.className = 'semantic-help';
  }

  function countLine(row) {
    var count = chars(row.querySelector('textarea').value);
    var line = row.querySelector('.semantic-count');
    line.textContent = count + ' of ' + LIMITS.noteChars + ' characters';
    line.classList.toggle('is-bad', count > LIMITS.noteChars);
  }

  function locked() {
    var s = controller ? controller.state() : null;
    return !!s && (s.busy || (s.collection !== null && s.phase !== 'notes-refused'));
  }

  function renumber() {
    var rows = notesBox.querySelectorAll('.semantic-note');
    Array.prototype.forEach.call(rows, function (row, i) {
      row.querySelector('legend').textContent = 'Note ' + (i + 1);
      row.querySelector('.semantic-remove').textContent = 'Remove note ' + (i + 1);
      row.querySelector('.semantic-remove').disabled = rows.length <= 1 || locked();
    });
    addNoteButton.disabled = rows.length >= LIMITS.formNotes || locked();
  }

  function addRow(note) {
    noteCounter++;
    var id = 'semantic-note-' + noteCounter;
    var row = el('fieldset', { className: 'semantic-note' });
    row.appendChild(el('legend', {}, 'Note'));
    row.appendChild(el('label', { 'for': id + '-text' }, 'Text'));
    var area = el('textarea', { id: id + '-text', rows: '2', spellcheck: 'true', 'aria-describedby': id + '-count' });
    area.value = note.text;
    row.appendChild(area);
    row.appendChild(el('p', { className: 'semantic-count', id: id + '-count' }));
    var keyLine = el('div', { className: 'semantic-key-line' });
    keyLine.appendChild(el('label', { 'for': id + '-key' }, 'Key, optional'));
    var key = el('input', { id: id + '-key', type: 'text', autocomplete: 'off', spellcheck: 'false' });
    key.value = note.key || '';
    keyLine.appendChild(key);
    var remove = el('button', { type: 'button', className: 'semantic-small semantic-remove' }, 'Remove');
    remove.addEventListener('click', function () {
      if (notesBox.querySelectorAll('.semantic-note').length > 1 && !locked()) {
        row.remove();
        renumber();
        writeJson(false);
        render(controller.state());
      }
    });
    keyLine.appendChild(remove);
    row.appendChild(keyLine);
    area.addEventListener('input', function () { countLine(row); writeJson(false); });
    key.addEventListener('input', function () { writeJson(false); });
    notesBox.appendChild(row);
    countLine(row);
    renumber();
    return row;
  }

  function showSearches(searches) {
    examplesBox.textContent = '';
    searches.forEach(function (text) {
      var button = el('button', { type: 'button', className: 'button button-secondary semantic-example' }, text);
      button.addEventListener('click', function () { queryInput.value = text; queryInput.focus(); writeSearchRequest(); });
      examplesBox.appendChild(button);
    });
    examplesBox.hidden = searches.length === 0;
  }

  /** Puts an example's notes and searches in the form, or one empty note for a blank start. */
  function useExample(example) {
    current = example;
    notesBox.textContent = '';
    (example ? example.notes : [{ key: '', text: '' }]).forEach(addRow);
    showSearches(example ? example.searches : []);
    Array.prototype.forEach.call(setsBox.querySelectorAll('button'), function (button) {
      button.setAttribute('aria-pressed', button.getAttribute('data-example') === (example ? example.id : 'blank') ? 'true' : 'false');
    });
    writeJson(true);
  }

  function writeSearchRequest() {
    var s = controller.state();
    var id = s.collection ? s.collection.id : 'COLLECTION_ID';
    var limit = parseInt(limitSelect.value, 10) || 3;
    searchRequest.textContent = 'POST ' + API + '/' + id + '/search\nAuthorization: Bearer READ_TOKEN\nContent-Type: application/json\n\n'
      + JSON.stringify({ query: queryInput.value, limit: limit });
  }

  function writeRequests(s) {
    createRequest.textContent = 'POST ' + API + '\nContent-Type: application/json\n\n' + JSON.stringify({ model: s.collection ? s.collection.model : modelSelect.value });
    notesRequest.textContent = 'POST ' + API + '/' + (s.collection ? s.collection.id : 'COLLECTION_ID') + '/notes\nAuthorization: Bearer WRITE_TOKEN\nContent-Type: application/json';
    writeSearchRequest();
  }

  function showProblems(problems) {
    errorBox.textContent = '';
    if (!Array.isArray(problems) || problems.length === 0) {
      errorBox.hidden = true;
      return;
    }
    errorBox.appendChild(el('p', { className: 'semantic-errors-title' }, 'Correct ' + (problems.length === 1 ? 'this' : 'these') + ' before sending:'));
    var list = el('ul');
    problems.forEach(function (problem) { list.appendChild(el('li', {}, problem.message)); });
    errorBox.appendChild(list);
    errorBox.hidden = false;
    errorBox.focus();
  }

  function render(s) {
    status.textContent = s.message.text;
    status.className = 'try-status' + (s.message.tone ? ' is-' + s.message.tone : '');
    root.setAttribute('aria-busy', s.busy ? 'true' : 'false');
    var hasCollection = s.collection !== null;
    var lockedNow = s.busy || (hasCollection && s.phase !== 'notes-refused');
    Array.prototype.forEach.call(notesBox.querySelectorAll('textarea, input'), function (field) { field.disabled = lockedNow; });
    Array.prototype.forEach.call(setsBox.querySelectorAll('button'), function (button) { button.disabled = lockedNow; });
    jsonBox.readOnly = lockedNow;
    rewriteButton.disabled = lockedNow;
    renumber();
    modelSelect.disabled = s.busy || hasCollection;
    createButton.textContent = s.phase === 'notes-refused' ? 'Add the notes again' : 'Create collection and add notes';
    createButton.disabled = s.busy || s.waitMs > 0 || !(s.phase === 'draft' || s.phase === 'notes-refused');
    var canSearch = hasCollection && (s.phase === 'ready' || s.phase === 'uncertain');
    searchButton.disabled = s.busy || s.waitMs > 0 || !canSearch;
    queryInput.disabled = s.busy || !canSearch;
    limitSelect.disabled = s.busy || !canSearch;
    resetButton.disabled = s.busy;
    if (hasCollection) {
      var expires = new Date(s.collection.expires * 1000);
      collectionLine.textContent = 'Collection ' + s.collection.id.slice(0, 8) + '... with ' + s.collection.model + ', holding ' + s.collection.notes
        + ' note' + (s.collection.notes === 1 ? '' : 's') + '. It expires at ' + expires.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'long' })
        + '. Searches do not extend it.';
      collectionLine.hidden = false;
    } else {
      collectionLine.textContent = '';
      collectionLine.hidden = true;
    }
    writeRequests(s);
    resultList.textContent = '';
    if (s.results) {
      resultFor.textContent = 'Results for the search: ' + s.results.query + ' (' + s.collection.model + ', up to ' + s.results.limit + ')';
      s.results.hits.forEach(function (hit) {
        var item = el('li', { className: 'semantic-hit' });
        var head = el('p', { className: 'semantic-hit-head' });
        head.appendChild(el('span', { className: 'semantic-rank' }, 'Rank ' + hit.rank));
        head.appendChild(el('span', { className: 'semantic-score' }, 'score ' + formatScore(hit.score)));
        head.appendChild(el('span', { className: 'semantic-hit-key' }, hit.key === null ? 'no key' : 'key ' + hit.key));
        item.appendChild(head);
        item.appendChild(el('p', { className: 'semantic-hit-text' }, hit.text));
        resultList.appendChild(item);
      });
    } else {
      resultFor.textContent = s.phase === 'searching' ? 'Searching...' : 'No results yet.';
    }
    rawBox.textContent = s.exchange ? JSON.stringify(s.exchange.response, null, 2) : 'Nothing has been sent yet.';
    clearTimeout(waitTimer);
    if (s.waitMs > 0) {
      // A local timer only: when the wait is over the buttons come back, and nothing is sent.
      waitTimer = setTimeout(function () { controller.recheck(); }, s.waitMs + 250);
    }
  }

  var controller = createController({ fetch: function (url, init) { return window.fetch(url, init); }, onChange: render });

  EXAMPLES.forEach(function (example) {
    var button = el('button', { type: 'button', className: 'button button-secondary', 'data-example': example.id, 'aria-pressed': 'false' }, example.title);
    button.addEventListener('click', function () { if (!locked()) { useExample(example); showProblems(null); render(controller.state()); } });
    setsBox.appendChild(button);
  });
  var blank = el('button', { type: 'button', className: 'button button-secondary', 'data-example': 'blank', 'aria-pressed': 'false' }, 'Start blank');
  blank.addEventListener('click', function () {
    if (!locked()) { useExample(null); showProblems(null); render(controller.state()); notesBox.querySelector('textarea').focus(); }
  });
  setsBox.appendChild(blank);

  for (var n = 1; n <= LIMITS.resultsMax; n++) {
    var option = el('option', { value: String(n) }, String(n));
    if (n === 3) { option.selected = true; }
    limitSelect.appendChild(option);
  }

  addNoteButton.addEventListener('click', function () {
    if (!locked() && notesBox.querySelectorAll('.semantic-note').length < LIMITS.formNotes) {
      addRow({ key: '', text: '' }).querySelector('textarea').focus();
      writeJson(false);
    }
  });

  jsonBox.addEventListener('input', function () {
    jsonEdited = true;
    jsonNote.textContent = 'You edited the JSON. The page sends it as it stands. Changes to the notes above will not overwrite it until you write it again from the notes.';
    jsonNote.className = 'semantic-help is-edited';
  });
  rewriteButton.addEventListener('click', function () { if (!locked()) { writeJson(true); } });

  modelSelect.addEventListener('change', function () { writeRequests(controller.state()); });
  queryInput.addEventListener('input', writeSearchRequest);
  limitSelect.addEventListener('change', writeSearchRequest);

  createButton.addEventListener('click', function () {
    showProblems(null);
    var rows = formRows();
    if (jsonEdited) {
      var parsed = parseNotesJson(jsonBox.value);
      if (parsed.problems.length > 0) { showProblems(parsed.problems); return; }
      rows = parsed.rows;
    }
    controller.create(rows, modelSelect.value).then(function (outcome) {
      if (Array.isArray(outcome)) { showProblems(outcome); }
    });
  });

  function runSearch() {
    showProblems(null);
    controller.search(queryInput.value, parseInt(limitSelect.value, 10)).then(function (outcome) {
      if (Array.isArray(outcome)) { showProblems(outcome); }
    });
  }
  searchButton.addEventListener('click', runSearch);
  queryInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!searchButton.disabled) { runSearch(); }
    }
  });

  resetButton.addEventListener('click', function () {
    var s = controller.state();
    if (s.collection !== null || s.phase === 'create-uncertain') {
      var ok = window.confirm('Start a new test? This page forgets its access to the current collection. The collection is not deleted: '
        + 'it stays on the server until it expires 24 hours after creation. Nothing new is created until you press Create collection and add notes.');
      if (!ok) { return; }
    }
    if (controller.reset()) {
      modelSelect.value = MODELS[0];
      queryInput.value = '';
      useExample(current);
      showProblems(null);
      render(controller.state());
    }
  });

  document.addEventListener('visibilitychange', function () { if (!document.hidden) { controller.recheck(); } });
  window.addEventListener('focus', function () { controller.recheck(); });

  useExample(EXAMPLES[0]);
  render(controller.state());
})();
