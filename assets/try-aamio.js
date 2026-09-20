// The live test at https://aisense.no/try-aamio.
//
// Built on the test page the aamio project wrote on 17 September 2026 and laid
// out as three tabs. Everything runs in the visitor's tab: keys are made here
// and never leave it, the tests talk to aamio.at, and the QR code comes from
// the qrcode_encode endpoint of the AisenseAPI, which only ever sees the public
// write address. Text that arrives from anyone else is set as textContent and
// never as HTML.
//
// The proof of work runs on the page itself rather than in a Web Worker.
// aamio 0.5.5 asks its solver for a nonce and expects the answer at once, so a
// solver that answers later cannot take part in send(). While a test runs,
// the buttons and the tabs are locked, and the page is painted first so the
// visitor sees that it is working.

import {
  Aamio,
  AamioError,
  GateStop,
  Keys,
  newId,
  deriveAddress,
  setWorkSolver,
  solveWork,
  sha256hex,
  threadSigningInput,
  expectedSeconds,
  describeSeconds,
} from "aamio";

window.__tryAamioLoaded = true;

const BASE = "https://aamio.at";
const PAGE = "https://aisense.no/try-aamio";
const QR_ENDPOINT = "https://aisenseapi.com/services/v1/qrcode_encode";
const TABS = ["proof-of-work", "round-trip", "another-device"];
const ADDRESS = /^[a-z2-7]{20}$/;
// The work runs on this page, and a tab that stands still for minutes looks
// broken, whatever the inbox allows.
const PAGE_WORK_SECONDS = 60;

const $ = (id) => document.getElementById(id);
const short = (text) => String(text).slice(0, 8) + "...";
const fmt = (ms) => (ms < 10 ? ms.toFixed(1) : Math.round(ms).toLocaleString("en")) + " ms";

function clip(text, limit = 480) {
  const value = String(text ?? "");
  return value.length > limit ? value.slice(0, limit) + ` ... (${value.length - limit} more characters)` : value;
}

function setText(element, text, kind = "") {
  element.textContent = text;
  element.classList.remove("is-ok", "is-bad");
  if (kind) element.classList.add(kind);
}

// A moment for the browser to draw what was just written, before a search
// holds the tab. A tab in the background gets no animation frames, so a timer
// goes on without one.
const paint = () => new Promise((resolve) => {
  let done = false;
  const go = () => {
    if (!done) {
      done = true;
      resolve();
    }
  };
  requestAnimationFrame(() => setTimeout(go, 0));
  setTimeout(go, 50);
});

function describe(error) {
  if (error instanceof GateStop) return `${error.reason} ${error.fix}`;
  if (error instanceof AamioError) {
    const body = error.body && typeof error.body === "object" ? error.body : {};
    return `aamio.at answered ${error.status}: ${body.error ?? error.message}${body.fix ? ". " + body.fix : ""}`;
  }
  return error && error.message ? error.message : String(error);
}

const textOf = (message) => (message.json && typeof message.json.text === "string" ? message.json.text : message.plain ?? message.body ?? "");

// Set once aamio-wasm has loaded, at the end of this file. Until then the run
// buttons are locked, so no test starts without knowing whether it has both
// solvers.
let wasm = null;
let wasmSolver = null;

// ------------------------------------------------------------------- tabs --

const tabButtons = TABS.map((name) => $("tab-" + name));
let busy = false;

function selectTab(name, { focus = false, updateHash = true } = {}) {
  TABS.forEach((tab, index) => {
    const on = tab === name;
    tabButtons[index].setAttribute("aria-selected", String(on));
    tabButtons[index].tabIndex = on ? 0 : -1;
    $(tab).hidden = !on;
  });
  if (focus) tabButtons[TABS.indexOf(name)].focus();
  if (updateHash) history.replaceState(null, "", "#" + name);
}

