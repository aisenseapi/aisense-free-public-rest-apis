/*
 * The Try box of the endpoint pages. tools/pages/make_try_boxes.py writes the form into each page; this
 * wires it up. The box sends the request of the page's quick start from the visitor's browser, and the
 * card names it in data attributes:
 *
 *   data-try-endpoint  the path under https://aisenseapi.com/services/v1/
 *   data-try-limit     the most bytes the box sends, as text or as a file
 *   data-try-busy      the word the status line shows while the call runs
 *   data-try-key       the JSON field the text goes in, data unless it says otherwise
 *   data-try-file      how a file goes: raw, the request body itself, or multipart, a form field
 *   data-try-field     the name of that form field, file unless it says otherwise
 *   data-try-image     a JSON field of the answer that holds a base64 image, which the box shows
 *   data-try-audio     a JSON field of the answer that holds a base64 WAV, which the box plays, asking for JSON
 *   data-try-download  a JSON field of the answer that holds a base64 file, which the box offers to save, asking for JSON
 *   data-try-sample    a file the run button sends when the box has no text field
 *   data-try-chars     present when the status line should count the characters of the answer
 *   data-try-method    GET for the endpoints whose quick start is a GET; POST otherwise
 *   data-try-captcha   the captcha box: make a challenge at the level chosen, show its picture to click, solve the proof of work in the page and check both once
 *
 * A GET box sends no body: an input .try-args, when there is one, holds the arguments that follow the
 * endpoint in the path, separated by /, and each one is percent-encoded on its own.
 *
 * The text in .try-input goes as {"<key>": text} in a JSON body. A select .try-path adds its value to the
 * path, and switching it puts that option's data-sample in the text field while the field still holds a
 * sample. A select .try-field puts its value in the JSON body under its data-try-name, beside the text.
 * A file dropped on .try-drop, or chosen through it, goes as data-try-file says: the encoders read
 * a raw body byte for byte, the hashes and the QR decoder a multipart upload. A select .try-accept sets the
 * Accept header. An answer of application/octet-stream is shown as text when it is readable UTF-8 and as
 * hex otherwise, with a Save button for the bytes; an image field is drawn in .try-image, with a Save
 * button for the image, and a download field gets a Save button of its own; the JSON shown shortens these
 * base64 fields. The answer area stays hidden until there is one.
 */
