/*
 * The handoff demo on /free-tools-for-agents-working-together. Two agents in one page pass a task through
 * Agent Handoff: Agent A creates it and keeps the owner token, Agent B accepts and works with the receiver
 * token, Agent A tries a move from a state the handoff has already left and is refused with 409, and both
 * read the history, which is the receipt. Six requests from the visitor's browser, on the visitor's own
 * daily limits, and nothing is sent until the button is pressed. A 429 or any other refusal stops the run
 * and shows the service's own sentence.
 */
(function () {
  var API = 'https://aisenseapi.com/services/v1/handoff';
  var box = document.querySelector('[data-handoff-demo]');
  if (!box) { return; }
  var button = box.querySelector('.handoff-run');
  var status = box.querySelector('.handoff-status');
  var steps = box.querySelector('.handoff-steps');
  var receipt = box.querySelector('.handoff-receipt');
  var rows = receipt.querySelector('tbody');

  // A token or an ID is shown by its first eight characters only.
  function short(value) {
    return String(value || '').slice(0, 8) + '…';
  }

  function say(message, kind) {
    status.textContent = message;
    status.classList.toggle('is-ok', kind === 'ok');
    status.classList.toggle('is-bad', kind === 'bad');
  }

  function step(who, what, request, code, detail) {
    var li = document.createElement('li');
    var name = document.createElement('strong');
    name.textContent = who;
    li.appendChild(name);
    li.appendChild(document.createTextNode(' ' + what + ' '));
    var line = document.createElement('code');
    line.textContent = request;
    li.appendChild(line);
    li.appendChild(document.createTextNode(', answered '));
    var answer = document.createElement('code');
    answer.textContent = String(code);
    li.appendChild(answer);
    if (detail) { li.appendChild(document.createTextNode(': ' + detail)); }
    steps.appendChild(li);
    steps.hidden = false;
  }

  // A history time as UTC, whether the service gives seconds or an ISO string such as 2026-11-15T17:08:13Z.
  function when(at) {
    if (typeof at === 'number') { return new Date(at * 1000).toISOString().slice(0, 19).replace('T', ' '); }
    return String(at || '-').replace('T', ' ').replace(/Z$/, '');
  }

  async function call(method, path, token, payload) {
    var headers = {};
    if (payload !== undefined) { headers['Content-Type'] = 'application/json'; }
    if (token) { headers.Authorization = 'Bearer ' + token; }
    var response = await fetch(API + path, {
      method: method,
      headers: headers,
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: 'no-store'
    });
    var data = {};
    try { data = await response.json(); } catch (e) { data = {}; }
    return { status: response.status, data: data || {}, retry: response.headers.get('Retry-After') };
  }

  function refused(r) {
    var why = r.data.error || ('HTTP ' + r.status);
    if (r.status === 429) {
      return 'This address has reached a limit: ' + why + (r.retry ? ' Try again in ' + r.retry + ' seconds.' : '');
    }
    return why + (r.data.fix ? ' ' + r.data.fix : '');
  }

  function stop(message, kind) {
    say(message, kind);
    button.disabled = false;
  }

  async function run() {
    button.disabled = true;
    steps.textContent = '';
    steps.hidden = true;
    rows.textContent = '';
    receipt.hidden = true;
    say('Agent A is creating the handoff…');

    var made = await call('POST', '', null, {
      payload: { task: 'Summarize the release notes in three points', words: 120 },
      note: 'Agent A: here is the task'
    });
    if (made.status !== 201) { return stop(refused(made), 'bad'); }
    var id = made.data.handoff_id;
    var owner = made.data.owner_token;
    var receiver = made.data.receiver_token;
    step('Agent A', 'creates the handoff with', 'POST /handoff', made.status,
      'state ' + made.data.state + '; it keeps owner token ' + short(owner) + ' and gives receiver token ' + short(receiver) + ' to Agent B');

    var moves = [
      { who: 'Agent B', token: receiver, to: 'accepted', from: 'offered', nonce: 'b-accept', note: 'Agent B: on it', expect: 200, what: 'accepts it with' },
      { who: 'Agent A', token: owner, to: 'done', from: 'offered', nonce: 'a-early', note: 'Agent A: marking it done', expect: 409, what: 'tries to mark it done from offered with' },
      { who: 'Agent B', token: receiver, to: 'working', from: 'accepted', nonce: 'b-work', note: 'Agent B: working on it', expect: 200, what: 'starts the work with' },
      { who: 'Agent B', token: receiver, to: 'done', from: 'working', nonce: 'b-done', note: 'Agent B: three points delivered', expect: 200, what: 'hands it in with' }
    ];

    for (var i = 0; i < moves.length; i++) {
      var m = moves[i];
      say(m.who + ' sends the next move…');
      var r = await call('POST', '/' + id + '/' + m.to, m.token, { from: m.from, nonce: m.nonce, note: m.note });
      if (r.status !== m.expect) { return stop(refused(r), 'bad'); }
      step(m.who, m.what, 'POST /handoff/' + short(id) + '/' + m.to, r.status,
        r.status === 409 ? 'refused, "' + (r.data.error || 'conflict') + '", and nothing was recorded' : 'now ' + r.data.state + ', version ' + r.data.version);
    }

    say('Agent A is reading the history…');
    var read = await call('GET', '/' + id, owner);
    if (read.status !== 200) { return stop(refused(read), 'bad'); }
    var history = Array.isArray(read.data.history) ? read.data.history : [];
    step('Agent A', 'reads the handoff with', 'GET /handoff/' + short(id), read.status,
      'state ' + read.data.state + ', ended ' + read.data.ended + ', ' + history.length + ' entries in the history');

    history.forEach(function (h) {
      var tr = document.createElement('tr');
      [h.state, h.from || '-', h.by || '-', when(h.at), h.note || ''].forEach(function (value) {
        var td = document.createElement('td');
        td.textContent = String(value);
        tr.appendChild(td);
      });
      rows.appendChild(tr);
    });
    receipt.hidden = false;
    stop('Done. Agent B delivered the task, the wrong move was refused without a trace, and both agents read the same history.', 'ok');
  }

  button.addEventListener('click', function () {
    run().catch(function (e) {
      stop('The request did not reach the service: ' + (e && e.message ? e.message : String(e)), 'bad');
    });
  });
})();