tabButtons.forEach((button, index) => {
  button.addEventListener("click", () => selectTab(TABS[index]));
  button.addEventListener("keydown", (event) => {
    const moves = { ArrowRight: 1, ArrowLeft: -1 };
    let next = null;
    if (event.key in moves) next = (index + moves[event.key] + TABS.length) % TABS.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = TABS.length - 1;
    if (next === null) return;
    event.preventDefault();
    if (!busy) selectTab(TABS[next], { focus: true });
  });
});

// One test at a time: the solver is a setting of the aamio module, and a
// JavaScript search holds the tab while it runs.
function exclusive(run, onError) {
  return async () => {
    if (busy) return;
    busy = true;
    const locked = [...document.querySelectorAll("[data-exclusive]"), ...tabButtons];
    locked.forEach((element) => (element.disabled = true));
    try {
      await run();
    } catch (error) {
      onError(error);
    } finally {
      setWorkSolver(null);
      busy = false;
      locked.forEach((element) => (element.disabled = false));
    }
  };
}

// aamio-js opens an inbox without conditions; this is the PUT it would send
// with them. The round trip takes signed messages only and requires work. The
// inbox for another device takes anyone and only advises work: aamio's MCP
// endpoint holds no keys and does no work, so an agent with only MCP tools can
// write to that inbox and is refused by the other.
async function openInbox(ttl, { signedOnly, gate }) {
  const id = newId();
  const w = deriveAddress(id);
  const headers = { "Content-Type": "application/json", "X-Read": id, "X-TTL": String(ttl) };
  if (signedOnly) headers["X-Allow"] = "*";
  const response = await recordingFetch(`${BASE}/${w}`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ gate }),
  });
  const answer = await response.json().catch(() => ({}));
  if (response.status !== 201) throw new AamioError(response.status, answer, answer.error);
  return { id, w, expireAt: answer.expire_at, allow: answer.allow || ["*"] };
}

// ----------------------------------------------------------- the recorder --
//
// The round trip shows each request and each answer. The client takes its
// fetch as an option, so the recorder is handed to it rather than patched in.
// The read key is never shown, and signatures and keys are cut short.

let sink = null;

function headerLines(headers) {
  const entries = headers instanceof Headers ? [...headers.entries()] : Object.entries(headers || {});
  return entries.map(([name, value]) => {
    const key = name.toLowerCase();
    let shown = String(value);
    if (key === "x-read") shown = "(the read key, kept in this tab)";
    else if (key === "x-sig" || key === "x-key") shown = shown.slice(0, 16) + "...";
    return `  ${name}: ${shown}`;
  });
}

async function recordingFetch(input, init = {}) {
  const entry = {
    request: [`${String(init.method || "GET").toUpperCase()} ${input}`, ...headerLines(init.headers)],
    body: typeof init.body === "string" ? init.body : "",
    status: null,
    answer: "",
  };
  if (sink) sink.push(entry);
  renderSelected();
  try {
    const response = await fetch(input, init);
    entry.status = response.status;
    entry.answer = await response.clone().text().catch(() => "(the answer could not be read)");
    return response;
  } catch (error) {
    entry.status = 0;
    entry.answer = describe(error);
    throw error;
  } finally {
    renderSelected();
  }
}

function exchangeText(exchanges) {
  if (!exchanges.length) return "Nothing was sent in this step. It ran in this tab.";
  return exchanges.map((entry) => [
    ...entry.request,
    ...(entry.body ? ["  " + clip(entry.body)] : []),
    entry.status === null ? "waiting for the answer..." : entry.status === 0 ? "no answer" : `answered ${entry.status}`,
    ...(entry.answer ? ["  " + clip(entry.answer)] : []),
  ].join("\n")).join("\n\n");
}

// ---------------------------------------------------------- 1. proof of work --

function showBar(which, ms, longest) {
  $(`work-bar-${which}`).style.width = Math.max(2, Math.round((ms / longest) * 100)) + "%";
  $(`work-ms-${which}`).textContent = fmt(ms);
}