(function () {
  var API = 'https://aisenseapi.com/services/v1/';
  var NL = String.fromCharCode(10);

  function size(n) {
    if (n < 1024) { return n + (n === 1 ? ' byte' : ' bytes'); }
    return n < 1048576 ? (n / 1024).toFixed(1) + ' KiB' : (n / 1048576).toFixed(1) + ' MiB';
  }

  function limitText(n) {
    if (n % 1048576 === 0) { return (n / 1048576) + ' MiB'; }
    return n % 1024 === 0 ? (n / 1024) + ' KiB' : n + ' bytes';
  }

  // The limit for a message: 72 bytes, or 1 MiB, 1048576 bytes.
  function sizeText(n) {
    var short = limitText(n);
    return short === n + ' bytes' ? short : short + ', ' + n + ' bytes';
  }

  // The first 64 bytes as hex, 16 to a line after their offset.
  function hex(bytes) {
    var lines = [];
    var shown = Math.min(bytes.length, 64);
    for (var i = 0; i < shown; i += 16) {
      var row = [];
      for (var j = i; j < Math.min(i + 16, shown); j++) {
        row.push(('0' + bytes[j].toString(16)).slice(-2));
      }
      lines.push(('0000000' + i.toString(16)).slice(-8) + '  ' + row.join(' '));
    }
    if (bytes.length > shown) {
      lines.push('(' + (bytes.length - shown) + ' more bytes in the file)');
    }
    return lines.join(NL);
  }

  // The bytes as text, or null when they are not UTF-8 or hold control characters other than tab and line ends.
  function readable(bytes) {
    var text;
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    } catch (error) {
      return null;
    }
    for (var i = 0; i < text.length; i++) {
      var c = text.charCodeAt(i);
      if ((c < 32 && c !== 9 && c !== 10 && c !== 13) || c === 127) { return null; }
    }
    return text;
  }

  function hasFiles(e) {
    var types = e.dataTransfer && e.dataTransfer.types;
    return !!types && Array.prototype.indexOf.call(types, 'Files') !== -1;
  }

  function box(card) {
    var endpoint = card.getAttribute('data-try-endpoint');
    var limit = parseInt(card.getAttribute('data-try-limit') || '1048576', 10);
    var busy = card.getAttribute('data-try-busy') || 'Sending';
    var key = card.getAttribute('data-try-key') || 'data';
    var fileMode = card.getAttribute('data-try-file') || 'raw';
    var field = card.getAttribute('data-try-field') || 'file';
    var imageField = card.getAttribute('data-try-image');
    var audioField = card.getAttribute('data-try-audio');
    var downloadField = card.getAttribute('data-try-download');
    var sampleFile = card.getAttribute('data-try-sample');
    var countChars = card.hasAttribute('data-try-chars');
    var method = (card.getAttribute('data-try-method') || 'POST').toUpperCase();
    var captcha = card.hasAttribute('data-try-captcha');
    var find = function (selector) { return card.querySelector(selector); };
    var input = find('.try-input');
    var args = find('.try-args');
    var path = find('.try-path');
    var fields = card.querySelectorAll('.try-field');
    var accept = find('.try-accept');
    var run = find('.try-run');
    var status = find('.try-status');
    var result = find('.try-result');
    var out = find('.try-out');
    var image = find('.try-image');
    var picture = image ? image.querySelector('img') : null;
    var audio = find('.try-audio');
    var player = audio ? audio.querySelector('audio') : null;
    var saveRow = find('.try-save');
    var save = find('.try-save-link');
    var saveName = save ? save.getAttribute('download') : null;
    var drop = find('.try-drop');
    var picker = find('.try-file');
    var note = drop ? drop.querySelector('small') : null;
    var noteText = note ? note.textContent : '';
    var chosen = null;
    var url = null;
    // The captcha box asks for a level beside its button: normal, hard or harder.
    var captchaLevel = null;
    if (captcha && run) {
      var levelLabel = document.createElement('label');
      levelLabel.className = 'try-captcha-level';
      levelLabel.appendChild(document.createTextNode('Level '));
      captchaLevel = document.createElement('select');
      ['normal', 'hard', 'harder'].forEach(function (name) {
        var option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        captchaLevel.appendChild(option);
      });
      levelLabel.appendChild(captchaLevel);
      run.parentNode.appendChild(levelLabel);
    }

    function show(text, state) {
      status.textContent = text;
      status.className = 'try-status' + (state ? ' is-' + state : '');
    }

    function clear() {
      result.hidden = true;
      out.textContent = '';
      if (image) { image.hidden = true; }
      if (audio) { audio.hidden = true; if (player) { player.removeAttribute('src'); } }
      if (saveRow) { saveRow.hidden = true; }
    }

    function offer(blob) {
      if (url) { URL.revokeObjectURL(url); }
      url = URL.createObjectURL(blob);
      if (saveRow) {
        save.href = url;
        saveRow.hidden = false;
      }
      return url;
    }

    function bytesAnswer(response, line) {
      return response.arrayBuffer().then(function (buffer) {
        var bytes = new Uint8Array(buffer);
        var match = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') || '');
        var name = match ? match[1] : 'decoded_data.bin';
        var text = bytes.length ? readable(bytes) : '';
        show(line + ' - ' + size(bytes.length), 'ok');
        out.textContent = bytes.length === 0 ? '(no bytes)' : (text !== null ? text : hex(bytes));
        result.hidden = false;
        if (saveRow) {
          offer(new Blob([buffer], { type: 'application/octet-stream' }));
          save.setAttribute('download', name);
          save.textContent = 'Save ' + name;
        }
      });
    }

    function decoded(base64) {
      var binary = atob(base64);
      var bytes = new Uint8Array(binary.length);
      for (var i = 0; i < binary.length; i++) { bytes[i] = binary.charCodeAt(i); }
      return bytes;
    }

    // The answer with one base64 field shortened for display, saying where its bytes went.
    function shortened(json, field, where) {
      var shown = {};
      Object.keys(json).forEach(function (name) { shown[name] = json[name]; });
      shown[field] = json[field].slice(0, 24) + '... (' + json[field].length + ' characters of base64, ' + where + ')';
      return shown;
    }

    // The Save button under the answer, with the file name the page gives it.
    function named() {
      if (saveRow) {
        save.setAttribute('download', saveName);
        save.textContent = 'Save ' + saveName;
      }
    }

    // Draws the base64 image of the answer.
    function drawn(json) {
      picture.src = offer(new Blob([decoded(json[imageField])], { type: 'image/' + (json.image_type || 'png') }));
      image.hidden = false;
      return shortened(json, imageField, 'drawn above');
    }

    // Plays the base64 WAV of the answer and offers it for saving.
    function played(json) {
      player.src = offer(new Blob([decoded(json[audioField])], { type: json.mime_type || 'audio/wav' }));
      audio.hidden = false;
      named();
      return shortened(json, audioField, 'playable above');
    }

    // Offers the base64 file of the answer for saving.
    function kept(json) {
      offer(new Blob([decoded(json[downloadField])], { type: json.mime_type || 'application/octet-stream' }));
      named();
      return shortened(json, downloadField, 'saved with the button below');
    }

    function textAnswer(response, line, file) {
      return response.text().then(function (text) {
        var type = response.headers.get('Content-Type') || '';
        var json = null;
        if (type.indexOf('application/json') === 0) {
          try {
            json = JSON.parse(text);
            text = JSON.stringify(json, null, 2);
          } catch (error) {
            json = null;
          }
        }
        if (json && response.ok && imageField && image && typeof json[imageField] === 'string') {
          text = JSON.stringify(drawn(json), null, 2);
        }
        if (json && response.ok && audioField && player && typeof json[audioField] === 'string') {
          text = JSON.stringify(played(json), null, 2);
        }
        if (json && response.ok && downloadField && saveRow && typeof json[downloadField] === 'string') {
          text = JSON.stringify(kept(json), null, 2);
        }
        if (file && response.ok) {
          line += ' - ' + file.name + ', ' + size(file.size) + (countChars ? ' in' : '');
          var keys = json ? Object.keys(json).filter(function (name) { return typeof json[name] === 'string'; }) : [];
          if (countChars && keys.length) { line += ', ' + json[keys[0]].length + ' characters out'; }
        }
        show(line, response.ok ? 'ok' : 'bad');
        out.textContent = text === '' ? '(no body)' : text;
        result.hidden = false;
      });
    }

    // Each argument percent-encoded on its own; : @ and + stay, so an IPv6 address or an offset such as
    // +0200 reads as it is written.
    function segment(text) {
      return encodeURIComponent(text).replace(/%3A/gi, ':').replace(/%40/gi, '@').replace(/%2B/gi, '+');
    }

    function sendGet() {
      var target = endpoint;
      if (args) {
        var parts = args.value.trim().split('/').filter(function (part) { return part !== ''; });
        if (/[?#]/.test(args.value) || parts.some(function (part) { return part === '.' || part === '..'; })) {
          clear();
          show('The arguments go in the path, separated by /, with no ? or #.', 'bad');
          return;
        }
        if (parts.length) { target += '/' + parts.map(segment).join('/'); }
      }
      run.disabled = true;
      clear();
      show(busy);
      fetch(API + target, { method: 'GET' }).then(function (response) {
        var type = response.headers.get('Content-Type') || '';
        return textAnswer(response, 'GET /services/v1/' + target + ' - HTTP ' + response.status + (type ? ' - ' + type : ''), null);
      }).catch(function (error) {
        show('The request failed: ' + error.message, 'bad');
      }).then(function () {
        run.disabled = false;
      });
    }

    // The proof of work a form page runs: the first nonce whose SHA-256 after the salt starts with bits zero bits.
    // Awaiting a digest gives the page no turn, so about every 10 ms the solver hands it one through a
    // MessageChannel, which keeps clicks smooth at the same hash rate. stop() ends it when its challenge is abandoned.
    async function solve(salt, bits, stop) {
      var enc = new TextEncoder();
      var channel = new MessageChannel();
      var waiting = null;
      channel.port1.onmessage = function () { if (waiting) { var next = waiting; waiting = null; next(); } };
      var last = performance.now();
      try {
        for (var nonce = 0; nonce <= Number.MAX_SAFE_INTEGER; nonce++) {
          var d = new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(salt + nonce)));
          var zero = 0;
          for (var i = 0; i < d.length; i++) {
            if (d[i] === 0) { zero += 8; continue; }
            zero += Math.clz32(d[i]) - 24;
            break;
          }
          if (zero >= bits) { return nonce; }
          if ((nonce & 255) === 255 && performance.now() - last >= 10) {
            await new Promise(function (resolve) { waiting = resolve; channel.port2.postMessage(0); });
            last = performance.now();
            if (stop && stop()) { return null; }
          }
        }
        return null;
      } finally {
        channel.port1.close();
        channel.port2.close();
      }
    }

    // How many points a challenge asks for, once it has everything the picture and the solver need at the level asked
    // for: a challenge from before the levels has no level and no count and is normal with three. Anything else is
    // thrown, so a half answer never replaces the picture. 24 bits keeps a visitor's browser from a runaway task.
    function captchaCount(challenge, level) {
      var counts = { normal: 3, hard: 4, harder: 5 };
      var click = challenge && challenge.click;
      var work = challenge && challenge.proof_of_work;
      var answered = challenge && challenge.level !== undefined ? challenge.level : 'normal';
      var count = click && click.count === undefined && level === 'normal' ? 3 : click && click.count;
      if (!click || !work || answered !== level || count !== counts[level] || typeof challenge.id !== 'string' || !challenge.id
          || typeof click.question !== 'string' || !click.question || typeof click.image !== 'string'
          || click.image.indexOf('data:image/png;base64,') !== 0 || click.image.length <= 22 || !(click.width > 0) || !(click.height > 0)
          || typeof work.salt !== 'string' || !work.salt || !(work.bits >= 1 && work.bits <= 24)) {
        throw new Error('the challenge came back incomplete');
      }
      return count;
    }

    // The picture of a captcha challenge, its question and Start over. A click becomes a point in picture pixels,
    // measured inside the border, with a numbered mark where it landed, up to as many as the question asks for.
    function picturePanel(task, clicks, changed, locked, renew) {
      var needed = task.count || 3;
      var panel = document.createElement('div');
      panel.className = 'try-captcha';
      var question = document.createElement('p');
      question.className = 'try-captcha-question';
      question.textContent = task.question;
      var frame = document.createElement('div');
      frame.className = 'try-captcha-picture';
      var img = document.createElement('img');
      img.src = task.image;
      img.width = task.width;
      img.height = task.height;
      img.alt = 'Symbols to click in the order above';
      frame.appendChild(img);
      var again = document.createElement('button');
      again.type = 'button';
      again.className = 'button try-captcha-again';
      again.textContent = 'Start over';
      function marks() {
        Array.prototype.forEach.call(frame.querySelectorAll('.try-captcha-dot'), function (dot) { frame.removeChild(dot); });
        clicks.forEach(function (point, i) {
          var dot = document.createElement('span');
          dot.className = 'try-captcha-dot';
          dot.textContent = String(i + 1);
          dot.style.left = (point[0] / task.width * 100) + '%';
          dot.style.top = (point[1] / task.height * 100) + '%';
          frame.appendChild(dot);
        });
      }
      img.addEventListener('click', function (event) {
        if (clicks.length >= needed || locked() || panel.classList.contains('is-loading')) { return; }
        var box = img.getBoundingClientRect();
        var x = Math.round((event.clientX - box.left - img.clientLeft) / img.clientWidth * task.width);
        var y = Math.round((event.clientY - box.top - img.clientTop) / img.clientHeight * task.height);
        clicks.push([Math.min(task.width - 1, Math.max(0, x)), Math.min(task.height - 1, Math.max(0, y))]);
        marks();
        changed();
      });
      again.addEventListener('click', function () {
        if (panel.classList.contains('is-loading')) { return; }
        renew();
      });
      panel.appendChild(question);
      panel.appendChild(frame);
      panel.appendChild(again);
      return panel;
    }

    // The captcha box: make a challenge at the level chosen, show its picture while the page solves the proof of
    // work, take the clicks the question asks for, then check both once and show every step. A new challenge
    // replaces one still waiting for clicks, and so does a new level while a picture is shown.
    var captchaRun = 0;
    var captchaBox = null;
    if (captchaLevel) {
      captchaLevel.addEventListener('change', function () {
        if (captchaBox && captchaBox.querySelector('img')) { sendCaptcha(true); }
      });
    }
    function sendCaptcha(renewing) {
      var nl = String.fromCharCode(10);
      var lines = [];
      var made = null;
      var nonce = null;
      var took = 0;
      var started = 0;
      var clicks = [];
      var needed = 3;
      var checking = false;
      var mine = ++captchaRun;
      var current = function () { return mine === captchaRun; };
      var level = captchaLevel ? captchaLevel.value : 'normal';
      var making = level === 'normal' ? 'captcha' : 'captcha/' + level;
      run.disabled = true;
      // The level stays as chosen while a picture loads, so the menu always names the level of the picture shown.
      if (captchaLevel) { captchaLevel.disabled = true; }
      clear();
      // Both buttons wait the same way: the picture there is greys under a spinner, and the first time an empty
      // frame of the same size holds it, for at least a second and a half. harder's picture is square.
      if (!captchaBox) {
        captchaBox = document.createElement('div');
        captchaBox.className = 'try-captcha';
        var empty = document.createElement('div');
        empty.className = 'try-captcha-picture try-captcha-empty' + (level === 'harder' ? ' is-square' : '');
        captchaBox.appendChild(empty);
        card.insertBefore(captchaBox, status);
      }
      captchaBox.classList.add('is-loading');
      var wait = document.createElement('span');
      wait.className = 'try-captcha-wait';
      captchaBox.querySelector('.try-captcha-picture').appendChild(wait);
      show(renewing ? 'Getting a new picture' : busy);

      function check() {
        checking = true;
        var written = clicks.map(function (point) { return point[0] + '-' + point[1]; }).join('_');
        var path = 'captcha_verify/' + made.id + '/' + nonce + '/' + written;
        show('Checking');
        fetch(API + path, { method: 'GET' }).then(function (response) {
          return response.text().then(function (text) {
            if (!current()) { return; }
            lines.push('', 'GET /services/v1/' + path + ' - HTTP ' + response.status, text);
            out.textContent = lines.join(nl);
            result.hidden = false;
            var json = null;
            try { json = JSON.parse(text); } catch (e) { json = null; }
            if (!response.ok) {
              show('The check answered HTTP ' + response.status, 'bad');
            } else if (json && json.valid === true) {
              show('Checked once: the clicks and the proof of work are right', 'ok');
            } else if (json && json.reason === 'wrong_clicks') {
              show('Those were not the symbols asked for, in that order. Make a new challenge to try again', 'bad');
            } else {
              show('Checked once: ' + (json && json.reason ? json.reason : 'not valid'), 'bad');
            }
          });
        }).catch(function (error) {
          if (current()) { show('The request failed: ' + error.message, 'bad'); }
        });
      }

      function step() {
        if (!current() || checking) { return; }
        if (nonce === null) {
          show(clicks.length === needed ? 'Finishing the proof of work' : 'Click the symbols in the order asked. The proof of work runs meanwhile');
          return;
        }
        if (clicks.length < needed) {
          show('The proof of work took ' + took + ' ms. Click the symbols in the order asked');
          return;
        }
        check();
      }

      // A fetch that hangs is given up after 15 s, so the spinner does not turn for ever.
      var controller = typeof AbortController === 'function' ? new AbortController() : null;
      var timer = controller ? setTimeout(function () { controller.abort(); }, 15000) : 0;
      Promise.all([
        fetch(API + making, { method: 'GET', signal: controller ? controller.signal : undefined }).then(function (response) {
          if (!response.ok) { throw new Error('GET /services/v1/' + making + ' answered HTTP ' + response.status); }
          return response.json();
        }),
        new Promise(function (resolve) { setTimeout(resolve, 1500); })
      ]).then(function (results) {
        clearTimeout(timer);
        var json = results[0];
        if (!current()) { return null; }
        needed = captchaCount(json, level);
        var shown = JSON.parse(JSON.stringify(json));
        shown.click.image = json.click.image.slice(0, 40) + '... (' + json.click.image.length + ' characters)';
        lines.push('GET /services/v1/' + making + ' - HTTP 200', JSON.stringify(shown, null, 2));
        var panel = picturePanel(json.click, clicks, step, function () { return checking; }, function () { sendCaptcha(true); });
        if (captchaBox) { captchaBox.parentNode.replaceChild(panel, captchaBox); } else { card.insertBefore(panel, status); }
        captchaBox = panel;
        // The run owns a picture only from here: until then a failure takes away the one still shown.
        made = json;
        run.disabled = false;
        if (captchaLevel) { captchaLevel.disabled = false; }
        step();
        started = performance.now();
        return solve(json.proof_of_work.salt, json.proof_of_work.bits, function () { return !current(); });
      }).then(function (found) {
        if (!current() || made === null) { return; }
        if (found === null) {
          show('The proof of work could not finish', 'bad');
          return;
        }
        nonce = found;
        took = Math.round(performance.now() - started);
        lines.push('', 'Solved in this browser in ' + took + ' ms: nonce ' + nonce);
        step();
      }).catch(function (error) {
        clearTimeout(timer);
        if (!current()) { return; }
        show((error && error.name === 'AbortError' ? 'The request took longer than 15 s' : 'The request failed: ' + error.message)
          + '. Make a challenge to try again', 'bad');
        // A run whose picture never came leaves none: the one still shown belongs to a run that is over, so its clicks
        // could not be checked, and the menu may already name another level.
        if (captchaBox && made === null) {
          captchaBox.parentNode.removeChild(captchaBox);
          captchaBox = null;
        } else if (captchaBox) {
          captchaBox.classList.remove('is-loading');
          var spinner = captchaBox.querySelector('.try-captcha-wait');
          if (spinner) { spinner.parentNode.removeChild(spinner); }
        }
      }).then(function () {
        if (current()) {
          run.disabled = false;
          if (captchaLevel) { captchaLevel.disabled = false; }
        }
      });
    }

    function send() {
      if (captcha) {
        sendCaptcha();
        return;
      }
      if (method === 'GET') {
        sendGet();
        return;
      }
      var file = chosen;
      var options = { method: 'POST', headers: {} };
      if (file && fileMode === 'multipart') {
        // The browser writes the multipart Content-Type with its boundary itself.
        options.body = new FormData();
        options.body.append(field, file, file.name);
      } else if (file) {
        options.headers['Content-Type'] = 'application/octet-stream';
        options.body = file;
      } else if (input) {
        var length = new TextEncoder().encode(input.value).length;
        if (length > limit) {
          clear();
          show('The text is ' + length + ' bytes. The box sends at most ' + sizeText(limit) + '.', 'bad');
          return;
        }
        var body = {};
        body[key] = input.value;
        for (var f = 0; f < fields.length; f++) { body[fields[f].getAttribute('data-try-name')] = fields[f].value; }
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
      } else {
        return;
      }
      if (accept) { options.headers.Accept = accept.value; }
      if (audioField || downloadField) { options.headers.Accept = 'application/json'; }
      run.disabled = true;
      clear();
      show(busy + (file ? ' ' + file.name : ''));
      fetch(API + endpoint + (path ? '/' + encodeURIComponent(path.value) : ''), options).then(function (response) {
        var type = response.headers.get('Content-Type') || '';
        var line = 'HTTP ' + response.status + (type ? ' - ' + type : '');
        if (response.ok && type.indexOf('application/octet-stream') === 0) {
          return bytesAnswer(response, line);
        }
        return textAnswer(response, line, file);
      }).catch(function (error) {
        show('The request failed: ' + error.message, 'bad');
      }).then(function () {
        run.disabled = false;
      });
    }

    // A box with no text field sends its sample file, fetched from this site, the way it sends a dropped one.
    function sendSample() {
      var name = sampleFile.split('/').pop();
      run.disabled = true;
      clear();
      show(busy + ' ' + name);
      fetch(sampleFile).then(function (response) {
        if (!response.ok) { throw new Error(name + ' answered HTTP ' + response.status); }
        return response.blob();
      }).then(function (blob) {
        chosen = new File([blob], name, { type: blob.type || 'application/octet-stream' });
        if (note) { note.textContent = noteText; }
        send();
      }).catch(function (error) {
        show('The sample could not be loaded: ' + error.message, 'bad');
        run.disabled = false;
      });
    }

    function take(file) {
      if (!file) { return; }
      if (file.size > limit) {
        drop.classList.add('is-bad');
        note.textContent = file.name + ' is ' + file.size + ' bytes. The box takes files up to ' + sizeText(limit) + '.';
        return;
      }
      chosen = file;
      drop.classList.remove('is-bad');
      note.textContent = file.name + ', ' + size(file.size) + (input ? '. Type in the text box to send text again.' : '.');
      send();
    }

    run.addEventListener('click', function () {
      if (!input && sampleFile) {
        sendSample();
      } else {
        send();
      }
    });

    if (args) {
      args.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          send();
        }
      });
    }

    if (path && input) {
      path.addEventListener('change', function () {
        var samples = Array.prototype.map.call(path.options, function (option) { return option.getAttribute('data-sample'); });
        if (input.value === '' || samples.indexOf(input.value) !== -1) {
          input.value = path.options[path.selectedIndex].getAttribute('data-sample') || '';
        }
        clear();
        show('');
      });
    }

    if (!drop || !picker) { return; }

    if (input) {
      input.addEventListener('input', function () {
        if (chosen) {
          chosen = null;
          note.textContent = noteText;
        }
        drop.classList.remove('is-bad');
      });
    }
    drop.addEventListener('click', function () { picker.click(); });
    drop.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        picker.click();
      }
    });
    picker.addEventListener('change', function () {
      take(picker.files && picker.files[0]);
      picker.value = '';
    });
    [drop, input].filter(Boolean).forEach(function (target) {
      ['dragenter', 'dragover'].forEach(function (name) {
        target.addEventListener(name, function (e) {
          if (!hasFiles(e)) { return; }
          e.preventDefault();
          drop.classList.add('is-over');
        });
      });
      target.addEventListener('dragleave', function () { drop.classList.remove('is-over'); });
      target.addEventListener('drop', function (e) {
        drop.classList.remove('is-over');
        if (!hasFiles(e)) { return; }
        e.preventDefault();
        take(e.dataTransfer.files[0]);
      });
    });
    // A file dropped anywhere else would make the browser open it and leave the page.
    ['dragover', 'drop'].forEach(function (name) {
      window.addEventListener(name, function (e) { if (hasFiles(e)) { e.preventDefault(); } });
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll('.try-card[data-try-endpoint]'), box);
})();
