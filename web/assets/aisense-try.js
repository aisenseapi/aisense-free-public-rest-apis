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
 *   data-try-sample    a file the run button sends when the box has no text field
 *   data-try-chars     present when the status line should count the characters of the answer
 *   data-try-method    GET for the endpoints whose quick start is a GET; POST otherwise
 *
 * A GET box sends no body: an input .try-args, when there is one, holds the arguments that follow the
 * endpoint in the path, separated by /, and each one is percent-encoded on its own.
 *
 * The text in .try-input goes as {"<key>": text} in a JSON body. A select .try-path adds its value to the
 * path, and switching it puts that option's data-sample in the text field while the field still holds a
 * sample. A file dropped on .try-drop, or chosen through it, goes as data-try-file says: the encoders read
 * a raw body byte for byte, the hashes and the QR decoder a multipart upload. A select .try-accept sets the
 * Accept header. An answer of application/octet-stream is shown as text when it is readable UTF-8 and as
 * hex otherwise, with a Save button for the bytes; an image field is drawn in .try-image, with a Save
 * button for the image. The answer area stays hidden until there is one.
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
    var key = card.getAttribute('data-try-key') || 'data';
    var fileMode = card.getAttribute('data-try-file') || 'raw';
    var field = card.getAttribute('data-try-field') || 'file';
    var imageField = card.getAttribute('data-try-image');
    var sampleFile = card.getAttribute('data-try-sample');
    var countChars = card.hasAttribute('data-try-chars');
    var method = (card.getAttribute('data-try-method') || 'POST').toUpperCase();
    var find = function (selector) { return card.querySelector(selector); };
    var input = find('.try-input');
    var args = find('.try-args');
    var path = find('.try-path');
    var accept = find('.try-accept');
    var run = find('.try-run');
    var status = find('.try-status');
    var result = find('.try-result');
    var out = find('.try-out');
    var image = find('.try-image');
    var picture = image ? image.querySelector('img') : null;
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
      if (image) { image.hidden = true; }
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

    // Draws the base64 image of the answer and returns the answer with that field shortened for display.
    function drawn(json) {
      var base64 = json[imageField];
      var binary = atob(base64);
      var bytes = new Uint8Array(binary.length);
      for (var i = 0; i < binary.length; i++) { bytes[i] = binary.charCodeAt(i); }
      picture.src = offer(new Blob([bytes], { type: 'image/' + (json.image_type || 'png') }));
      image.hidden = false;
      var shown = {};
      Object.keys(json).forEach(function (name) { shown[name] = json[name]; });
      shown[imageField] = base64.slice(0, 24) + '... (' + base64.length + ' characters of base64, drawn above)';
      return shown;
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

    function send() {
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
          show('The text is ' + length + ' bytes. The box sends at most ' + limitText(limit) + ', ' + limit + ' bytes.', 'bad');
          return;
        }
        var body = {};
        body[key] = input.value;
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
      } else {
        return;
      }
      if (accept) { options.headers.Accept = accept.value; }
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
        note.textContent = file.name + ' is ' + file.size + ' bytes. The box takes files up to ' + limitText(limit) + ', ' + limit + ' bytes.';
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