$("work-run").addEventListener("click", exclusive(async () => {
  const bits = Number($("work-bits").value);
  const note = $("work-note");
  const log = $("work-log");
  for (const which of ["js", "wasm"]) {
    $(`work-bar-${which}`).style.width = "0";
    $(`work-ms-${which}`).textContent = "-";
  }
  const w = deriveAddress(newId());
  const key = Keys.generate().public;
  const body = JSON.stringify({ test: "proof of work", bits, at: Date.now() });
  const sha = sha256hex(body);
  const lines = [
    `address  ${w}`,
    `key      ${key.slice(0, 16)}...`,
    `body     sha256 ${sha.slice(0, 16)}...`,
    `bits     ${bits}`,
    "",
  ];
  log.textContent = lines.join("\n");
  setText(note, `Searching for ${bits} zero bits in JavaScript...`);
  await paint();

  setWorkSolver(null);
  let started = performance.now();
  const fromJs = String(solveWork(w, key, body, bits));
  const jsMs = performance.now() - started;
  const tries = (Number(fromJs) + 1).toLocaleString("en");
  lines.push(`JavaScript, aamio         nonce ${fromJs.padEnd(9)} ${fmt(jsMs)}`);
  log.textContent = lines.join("\n");
  showBar("js", jsMs, jsMs);

  if (!wasm) {
    setText(note, `Found after ${tries} tries. aamio-wasm did not load, so there is nothing to compare with.`);
    return;
  }

  setText(note, "Searching again in WebAssembly...");
  await paint();
  started = performance.now();
  const fromWasm = String(wasm.solvePow(w, key, sha, bits));
  const wasmMs = performance.now() - started;
  lines.push(`WebAssembly, aamio-wasm   nonce ${fromWasm.padEnd(9)} ${fmt(wasmMs)}`, "", `tries    ${tries}`);
  log.textContent = lines.join("\n");
  const longest = Math.max(jsMs, wasmMs);
  showBar("js", jsMs, longest);
  showBar("wasm", wasmMs, longest);

  if (fromWasm === fromJs) {
    const times = (jsMs / Math.max(wasmMs, 0.1)).toFixed(1);
    setText(note, `The same nonce from both, after ${tries} tries. WebAssembly was ${times} times faster in this browser.`, "is-ok");
  } else {
    setText(note, `The two found different nonces, ${fromJs} and ${fromWasm}. That is a bug in one of them.`, "is-bad");
  }
}, (error) => setText($("work-note"), "Stopped. " + describe(error), "is-bad")));

// ------------------------------------------------------------- 2. round trip --

let selectedStep = null;
let currentStep = null;

function renderSelected() {
  if (!selectedStep) return;
  const text = exchangeText(selectedStep.exchanges);
  $("trip-log").textContent = selectedStep.note ? `${text}\n\n${selectedStep.note}` : text;
}

function selectStep(step) {
  document.querySelectorAll("#trip-steps .try-step").forEach((button) => button.setAttribute("aria-pressed", "false"));
  step.button.setAttribute("aria-pressed", "true");
  selectedStep = step;
  renderSelected();
}

function addStep(label) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "try-step";
  const mark = document.createElement("span");
  mark.className = "try-mark is-running";
  mark.setAttribute("aria-hidden", "true");
  const text = document.createElement("span");
  text.className = "try-step-label";
  text.textContent = label;
  const badge = document.createElement("span");
  badge.className = "try-badge";
  badge.hidden = true;
  const time = document.createElement("span");
  time.className = "try-step-time";
  const state = document.createElement("span");
  state.className = "visually-hidden";
  state.textContent = ", running";
  button.append(mark, text, badge, time, state);
  item.append(button);
  $("trip-steps").append(item);

  const step = {
    exchanges: [],
    note: "",
    button,
    finish(outcome, { badgeText = "", ms = null } = {}) {
      mark.className = "try-mark " + (outcome === "bad" ? "is-bad" : "is-ok");
      state.textContent = outcome === "bad" ? ", failed" : ", passed";
      if (badgeText) {
        badge.textContent = badgeText;
        badge.className = "try-badge" + (outcome === "bad" ? " is-bad" : outcome === "expected" ? " is-expected" : "");
        badge.hidden = false;
      }
      if (ms !== null) time.textContent = fmt(ms);
      renderSelected();
    },
  };
  button.addEventListener("click", () => selectStep(step));
  sink = step.exchanges;
  currentStep = step;
  selectStep(step);
  return step;
}

