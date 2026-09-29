/*
 * Shared browser code for the conversion tool pages.
 *
 * Every conversion is one POST to https://aisenseapi.com/services/v1/<name>.
 * The service stores the result in Storage for 24 hours and answers with a
 * link to it; the page then reads the result from that link to show it, and
 * the download button saves the same bytes. Text from the page or from the
 * service is always set with textContent, never as HTML.
 */
(function () {
  'use strict';

  var API = 'https://aisenseapi.com/services/v1/';
  var LIMIT = 262144;
  var PREVIEW = 20000;

  function make(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  function clear(node) {
    while (node.firstChild) { node.removeChild(node.firstChild); }
  }

  function bytes(n) {
    if (n < 1024) { return n + ' bytes'; }
    if (n < 1048576) { return (n / 1024).toFixed(1) + ' KiB'; }
    return (n / 1048576).toFixed(2) + ' MiB';
  }

  /** POST one conversion. Resolves with the Storage answer, rejects with an Error carrying the service's fix. */
  function post(operation, payload) {
    var body = JSON.stringify(payload);
    var size = new Blob([body]).size;
    if (size > LIMIT) {
      var tooBig = new Error('The request is ' + bytes(size) + ', and the limit is 256 KiB.');
      tooBig.fix = 'Send fewer rows or less text in one request.';
      return Promise.reject(tooBig);
    }
    return fetch(API + operation, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body
    }).then(function (response) {
      return response.text().then(function (raw) {
        var data;
        try {
          data = JSON.parse(raw);
        } catch (e) {
          throw new Error('The service answered HTTP ' + response.status + ' without JSON.');
        }
        if (!response.ok) {
          var error = new Error((data && data.error) || ('The service answered HTTP ' + response.status + '.'));
          error.fix = data && data.fix;
          throw error;
        }
        if (!data || typeof data.storage_url !== 'string') {
          throw new Error('The answer carried no storage_url.');
        }
        data.raw = raw;
        return data;
      });
    }, function () {
      throw new Error('Network error. The service could not be reached.');
    });
  }

  /** The stored result as a Blob. */
  function stored(result) {
    return fetch(result.storage_url).then(function (response) {
      if (!response.ok) { throw new Error('The stored result is gone or has expired.'); }
      return response.blob();
    });
  }

  function save(result, button) {
    button.disabled = true;
    stored(result).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var link = make('a');
      link.href = url;
      link.download = result.filename || 'result';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
    }).catch(function (error) {
      alert(error.message);
    }).then(function () {
      button.disabled = false;
    });
  }

  function copy(text, button) {
    var label = button.textContent;
    var done = function () {
      button.textContent = 'Copied';
      setTimeout(function () { button.textContent = label; }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { button.textContent = 'Copy failed'; });
    } else {
      button.textContent = 'Copy failed';
    }
  }

  function showError(box, error) {
    clear(box);
    var node = make('p', 'tool-error', error.message || String(error));
    if (error.fix) { node.appendChild(make('small', '', error.fix)); }
    box.appendChild(node);
  }

  function busy(box, message) {
    clear(box);
    box.appendChild(make('p', 'tool-meta', message));
  }

  /**
   * Show a stored result: its link, size and expiry, the download and copy
   * buttons, and, with options.preview, the first part of the text itself.
   * Resolves with the stored text when a preview was asked for.
   */
  function showStored(box, result, options) {
    options = options || {};
    clear(box);
    if (options.status) {
      box.appendChild(make('p', 'tool-status' + (options.statusClass ? ' ' + options.statusClass : ''), options.status));
    }
    var expires = new Date(result.expire_timestamp * 1000);
    box.appendChild(make('p', 'tool-meta',
      'Stored as ' + result.filename + ', ' + bytes(result.bytes) + ', until ' + expires.toLocaleString() + '. Anyone with the link can open it.'));
    var link = make('code', 'tool-link', result.storage_url);
    box.appendChild(link);

    var actions = make('div', 'tool-actions');
    var download = make('button', 'button button-primary', 'Download ' + result.filename);
    download.type = 'button';
    download.addEventListener('click', function () { save(result, download); });
    var copyLink = make('button', 'button button-secondary', 'Copy link');
    copyLink.type = 'button';
    copyLink.addEventListener('click', function () { copy(result.storage_url, copyLink); });
    actions.appendChild(download);
    actions.appendChild(copyLink);
    box.appendChild(actions);

    if (!options.preview) { return Promise.resolve(null); }

    var pre = make('pre', 'tool-preview', 'Reading the stored result...');
    box.appendChild(pre);
    return stored(result).then(function (blob) {
      return blob.text();
    }).then(function (text) {
      pre.textContent = text.length > PREVIEW
        ? text.slice(0, PREVIEW) + '\n\n[Preview ends here. Download the file for all of it.]'
        : text;
      if (options.copyText) {
        var copyText = make('button', 'button button-secondary', 'Copy text');
        copyText.type = 'button';
        copyText.addEventListener('click', function () { copy(text, copyText); });
        actions.appendChild(copyText);
      }
      return text;
    }).catch(function (error) {
      pre.textContent = error.message;
      return null;
    });
  }

  /** Read a chosen file as text into a textarea. */
  function fileInto(input, textarea) {
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) { return; }
      file.text().then(function (text) {
        textarea.value = text;
        textarea.dispatchEvent(new Event('input'));
      });
      input.value = '';
    });
  }

  /** Comma, semicolon or tab, whichever the first line holds most of. */
  function guessDelimiter(text) {
    var first = String(text).split(/\r?\n/, 1)[0] || '';
    var best = ',';
    var most = -1;
    [',', ';', '\t'].forEach(function (d) {
      var n = first.split(d).length - 1;
      if (n > most) { most = n; best = d; }
    });
    return best;
  }

  /**
   * CSV text to {columns, rows}, for the matching page, which sends rows as
   * JSON. Quoted fields, doubled quotes and line breaks inside quotes are
   * handled; every cell stays text, as on the CSV to JSON endpoint.
   */
  function parseCsv(text, delimiter) {
    var records = [];
    var row = [];
    var cell = '';
    var quoted = false;
    var i = 0;
    text = String(text).replace(/^﻿/, '');
    while (i < text.length) {
      var c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') { cell += '"'; i += 2; continue; }
          quoted = false; i++; continue;
        }
        cell += c; i++; continue;
      }
      if (c === '"' && cell === '') { quoted = true; i++; continue; }
      if (c === delimiter) { row.push(cell); cell = ''; i++; continue; }
      if (c === '\r' && text[i + 1] === '\n') { i++; continue; }
      if (c === '\n') { row.push(cell); records.push(row); row = []; cell = ''; i++; continue; }
      cell += c; i++;
    }
    if (quoted) { throw new Error('A quoted field is never closed.'); }
    if (cell !== '' || row.length) { row.push(cell); records.push(row); }
    var columns = records.shift() || [];
    if (!columns.length || columns.some(function (c) { return c === ''; })) {
      throw new Error('The first line must name every column.');
    }
    var rows = records.map(function (record, n) {
      if (record.length !== columns.length) {
        throw new Error('Line ' + (n + 2) + ' has ' + record.length + ' fields where the header has ' + columns.length + '.');
      }
      var out = {};
      columns.forEach(function (name, k) { out[name] = record[k]; });
      return out;
    });
    return { columns: columns, rows: rows };
  }

  /** A table from text that is either a JSON list of objects or CSV with a header line. */
  function parseTable(text) {
    var trimmed = String(text).trim();
    if (!trimmed) { throw new Error('The table is empty.'); }
    if (trimmed[0] === '[' || trimmed[0] === '{') {
      var data = JSON.parse(trimmed);
      var rows = Array.isArray(data) ? data : data.rows;
      if (!Array.isArray(rows) || rows.some(function (r) { return !r || typeof r !== 'object' || Array.isArray(r); })) {
        throw new Error('JSON must be a list of objects, or an object with rows.');
      }
      var columns = [];
      rows.forEach(function (r) {
        Object.keys(r).forEach(function (k) { if (columns.indexOf(k) === -1) { columns.push(k); } });
      });
      return { columns: columns, rows: rows };
    }
    return parseCsv(trimmed, guessDelimiter(trimmed));
  }

  window.AisenseTools = {
    make: make,
    clear: clear,
    post: post,
    stored: stored,
    showError: showError,
    showStored: showStored,
    busy: busy,
    fileInto: fileInto,
    guessDelimiter: guessDelimiter,
    parseCsv: parseCsv,
    parseTable: parseTable
  };
})();
