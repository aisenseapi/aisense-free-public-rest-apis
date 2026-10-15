/*
 * The Try box of the endpoint pages. tools/pages/make_try_boxes.py writes the form into each page; this
 * wires it up. The box sends the request of the page's quick start from the visitor's browser, and the
 * card names it in data attributes:
 *
 *   data-try-endpoint  the path under https://aisenseapi.com/services/v1/
 *   data-try-limit     the most bytes the box sends, as text or as a file
 *   data-try-busy      the word the status line shows while the call runs
 *   data-try-file      how a file goes: raw, the request body itself, or multipart, a form field named file
 *   data-try-chars     present when the status line should count the characters of the answer
 *
 * The text in .try-input goes as {"data": text} in a JSON body. A file dropped on .try-drop, or chosen
 * through it, goes as data-try-file says: the encoders read a raw body byte for byte, the hashes a
 * multipart upload. A select .try-accept sets the
 * Accept header. An answer of application/octet-stream is shown as text when it is readable UTF-8 and
 * as hex otherwise, with a Save button for the bytes. The answer area stays hidden until there is one.
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
    var fileMode = card.getAttribute('data-try-file') || 'raw';
    var countChars = card.hasAttribute('data-try-chars');
    var find = function (selector) { return card.querySelector(selector); };
    var input = find('.try-input');
    var accept = find('.try-accept');
    var run = find('.try-run');
    var status = find('.try-status');
    var result = find('.try-result');
    var out = find('.try-out');
    var saveRow = find('.try-save');
    var save = find('.try-save-link');
    var drop = find('.try-drop');
    var picker = find('.try-file');
    var note = drop ? drop.querySelector('small') : null;
    var noteText = note ? note.textContent : '';
    var chosen = null;
    var url = null;

    function show(text, state) {
      status.textContent = text;
      status.className = 'try-status' + (state ? ' is-' + state : '');
    }

    function clear() {
      result.hidden = true;
      out.textContent = '';
      if (saveRow) { saveRow.hidden = true; }
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
          if (url) { URL.revokeObjectURL(url); }
          url = URL.createObjectURL(new Blob([buffer], { type: 'application/octet-stream' }));
          save.href = url;
          save.setAttribute('download', name);
          save.textContent = 'Save ' + name;
          saveRow.hidden = false;
        }
      });
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
        if (file && response.ok) {
          line += ' - ' + file.name + ', ' + size(file.size) + (countChars ? ' in' : '');
          var keys = json ? Object.keys(json).filter(function (key) { return typeof json[key] === 'string'; }) : [];
          if (countChars && keys.length) { line += ', ' + json[keys[0]].length + ' characters out'; }
        }
        show(line, response.ok ? 'ok' : 'bad');
        out.textContent = text === '' ? '(no body)' : text;
        result.hidden = false;
      });
    }

    function send() {
      var file = chosen;
      var options = { method: 'POST', headers: {} };
      if (file && fileMode === 'multipart') {
        // The browser writes the multipart Content-Type with its boundary itself.
        options.body = new FormData();
        options.body.append('file', file, file.name);
      } else if (file) {
        options.headers['Content-Type'] = 'application/octet-stream';
        options.body = file;
      } else {
        var length = new TextEncoder().encode(input.value).length;
        if (length > limit) {
          clear();
          show('The text is ' + length + ' bytes. The box sends at most ' + limitText(limit) + ', ' + limit + ' bytes.', 'bad');
          return;
        }
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify({ data: input.value });
      }
      if (accept) { options.headers.Accept = accept.value; }
      run.disabled = true;
      clear();
      show(busy + (file ? ' ' + file.name : ''));
      fetch(API + endpoint, options).then(function (response) {
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

    function take(file) {
      if (!file) { return; }
      if (file.size > limit) {
        drop.classList.add('is-bad');
        note.textContent = file.name + ' is ' + file.size + ' bytes. The box takes files up to ' + limitText(limit) + ', ' + limit + ' bytes.';
        return;
      }
      chosen = file;
      drop.classList.remove('is-bad');
      note.textContent = file.name + ', ' + size(file.size) + '. Type in the text box to send text again.';
      send();
    }

    run.addEventListener('click', send);
    if (!drop || !picker) { return; }

    input.addEventListener('input', function () {
      if (chosen) {
        chosen = null;
        note.textContent = noteText;
      }
      drop.classList.remove('is-bad');
    });
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
    [drop, input].forEach(function (target) {
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