$("trip-run").addEventListener("click", exclusive(async () => {
  $("trip-steps").replaceChildren();
  selectedStep = null;
  currentStep = null;
  $("trip-log").textContent = "";

  const holder = new Aamio({ keys: Keys.generate(), fetch: recordingFetch });
  const writer = new Aamio({ keys: Keys.generate(), fetch: recordingFetch });

  let step = addStep("Two keys made in this tab");
  step.note = `The inbox holder signs as ${holder.keys.public}\nThe writer signs as ${writer.keys.public}\nBoth secret keys stay in this tab.`;
  step.finish("ok", { badgeText: `${short(holder.keys.public)} and ${short(writer.keys.public)}` });

  step = addStep("Inbox opened for two minutes, signed messages only, 16 bits of work");
  let started = performance.now();
  const inbox = await openInbox(120, { signedOnly: true, gate: { require: { pow: { bits: 16 } } } });
  step.note = `The write address is ${inbox.w}.`;
  step.finish("ok", { badgeText: "201", ms: performance.now() - started });

  step = addStep("Signed, but without the work");
  const bare = "signed, but no work";
  started = performance.now();
  const refused = await recordingFetch(`${BASE}/${inbox.w}`, {
    method: "POST",
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Key": writer.keys.public,
      "X-Sig": writer.keys.sign(threadSigningInput(inbox.w, bare)),
    },
    body: bare,
  });
  const refusedAsExpected = refused.status === 428;
  step.note = refusedAsExpected ? "aamio.at refused the write because the inbox asks for work. That is the point of this step." : "aamio.at should have answered 428 here.";
  step.finish(refusedAsExpected ? "expected" : "bad", {
    badgeText: refusedAsExpected ? "428, as expected" : `${refused.status}, expected 428`,
    ms: performance.now() - started,
  });

  let written = 0;
  for (const [name, solver] of [["JavaScript", null], ["WebAssembly", wasmSolver]]) {
    step = addStep(`Written with the work done in ${name}`);
    if (name === "WebAssembly" && !solver) {
      step.note = "aamio-wasm did not load in this browser, so this write is skipped.";
      step.finish("bad", { badgeText: "skipped" });
      continue;
    }
    await paint();
    setWorkSolver(solver);
    started = performance.now();
    const sent = await writer.send(inbox.w, { text: `sealed, with the work done in ${name}` }, { encryptTo: holder.keys.public });
    const took = performance.now() - started;
    setWorkSolver(null);
    written++;
    const met = sent.met?.pow ?? 0;
    const good = Boolean(sent.verified && sent.sealed && met >= 16);
    step.note = `aamio.at checked it on its own side: verified ${sent.verified}, sealed ${sent.sealed}, met.pow ${met}. The time includes the network.`;
    step.finish(good ? "ok" : "bad", {
      badgeText: [sent.verified ? "verified" : "not verified", sent.sealed ? "sealed" : "not sealed", `pow ${met}`].join(", "),
      ms: took,
    });
  }

  step = addStep("Read back by the holder and opened");
  started = performance.now();
  const read = await holder.read(inbox);
  const opened = read.messages.map((message) => ({ message, text: textOf(message) }));
  const allGood = opened.length === written
    && opened.every(({ message, text }) => message.verified && message.from === writer.keys.public && message.encrypted && text);
  step.note = opened
    .map(({ message, text }) => `message ${message.seq}: from the writer ${message.from === writer.keys.public}, verified ${message.verified}, opened "${clip(text, 120)}"`)
    .join("\n");
  step.finish(allGood ? "ok" : "bad", { badgeText: `${opened.length} of ${written} opened`, ms: performance.now() - started });

  step = addStep("Receipt root recomputed in this tab");
  started = performance.now();
  const receipt = await holder.receipt(inbox);
  step.note = `aamio.at reports the root ${receipt.receipt.root}\nthis tab computed    ${receipt.root}\nover ${receipt.receipt.count} messages`;
  step.finish(receipt.matches ? "ok" : "bad", {
    badgeText: receipt.matches ? "matches aamio.at" : "does not match",
    ms: performance.now() - started,
  });

  step = addStep("Inbox closed");
  started = performance.now();
  await holder.close(inbox);
  step.note = "aamio.at keeps nothing of this inbox now. The receipt is the only trace, and it is in this tab.";
  step.finish("ok", { ms: performance.now() - started });
  sink = null;
}, (error) => {
  if (currentStep) {
    currentStep.note = "Stopped. " + describe(error);
    currentStep.finish("bad", { badgeText: "stopped" });
  } else {
    $("trip-log").textContent = "Stopped. " + describe(error);
  }
  sink = null;
}));

// ---------------------------------------------------- 3. another device: receive --

let mine = null;
let countdown = null;

function startCountdown(expireAt) {
  clearInterval(countdown);
  const tick = () => {
    const left = Math.max(0, Math.round(expireAt - Date.now() / 1000));
    $("recv-left").textContent = left > 0 ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")} left` : "expired";
    if (left === 0) clearInterval(countdown);
  };
  tick();
  countdown = setInterval(tick, 1000);
}

async function drawQr(w) {
  const image = $("recv-qr");
  const note = $("recv-qr-note");
  image.hidden = true;
  note.textContent = "Making a QR code...";
  try {
    const response = await fetch(QR_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload: `${PAGE}#another-device&to=${w}` }),
    });
    const answer = await response.json();
    if (!response.ok || typeof answer.qrcode_image !== "string" || !/^[A-Za-z0-9+/]+={0,2}$/.test(answer.qrcode_image)) {
      throw new Error("no image");
    }
    if (!mine || mine.inbox.w !== w) return;
    image.src = "data:image/png;base64," + answer.qrcode_image;
    image.hidden = false;
    note.textContent = "Scan it with a phone. This page opens there with the address filled in.";
  } catch {
    if (mine && mine.inbox.w === w) note.textContent = "The QR code could not be made just now. Copy the address instead.";
  }
}

function messageItem(message) {
  const item = document.createElement("li");
  const meta = document.createElement("div");
  meta.className = "try-message-meta";
  const who = document.createElement("span");
  const when = message.at ? new Date(message.at * 1000).toLocaleTimeString() : "now";
  who.textContent = `${when}, from ${message.from ? short(message.from) : "an unsigned writer"}`;
  const badge = document.createElement("span");
  const pow = `pow ${message.met?.pow ?? 0}`;
  if (!message.from) {
    badge.className = "try-badge is-expected";
    badge.textContent = `unsigned, ${pow}`;
  } else if (message.verified) {
    badge.className = "try-badge";
    badge.textContent = `verified, ${pow}`;
  } else {
    badge.className = "try-badge is-bad";
    badge.textContent = `signature not verified, ${pow}`;
  }
  meta.append(who, badge);
  const text = document.createElement("p");
  text.className = "try-message-text";
  text.textContent = clip(textOf(message), 280);
  item.append(meta, text);
  return item;
}

async function listenTo(session) {
  const list = $("recv-out");
  try {
    for await (const message of session.client.listen(session.inbox, { wait: 25, signal: session.stop.signal })) {
      if (mine !== session) return;
      list.prepend(messageItem(message));
      const count = list.children.length;
      setText($("recv-state"), `${count} ${count === 1 ? "message has" : "messages have"} arrived. The newest is on top.`);
    }
  } catch (error) {
    if (session.stop.signal.aborted || mine !== session) return;
    const expired = error instanceof AamioError && error.status === 410;
    setText($("recv-state"), expired ? "The inbox has expired. Open a new one to go on." : "Stopped listening. " + describe(error), expired ? "" : "is-bad");
  }
}

$("recv-open").addEventListener("click", exclusive(async () => {
  if (mine) {
    mine.stop.abort();
    mine.client.close(mine.inbox).catch(() => {});
    mine = null;
  }
  clearInterval(countdown);
  $("recv-out").replaceChildren();
  const client = new Aamio({ keys: Keys.generate() });
  const inbox = await openInbox(600, { signedOnly: false, gate: { advise: { pow: { bits: 16 } } } });
  mine = { client, inbox, stop: new AbortController() };
  $("recv-w").textContent = inbox.w;
  $("recv-box").hidden = false;
  $("recv-open").textContent = "Open a new inbox";
  setText($("recv-state"), `Waiting for messages. Anyone with the address can write, and 16 bits of work are asked for but not required. This tab signs with the key ${short(client.keys.public)}`);
  startCountdown(inbox.expireAt);
  renderCode();
  drawQr(inbox.w);
  listenTo(mine);
}, (error) => setText($("recv-state"), "Stopped. " + describe(error), "is-bad")));

$("recv-copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("recv-w").textContent);
    $("recv-copy").textContent = "Copied";
  } catch {
    $("recv-copy").textContent = "Select it and copy";
  }
  setTimeout(() => ($("recv-copy").textContent = "Copy address"), 1500);
});

// ------------------------------------------------------ 3. another device: send --

$("send-to").addEventListener("input", () => {
  if ($("send-out").classList.contains("is-bad")) setText($("send-out"), "");
});

$("send-go").addEventListener("click", exclusive(async () => {
  const out = $("send-out");
  const to = $("send-to").value.trim().toLowerCase();
  if (!ADDRESS.test(to)) {
    setText(out, "A write address is 20 characters of a to z and 2 to 7.", "is-bad");
    $("send-to").focus();
    return;
  }
  const client = mine ? mine.client : new Aamio({ keys: Keys.generate() });
  const useWasm = $("send-wasm").checked && Boolean(wasmSolver);
  const gate = await client.gate(to);
  const bits = gate?.require?.pow?.bits ?? gate?.advise?.pow?.bits ?? 0;
  const body = { text: $("send-text").value || "hello" };
  if (mine) body.reply_to = mine.inbox.w;
  setText(out, bits ? `The inbox asks for ${bits} bits of work. Working in ${useWasm ? "WebAssembly" : "JavaScript"}...` : "Sending...");
  await paint();
  setWorkSolver(useWasm ? wasmSolver : null);
  const required = gate?.require?.pow?.bits ?? 0;
  if (required > 16 && expectedSeconds(required) > PAGE_WORK_SECONDS) {
    setText(out, `The inbox requires ${required} bits of work, about ${describeSeconds(expectedSeconds(required))} in ${useWasm ? "WebAssembly" : "JavaScript"} on this device, and this page stops at a minute. Nothing was sent.${useWasm ? "" : " With WebAssembly on, the same work goes about eighteen times faster."}`, "is-bad");
    return;
  }
  const started = performance.now();
  const sent = await client.send(to, body);
  const took = performance.now() - started;
  const work = bits
    ? `It asked for ${bits} bits, the work was done in ${useWasm ? "WebAssembly" : "JavaScript"}, and aamio.at counted pow ${sent.met?.pow ?? 0}.`
    : "It asks for no work.";
  setText(out, `Delivered as message ${sent.seq}, signed as ${short(client.keys.public)}, ${fmt(took)} in all. ${work}${mine ? " It carries your inbox as reply_to." : ""}`, "is-ok");
}, (error) => setText($("send-out"), "Stopped. " + describe(error), "is-bad")));

// ---------------------------------------------------- 3. from your own code --

const CODE = {
  agent: (w) => [
    "# Any MCP client that takes a remote server. No account, no API key:",
    "https://aamio.at/mcp",
    "",
    "# In Claude Code:",
    "claude mcp add --transport http aamio https://aamio.at/mcp",
    "",
    "# Then ask the agent:",
    `Use the aamio_send tool to send "hello from an agent" to the aamio address ${w}.`,
    "",
    "# The message arrives above as unsigned, pow 0. aamio's MCP endpoint holds no",
    "# keys and does no work, so an agent with only MCP tools can write to an inbox",
    "# that advises work, like this one, and is refused by one that requires it.",
  ].join("\n"),
  node: (w) => [
    'import { Aamio, Keys } from "aamio";',
    "",
    "const me = new Aamio({ keys: Keys.generate() });",
    `const sent = await me.send("${w}", { text: "hello from Node" });`,
    "console.log(sent.met); // { pow: 16 }, the work was done before sending",
  ].join("\n"),
  php: (w) => [
    "use Aamio\\Client;",
    "use Aamio\\Keys;",
    "",
    "$client = new Client('https://aamio.at', Keys::generate());",
    `$sent = $client->send('${w}', ['text' => 'hello from PHP'], true);`,
    "// $sent['body']['met']['pow'] is 16, the work was done in PHP before sending",
  ].join("\n"),
  curl: (w) => [
    `curl -X POST https://aamio.at/${w} \\`,
    "  -H 'Content-Type: text/plain' \\",
    "  -d 'hello from curl'",
    "",
    "# Unsigned and without work. This inbox asks for work but refuses no one,",
    "# so the message arrives and shows as unsigned, pow 0.",
  ].join("\n"),
  install: () => [
    "npm install aamio                        # JavaScript",
    "pip install aamio                        # Python",
    "composer require aisenseapi/aamio        # PHP 8.1",
    "go get github.com/aisenseapi/aamio-go    # Go 1.22",
    "cargo add aamio                          # Rust",
    "at.aamio:aamio                           # Maven Central: Java, Kotlin, Scala",
  ].join("\n"),
};
let codeChoice = "agent";

function renderCode() {
  $("code-out").textContent = CODE[codeChoice](mine ? mine.inbox.w : "<address>");
  document.querySelectorAll("#code-tabs button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.code === codeChoice));
  });
}

document.querySelectorAll("#code-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    codeChoice = button.dataset.code;
    renderCode();
  });
});
renderCode();

// ------------------------------------------------------------------ start --
//
// #round-trip or #another-device opens that tab. The QR code links to
// #another-device&to=<address>, which fills in the send form. The fragment
// never leaves the browser.

function readHash() {
  const parts = location.hash.slice(1).split("&");
  const tab = TABS.includes(parts[0]) ? parts[0] : null;
  const found = parts.map((part) => /^to=([a-z2-7]{20})$/.exec(part)).find(Boolean);
  return { tab, to: found ? found[1] : null };
}

function followHash({ scroll }) {
  const { tab, to } = readHash();
  if (!tab && !to) return;
  if (!busy) selectTab(to ? "another-device" : tab, { updateHash: false });
  if (to) {
    $("send-to").value = to;
    setText($("send-out"), "The address came from the link. Press Send to write to it.");
  }
  if (scroll) $("try-tabs").scrollIntoView({ block: "start" });
}

// On arrival, and when a link on the page or the back button changes the
// fragment without loading the page again.
followHash({ scroll: true });
window.addEventListener("hashchange", () => followHash({ scroll: true }));

// ------------------------------------------------------------ WebAssembly --

const runButtons = [...document.querySelectorAll("[data-exclusive]")];
runButtons.forEach((button) => (button.disabled = true));
try {
  wasm = await import("aamio-wasm");
  wasmSolver = { thread: wasm.solvePow, board: wasm.solveBoardPow };
  setText($("try-status"), `aamio-wasm ${wasm.version()} is loaded, so both solvers run.`, "is-ok");
} catch (error) {
  setText($("try-status"), `aamio-wasm did not load in this browser, so only the JavaScript solver runs: ${describe(error)}`, "is-bad");
  $("send-wasm").checked = false;
  $("send-wasm").disabled = true;
} finally {
  runButtons.forEach((button) => (button.disabled = false));
}
