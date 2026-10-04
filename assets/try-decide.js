/*
 * Try Decide: build a /decide request from a form in plain words, see and edit
 * the JSON it makes, send it, and read the answer in plain words and as JSON.
 *
 * Two forms. Rules: facts, one question and weighted rules, answered by the
 * rule engine. Clef: a situation in words and a question with what each answer
 * means, answered by the Clef model. Everything a visitor types is put on the
 * page as text, never as markup. The request goes
 * from this tab straight to the free API; this page stores nothing.
 */
(function () {
  'use strict';

  var API = 'https://aisenseapi.com/services/v1/decide';

  var NUMBER_OPS = [['gt', 'is more than'], ['gte', 'is at least'], ['lt', 'is less than'], ['lte', 'is at most'], ['eq', 'is'], ['ne', 'is not']];
  var TEXT_OPS = [['contains', 'contains'], ['eq', 'is'], ['ne', 'is not'], ['prefix', 'starts with']];
  var YESNO_OPS = [['yes', 'is yes'], ['no', 'is no']];
  var WEIGHTS = [[3, '+3, strongly for'], [2, '+2, for'], [1, '+1, a little for'], [-1, '-1, a little against'], [-2, '-2, against'], [-3, '-3, strongly against']];
  var CHOICE_WEIGHTS = [[3, '+3, strongly for'], [2, '+2, for'], [1, '+1, a little for'], [-1, '-1, a little against'], [-2, '-2, against']];

  var RULE_EXAMPLES = [
    {
      id: 'refund', title: 'Refund the customer now?',
      question: { name: 'refund_now', type: 'yes_no', bias: -2 },
      facts: [['amount', 'number', '30'], ['tier', 'text', 'gold'], ['order_age_days', 'number', '3'], ['has_photo', 'yesno', 'yes']],
      rules: [['amount', 'lte', '50', 2], ['tier', 'eq', 'gold', 1], ['order_age_days', 'lte', '14', 1], ['has_photo', 'yes', '', 1]]
    },
    {
      id: 'umbrella', title: 'Bring an umbrella?',
      question: { name: 'bring_umbrella', type: 'yes_no', bias: -1 },
      facts: [['rain_chance', 'number', '70'], ['wind', 'number', '4'], ['minutes_outside', 'number', '20']],
      rules: [['rain_chance', 'gte', '60', 3], ['rain_chance', 'gte', '30', 1], ['wind', 'gt', '10', -2], ['minutes_outside', 'gte', '15', 1]]
    },
    {
      id: 'team', title: 'Which team gets this message?',
      question: { name: 'team', type: 'choice' },
      facts: [['subject', 'text', 'I was charged twice for my order']],
      groups: [
        ['billing', [['subject', 'contains', 'charged', 2], ['subject', 'contains', 'invoice', 2], ['subject', 'contains', 'refund', 1]]],
        ['technical', [['subject', 'contains', 'error', 2], ['subject', 'contains', 'down', 2]]],
        ['shipping', [['subject', 'contains', 'tracking', 2], ['subject', 'contains', 'delivery', 1]]]
      ]
    },
    {
      id: 'alert', title: 'How serious is this alert?',
      question: { name: 'severity', type: 'scale' },
      facts: [['service', 'text', 'payments'], ['error_rate', 'number', '0.12'], ['customers_affected', 'number', '340']],
      groups: [
        ['low', []],
        ['normal', [['error_rate', 'lt', '0.05', 2]]],
        ['high', [['error_rate', 'gte', '0.05', 2], ['service', 'eq', 'payments', 1]]],
        ['urgent', [['error_rate', 'gte', '0.1', 2], ['customers_affected', 'gte', '100', 2], ['service', 'eq', 'payments', 1]]]
      ]
    }
  ];

  var CLEF_EXAMPLES = [
    {
      id: 'urgent', title: 'Is this urgent?',
      message: 'The production API returns HTTP 500 and blocks checkout for every customer.',
      question: { name: 'urgent', type: 'noul', instructions: 'Does this need urgent attention?' },
      yes: 'An active failure that blocks customers or the business.', no: 'It can wait for normal working hours.'
    },
    {
      id: 'team', title: 'Which team should take it?',
      message: 'I was charged twice, and now the app shows an error when I open my orders.',
      question: { name: 'team', type: 'choice', instructions: 'Which team should handle this first?' },
      choices: [['technical', 'Outages, errors and things that do not work.'], ['billing', 'Payments, charges and refunds.'], ['sales', 'New purchases and prices.'], ['other', 'Anything else.']]
    },
    {
      id: 'priority', title: 'Rate the priority',
      message: 'A customer says the invoice PDF has the wrong address. Their accountant needs it next week.',
      question: { name: 'priority', type: 'score', instructions: 'How urgent is this request?' },
      levels: ['Routine', 'Important', 'Urgent', 'Critical']
    }
  ];

  var mode = 'rules';
  var rules = blankRules();
  var clef = blankClef();
  var jsonEdited = false;

  var root = document.querySelector('.try-decide');
  if (!root) { return; }
  var jsonBox = document.getElementById('decide-json');
  var jsonNote = document.getElementById('decide-json-note');
  var sendButton = document.getElementById('decide-send');
  var plain = document.getElementById('decide-plain');
  var responseBox = document.getElementById('decide-response');

  // ---------- small helpers ----------

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === 'text') { node.textContent = attrs[key]; }
      else if (key === 'class') { node.className = attrs[key]; }
      else if (attrs[key] !== null && attrs[key] !== undefined) { node.setAttribute(key, attrs[key]); }
    });
    (children || []).forEach(function (child) { if (child) { node.appendChild(child); } });
    return node;
  }

  function select(options, value, attrs) {
    var node = el('select', attrs);
    options.forEach(function (option) {
      var item = el('option', { value: String(option[0]), text: option[1] });
      if (String(option[0]) === String(value)) { item.selected = true; }
      node.appendChild(item);
    });
    return node;
  }

  function button(text, attrs) {
    var node = el('button', Object.assign({ type: 'button', text: text }, attrs || {}));
    return node;
  }

  function cleanName(text, fallback) {
    var name = String(text || '').trim().toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64);
    return name || fallback;
  }

  function percent(value) {
    return Math.round(Number(value) * 100) + ' %';
  }

  // ---------- the rules form ----------

  function blankRules() {
    return { question: { name: 'answer', type: 'yes_no', bias: 0 }, facts: [{ name: '', kind: 'number', value: '' }], rules: [rule('', 'gt', '', 1)], groups: [] };
  }

  function rule(fact, op, value, weight) {
    return { fact: fact, op: op, value: value, weight: weight };
  }

  function fromRuleExample(example) {
    return {
      question: { name: example.question.name, type: example.question.type, bias: example.question.bias || 0 },
      facts: example.facts.map(function (f) { return { name: f[0], kind: f[1], value: f[2] }; }),
      rules: (example.rules || []).map(function (r) { return rule(r[0], r[1], r[2], r[3]); }),
      groups: (example.groups || []).map(function (g) { return { name: g[0], rules: g[1].map(function (r) { return rule(r[0], r[1], r[2], r[3]); }) }; })
    };
  }

  function factKind(name) {
    var found = rules.facts.filter(function (f) { return cleanName(f.name, '') === name; })[0];
    return found ? found.kind : 'number';
  }

  function opsFor(kind) {
    return kind === 'text' ? TEXT_OPS : kind === 'yesno' ? YESNO_OPS : NUMBER_OPS;
  }

  function factValue(kind, value) {
    if (kind === 'number') { var n = Number(String(value).replace(',', '.')); return isFinite(n) && String(value).trim() !== '' ? n : 0; }
    if (kind === 'yesno') { return value === 'yes' || value === true; }
    return String(value);
  }

  function ruleJson(r) {
    var name = cleanName(r.fact, 'fact');
    var kind = factKind(name);
    var test = {};
    if (kind === 'yesno') { test.eq = r.op !== 'no'; }
    else { test[r.op] = factValue(kind, r.value); }
    var condition = {};
    condition[name] = test;
    return { if: condition, weight: Number(r.weight) };
  }

  function buildRules() {
    var state = {};
    rules.facts.forEach(function (f) {
      var name = cleanName(f.name, '');
      if (name) { state[name] = factValue(f.kind, f.value); }
    });
    var question = { type: rules.question.type };
    if (rules.question.type === 'yes_no') {
      if (Number(rules.question.bias)) { question.bias = Number(rules.question.bias); }
      question.rules = rules.rules.filter(function (r) { return r.fact; }).map(ruleJson);
    } else {
      var key = rules.question.type === 'choice' ? 'options' : 'levels';
      question[key] = {};
      rules.groups.forEach(function (g, index) {
        question[key][cleanName(g.name, (key === 'options' ? 'option_' : 'level_') + (index + 1))] = g.rules.filter(function (r) { return r.fact; }).map(ruleJson);
      });
    }
    var questions = {};
    questions[cleanName(rules.question.name, 'answer')] = question;
    return { state: state, questions: questions };
  }

  function factOptions() {
    var names = rules.facts.map(function (f) { return cleanName(f.name, ''); }).filter(Boolean);
    return names.length ? names.map(function (n) { return [n, n]; }) : [['', 'add a fact first']];
  }

  function ruleRow(r, path) {
    var name = r.fact || (factOptions()[0] || [''])[0];
    if (!r.fact) { r.fact = name; }
    var kind = factKind(cleanName(r.fact, ''));
    var ops = opsFor(kind);
    if (!ops.some(function (o) { return o[0] === r.op; })) { r.op = ops[0][0]; }
    var weights = rules.question.type === 'yes_no' ? WEIGHTS : CHOICE_WEIGHTS;
    var row = el('div', { class: 'decide-row decide-rule' }, [
      el('span', { class: 'decide-word', text: 'If' }),
      select(factOptions(), r.fact, { 'data-path': path + '.fact', 'aria-label': 'Fact' }),
      select(ops, r.op, { 'data-path': path + '.op', 'aria-label': 'Comparison' }),
      kind === 'yesno' ? null : el('input', { type: kind === 'number' ? 'number' : 'text', step: 'any', value: r.value, 'data-path': path + '.value', 'aria-label': 'Value', placeholder: kind === 'number' ? '50' : 'text' }),
      el('span', { class: 'decide-word', text: 'it counts' }),
      select(weights, r.weight, { 'data-path': path + '.weight', 'aria-label': 'Weight' }),
      button('Remove', { class: 'decide-remove', 'data-remove': path, 'aria-label': 'Remove this rule' })
    ]);
    return row;
  }

  function renderRules() {
    var panel = document.getElementById('rules-form');
    panel.textContent = '';

    var facts = el('div', { class: 'decide-rows' });
    rules.facts.forEach(function (f, i) {
      facts.appendChild(el('div', { class: 'decide-row decide-fact' }, [
        el('input', { type: 'text', value: f.name, placeholder: 'name, like amount', 'data-path': 'facts.' + i + '.name', 'aria-label': 'Fact name' }),
        select([['number', 'Number'], ['text', 'Text'], ['yesno', 'Yes or no']], f.kind, { 'data-path': 'facts.' + i + '.kind', 'data-redraw': '1', 'aria-label': 'Kind of value' }),
        f.kind === 'yesno'
          ? select([['yes', 'Yes'], ['no', 'No']], f.value === 'no' ? 'no' : 'yes', { 'data-path': 'facts.' + i + '.value', 'aria-label': 'Value' })
          : el('input', { type: f.kind === 'number' ? 'number' : 'text', step: 'any', value: f.value, placeholder: f.kind === 'number' ? '30' : 'gold', 'data-path': 'facts.' + i + '.value', 'aria-label': 'Value' }),
        button('Remove', { class: 'decide-remove', 'data-remove': 'facts.' + i, 'aria-label': 'Remove this fact' })
      ]));
    });
    panel.appendChild(el('h3', { text: 'The facts' }));
    panel.appendChild(el('p', { class: 'decide-help', text: 'What you know about the situation. Each fact has a short name, a kind and a value.' }));
    panel.appendChild(facts);
    panel.appendChild(button('Add a fact', { class: 'button button-secondary decide-add', 'data-add': 'facts' }));

    panel.appendChild(el('h3', { text: 'The question' }));
    var head = el('div', { class: 'decide-row decide-question' }, [
      el('input', { type: 'text', value: rules.question.name, placeholder: 'name, like refund_now', 'data-path': 'question.name', 'aria-label': 'Question name' }),
      select([['yes_no', 'Yes or no'], ['choice', 'Pick one of several'], ['scale', 'A level, from low to high']], rules.question.type, { 'data-path': 'question.type', 'data-redraw': '1', 'aria-label': 'Kind of question' }),
      rules.question.type === 'yes_no'
        ? select([[-2, 'Starts leaning no'], [-1, 'Starts leaning a little no'], [0, 'Starts neutral'], [1, 'Starts leaning a little yes'], [2, 'Starts leaning yes']], rules.question.bias || 0, { 'data-path': 'question.bias', 'aria-label': 'Starting point' })
        : null
    ]);
    panel.appendChild(head);

    if (rules.question.type === 'yes_no') {
      panel.appendChild(el('p', { class: 'decide-help', text: 'Each rule that holds pushes the answer towards yes (plus) or no (minus).' }));
      var list = el('div', { class: 'decide-rows' });
      rules.rules.forEach(function (r, i) { list.appendChild(ruleRow(r, 'rules.' + i)); });
      panel.appendChild(list);
      panel.appendChild(button('Add a rule', { class: 'button button-secondary decide-add', 'data-add': 'rules' }));
    } else {
      var word = rules.question.type === 'choice' ? 'option' : 'level';
      panel.appendChild(el('p', { class: 'decide-help', text: rules.question.type === 'choice'
        ? 'Each option collects the weight of its rules that hold. The strongest option wins.'
        : 'Levels go from low to high, in this order. Each level collects the weight of its rules that hold.' }));
      rules.groups.forEach(function (g, gi) {
        var box = el('div', { class: 'decide-group' }, [
          el('div', { class: 'decide-row decide-group-head' }, [
            el('input', { type: 'text', value: g.name, placeholder: word + ' name', 'data-path': 'groups.' + gi + '.name', 'aria-label': 'Name of the ' + word }),
            button('Remove ' + word, { class: 'decide-remove', 'data-remove': 'groups.' + gi })
          ])
        ]);
        var list2 = el('div', { class: 'decide-rows' });
        g.rules.forEach(function (r, ri) { list2.appendChild(ruleRow(r, 'groups.' + gi + '.rules.' + ri)); });
        box.appendChild(list2);
        box.appendChild(button('Add a rule for this ' + word, { class: 'button button-secondary decide-add', 'data-add': 'groups.' + gi + '.rules' }));
        panel.appendChild(box);
      });
      panel.appendChild(button('Add an ' + word, { class: 'button button-secondary decide-add', 'data-add': 'groups' }));
    }
  }

  // ---------- the Clef form ----------

  function blankClef() {
    return { message: '', question: { name: 'answer', type: 'noul', instructions: '' }, yes: '', no: '', choices: [['', ''], ['', '']], levels: ['', ''] };
  }

  function fromClefExample(example) {
    return {
      message: example.message,
      question: { name: example.question.name, type: example.question.type, instructions: example.question.instructions },
      yes: example.yes || '', no: example.no || '',
      choices: (example.choices || [['', ''], ['', '']]).map(function (c) { return [c[0], c[1]]; }),
      levels: (example.levels || ['', '']).slice()
    };
  }

  function buildClef() {
    var question = { type: clef.question.type, instructions: clef.question.instructions };
    if (clef.question.type === 'noul') { question.criteria = { true: clef.yes, false: clef.no }; }
    else if (clef.question.type === 'choice') {
      question.criteria = {};
      clef.choices.forEach(function (c, i) { question.criteria[cleanName(c[0], 'choice_' + (i + 1))] = c[1]; });
    } else { question.criteria = clef.levels.slice(); }
    var questions = {};
    questions[cleanName(clef.question.name, 'answer')] = question;
    return { model: 'clef', state: { message: clef.message }, questions: questions };
  }

  function renderClef() {
    var panel = document.getElementById('clef-form');
    panel.textContent = '';
    panel.appendChild(el('h3', { text: 'The situation' }));
    panel.appendChild(el('textarea', { rows: '3', 'data-clef': 'message', 'aria-label': 'The situation in your own words', placeholder: 'Describe what happened, in your own words.' }));
    panel.lastChild.value = clef.message;
    panel.appendChild(el('h3', { text: 'The question' }));
    panel.appendChild(el('div', { class: 'decide-row decide-question' }, [
      el('input', { type: 'text', value: clef.question.name, placeholder: 'name, like urgent', 'data-clef': 'question.name', 'aria-label': 'Question name' }),
      select([['noul', 'Yes or no, as a number from 0 to 1'], ['choice', 'Pick one of several'], ['score', 'A level, from low to high']], clef.question.type, { 'data-clef': 'question.type', 'data-redraw': '1', 'aria-label': 'Kind of question' })
    ]));
    panel.appendChild(el('input', { type: 'text', class: 'decide-wide', value: clef.question.instructions, placeholder: 'Ask the question, like: Does this need urgent attention?', 'data-clef': 'question.instructions', 'aria-label': 'The question' }));
    if (clef.question.type === 'noul') {
      panel.appendChild(el('label', { class: 'decide-label', text: 'What counts as yes' }));
      panel.appendChild(el('input', { type: 'text', class: 'decide-wide', value: clef.yes, 'data-clef': 'yes', 'aria-label': 'What counts as yes' }));
      panel.appendChild(el('label', { class: 'decide-label', text: 'What counts as no' }));
      panel.appendChild(el('input', { type: 'text', class: 'decide-wide', value: clef.no, 'data-clef': 'no', 'aria-label': 'What counts as no' }));
    } else if (clef.question.type === 'choice') {
      panel.appendChild(el('p', { class: 'decide-help', text: 'Each choice has a short name and what it covers.' }));
      clef.choices.forEach(function (c, i) {
        panel.appendChild(el('div', { class: 'decide-row decide-choice' }, [
          el('input', { type: 'text', value: c[0], placeholder: 'name', 'data-clef': 'choices.' + i + '.0', 'aria-label': 'Choice name' }),
          el('input', { type: 'text', value: c[1], placeholder: 'what it covers', 'data-clef': 'choices.' + i + '.1', 'aria-label': 'What the choice covers' }),
          button('Remove', { class: 'decide-remove', 'data-clef-remove': 'choices.' + i })
        ]));
      });
      panel.appendChild(button('Add a choice', { class: 'button button-secondary decide-add', 'data-clef-add': 'choices' }));
    } else {
      panel.appendChild(el('p', { class: 'decide-help', text: 'Levels from low to high, in this order.' }));
      clef.levels.forEach(function (level, i) {
        panel.appendChild(el('div', { class: 'decide-row decide-choice' }, [
          el('input', { type: 'text', value: level, placeholder: 'level ' + (i + 1), 'data-clef': 'levels.' + i, 'aria-label': 'Level ' + (i + 1) }),
          button('Remove', { class: 'decide-remove', 'data-clef-remove': 'levels.' + i })
        ]));
      });
      panel.appendChild(button('Add a level', { class: 'button button-secondary decide-add', 'data-clef-add': 'levels' }));
    }
  }

  // ---------- keeping the JSON in step ----------

  function writeJson(force) {
    if (jsonEdited && !force) { return; }
    jsonBox.value = JSON.stringify(mode === 'rules' ? buildRules() : buildClef(), null, 2);
    jsonEdited = false;
    jsonNote.textContent = 'Written from the form. You can edit it here too.';
    jsonNote.className = 'decide-note';
  }

  function walk(object, path) {
    var parts = path.split('.');
    var last = parts.pop();
    parts.forEach(function (part) { object = object[part]; });
    return { holder: object, key: last };
  }

  function redraw() {
    if (mode === 'rules') { renderRules(); } else { renderClef(); }
    writeJson(false);
  }

  root.addEventListener('input', function (event) {
    var target = event.target;
    if (target === jsonBox) {
      jsonEdited = true;
      jsonNote.textContent = 'You edited the JSON. Decide sends it as it stands. Changes to the form will not overwrite it until you write it again from the form.';
      jsonNote.className = 'decide-note is-edited';
      return;
    }
    var path = target.getAttribute('data-path');
    var clefPath = target.getAttribute('data-clef');
    if (path) {
      var spot = walk(rules, path);
      spot.holder[spot.key] = target.value;
      if (target.getAttribute('data-redraw') || /\.name$/.test(path)) {
        if (/^facts\.\d+\.kind$/.test(path)) { spot.holder.value = target.value === 'yesno' ? 'yes' : ''; }
        if (path === 'question.type' && target.value !== 'yes_no' && !rules.groups.length) {
          rules.groups = target.value === 'choice'
            ? [{ name: 'first', rules: [rule('', 'gt', '', 1)] }, { name: 'second', rules: [rule('', 'gt', '', 1)] }]
            : [{ name: 'low', rules: [] }, { name: 'high', rules: [rule('', 'gt', '', 1)] }];
        }
        if (target.getAttribute('data-redraw')) { redraw(); return; }
      }
      writeJson(false);
    } else if (clefPath) {
      var place = walk(clef, clefPath);
      place.holder[place.key] = target.value;
      if (target.getAttribute('data-redraw')) { redraw(); return; }
      writeJson(false);
    }
  });

  root.addEventListener('change', function (event) {
    // Name changes alter the fact lists in the rule rows, so redraw once typing ends.
    var path = event.target.getAttribute('data-path') || '';
    if (/^facts\.\d+\.name$/.test(path)) { redraw(); }
  });

  root.addEventListener('click', function (event) {
    var target = event.target.closest('button');
    if (!target) { return; }
    var add = target.getAttribute('data-add');
    var remove = target.getAttribute('data-remove');
    var clefAdd = target.getAttribute('data-clef-add');
    var clefRemove = target.getAttribute('data-clef-remove');
    var example = target.getAttribute('data-example');
    if (add) {
      var list = walk(rules, add + '.x');
      var array = list.holder;
      if (add === 'facts') { array.push({ name: '', kind: 'number', value: '' }); }
      else if (add === 'groups') { array.push({ name: '', rules: [rule('', 'gt', '', 1)] }); }
      else { array.push(rule('', 'gt', '', 1)); }
      redraw();
    } else if (remove) {
      var spot = walk(rules, remove);
      spot.holder.splice(Number(spot.key), 1);
      redraw();
    } else if (clefAdd) {
      clef[clefAdd].push(clefAdd === 'choices' ? ['', ''] : '');
      redraw();
    } else if (clefRemove) {
      var place = walk(clef, clefRemove);
      if (place.holder.length > 2) { place.holder.splice(Number(place.key), 1); }
      redraw();
    } else if (example) {
      var parts = example.split(':');
      if (parts[0] === 'rules') {
        rules = parts[1] === 'blank' ? blankRules() : fromRuleExample(RULE_EXAMPLES.filter(function (e) { return e.id === parts[1]; })[0]);
      } else {
        clef = parts[1] === 'blank' ? blankClef() : fromClefExample(CLEF_EXAMPLES.filter(function (e) { return e.id === parts[1]; })[0]);
      }
      redraw();
      writeJson(true);
    } else if (target.id === 'decide-rewrite') {
      writeJson(true);
    } else if (target.id === 'decide-send') {
      send();
    }
  });

  // ---------- tabs ----------

  // /try-decide#clef opens the Clef tab, so a link can point straight at it,
  // and choosing a tab keeps the address in step for sharing.
  var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));

  function showTab(tab, fromAddress) {
    tabs.forEach(function (other) {
      var selected = other === tab;
      other.setAttribute('aria-selected', String(selected));
      other.tabIndex = selected ? 0 : -1;
      document.getElementById(other.getAttribute('aria-controls')).hidden = !selected;
    });
    mode = tab.id === 'tab-clef' ? 'clef' : 'rules';
    redraw();
    writeJson(true);
    clearAnswer();
    if (!fromAddress && window.history && history.replaceState) {
      history.replaceState(null, '', mode === 'clef' ? '#clef' : location.pathname + location.search);
    }
  }

  function tabFromAddress() {
    var name = location.hash.replace(/^#/, '').toLowerCase();
    if (name === 'clef') { return document.getElementById('tab-clef'); }
    if (name === 'rules') { return document.getElementById('tab-rules'); }
    return null;
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { showTab(tab, false); });
  });
  window.addEventListener('hashchange', function () {
    var tab = tabFromAddress();
    if (tab && tab.getAttribute('aria-selected') !== 'true') { showTab(tab, true); }
  });

  // ---------- the answer in plain words ----------

  function describeTest(field, test) {
    var words = { gt: 'is more than', gte: 'is at least', lt: 'is less than', lte: 'is at most', eq: 'is', ne: 'is not', in: 'is one of', prefix: 'starts with', contains: 'contains' };
    return Object.keys(test || {}).map(function (op) {
      var value = test[op];
      if (op === 'exists') { return field + (value ? ' is there' : ' is missing'); }
      if (typeof value === 'boolean') { return field + ' ' + (words[op] || op) + ' ' + (value ? 'yes' : 'no'); }
      if (Array.isArray(value)) { value = value.join(', '); }
      return field + ' ' + (words[op] || op) + ' ' + (typeof value === 'string' && op !== 'in' ? '"' + value + '"' : value);
    }).join(' and ');
  }

  function describeCondition(condition) {
    if (!condition || typeof condition !== 'object') { return 'a condition'; }
    return Object.keys(condition).map(function (key) {
      if (key === 'any' && Array.isArray(condition.any)) { return 'one of (' + condition.any.map(describeCondition).join('; ') + ')'; }
      if (key === 'not') { return 'not (' + describeCondition(condition.not) + ')'; }
      return describeTest(key, condition[key]);
    }).join(' and ');
  }

  function weightText(weight) {
    return (weight > 0 ? '+' : '') + weight;
  }

  // The action says whether the answer given is clear-cut enough to act on, so
  // the advice follows that answer: an act on a no means do not do it.
  function actionText(answer, question) {
    var act = question && typeof question.act_at === 'number' ? question.act_at : 0.9;
    var review = question && typeof question.review_at === 'number' ? question.review_at : 0.5;
    var said = answer.type === 'yes_no' ? (answer.answer === 'yes' ? 'yes' : 'no') : (answer.type === 'choice' ? answer.choice : answer.level);
    if (answer.action === 'act') {
      if (answer.type === 'yes_no') {
        return (said === 'yes' ? 'Next step: go ahead.' : 'Next step: do not go ahead.') + ' The ' + said + ' is clear-cut enough to act on, at ' + percent(act) + ' or more.';
      }
      return 'Next step: act on ' + said + '. It is clear-cut enough, at ' + percent(act) + ' or more.';
    }
    if (answer.action === 'review') { return 'Next step: let a person check the ' + (answer.type === 'yes_no' ? said : 'answer ' + said) + ' first. It is between ' + percent(review) + ' and ' + percent(act) + ' clear-cut.'; }
    if (answer.action === 'hold') { return 'Next step: do nothing yet. It is less than ' + percent(review) + ' clear-cut, too close to act on either way.'; }
    return '';
  }

  function list(items) {
    return el('ul', {}, items.map(function (text) { return el('li', { text: text }); }));
  }

  function ruleAnswer(name, answer, question) {
    var box = el('div', { class: 'decide-result' });
    box.appendChild(el('h3', { text: name.replace(/_/g, ' ') }));
    var why = [];
    if (answer.type === 'yes_no') {
      box.appendChild(el('p', { class: 'decide-headline', text: (answer.answer === 'yes' ? 'Yes' : 'No') + ', with ' + percent(answer.probability) + ' for yes from the weights.' }));
      (answer.because || []).forEach(function (b) {
        var r = question && question.rules ? question.rules[b.rule] : null;
        why.push((r ? describeCondition(r.if) : 'rule ' + (b.rule + 1)) + ' (' + weightText(b.weight) + ')');
      });
    } else {
      var picked = answer.type === 'choice' ? answer.choice : answer.level;
      var probabilities = answer.probabilities || {};
      box.appendChild(el('p', { class: 'decide-headline', text: (answer.type === 'choice' ? 'Best choice: ' : 'Level: ') + picked + ', ' + percent(probabilities[picked]) + '.' }));
      var others = Object.keys(probabilities).filter(function (k) { return k !== picked; }).map(function (k) { return k + ' ' + percent(probabilities[k]); });
      if (others.length) { box.appendChild(el('p', { text: 'The others: ' + others.join(', ') + '.' })); }
      if (answer.tied) { box.appendChild(el('p', { text: answer.tied.join(' and ') + ' scored the same. The first one listed wins.' })); }
      if (answer.type === 'scale' && typeof answer.expected === 'number') {
        box.appendChild(el('p', { text: 'Average level: ' + answer.expected.toFixed(1) + ' on a scale from 0 to ' + (Object.keys(probabilities).length - 1) + '.' }));
      }
      var groups = question ? (question.options || question.levels || {}) : {};
      (answer.because || []).forEach(function (b) {
        var group = b.option || b.level;
        var r = groups[group] ? groups[group][b.rule] : null;
        why.push(group + ': ' + (r ? describeCondition(r.if) : 'rule ' + (b.rule + 1)) + ' (' + weightText(b.weight) + ')');
      });
    }
    box.appendChild(el('p', { text: actionText(answer, question) }));
    box.appendChild(el('p', { class: 'decide-help', text: 'Clear-cut: ' + percent(answer.confidence) + '. This is how one-sided the weights are, not a measured chance that the rules are right.' }));
    if (why.length) {
      box.appendChild(el('p', { class: 'decide-why', text: 'Why: these rules held.' }));
      box.appendChild(list(why));
    } else {
      box.appendChild(el('p', { class: 'decide-why', text: 'No rule held, so the answer comes from the starting point alone.' }));
    }
    return box;
  }

  function modelAnswer(name, answer, question) {
    var box = el('div', { class: 'decide-result' });
    box.appendChild(el('h3', { text: name.replace(/_/g, ' ') }));
    if (answer.type === 'noul') {
      var value = Number(answer.noul);
      box.appendChild(el('p', { class: 'decide-headline', text: value.toFixed(2) + ' on a scale from 0 (no) to 1 (yes): ' + (value >= 0.5 ? 'leaning yes.' : 'leaning no.') }));
      if (question && question.criteria) {
        box.appendChild(list(['1 means: ' + question.criteria.true, '0 means: ' + question.criteria.false]));
      }
    } else if (answer.type === 'choice') {
      var p = answer.probabilities || {};
      box.appendChild(el('p', { class: 'decide-headline', text: 'Best choice: ' + answer.choice + ', ' + percent(p[answer.choice]) + '.' }));
      box.appendChild(el('p', { text: 'All choices: ' + Object.keys(p).map(function (k) { return k + ' ' + percent(p[k]); }).join(', ') + '.' }));
    } else if (answer.type === 'score') {
      var legend = answer.legend || [];
      var score = Number(answer.score);
      var low = legend[Math.floor(score)] || '';
      var high = legend[Math.ceil(score)] || '';
      box.appendChild(el('p', { class: 'decide-headline', text: 'Score ' + score.toFixed(1) + (low === high ? ': ' + low : ', between ' + low + ' and ' + high) + '.' }));
      box.appendChild(el('p', { text: 'Levels: ' + legend.map(function (label, i) { return label + ' ' + percent((answer.probabilities || [])[i] || 0); }).join(', ') + '.' }));
    }
    if (typeof answer.confidence === 'number') {
      box.appendChild(el('p', { text: 'Clef\'s own confidence: ' + percent(answer.confidence) + '. It is the model\'s figure, not a guarantee that the answer is right, and the model gives no next step. Keep a person in the loop for anything that matters.' }));
    }
    return box;
  }

  function refusal(status, body, retryAfter) {
    var box = el('div', { class: 'decide-result is-refused' });
    var error = body && body.error ? String(body.error) : 'The API answered with status ' + status + '.';
    var wait = retryAfter ? ' Try again in ' + retryAfter + ' seconds.' : ' Try again later.';
    var headline = 'The API said no: ' + error;
    if (status === 429) {
      headline = 'The request limit is reached for now.' + wait;
    } else if (status === 503) {
      headline = 'The Clef model is not available right now. Rules still work.' + wait;
    } else if (status === 502) {
      headline = 'The model request could not be completed. Try again later.';
    } else if (status === 504) {
      headline = 'The model request took too long and timed out. Try again later.';
    }
    box.appendChild(el('p', { class: 'decide-headline', text: headline }));
    if (body && body.fix) { box.appendChild(el('p', { text: 'What to do: ' + body.fix })); }
    return box;
  }

  function clearAnswer() {
    plain.textContent = '';
    plain.appendChild(el('p', { class: 'decide-note', text: 'Press Decide to see the answer here.' }));
    responseBox.textContent = '';
  }

  function send() {
    var request;
    try {
      request = JSON.parse(jsonBox.value);
    } catch (error) {
      plain.textContent = '';
      plain.appendChild(el('div', { class: 'decide-result is-refused' }, [el('p', { class: 'decide-headline', text: 'The JSON above is not valid, so nothing was sent.' }), el('p', { text: String(error.message || error) })]));
      responseBox.textContent = '';
      return;
    }
    sendButton.disabled = true;
    plain.textContent = '';
    plain.appendChild(el('p', { class: 'decide-note', text: 'Asking Decide...' }));
    var started = Date.now();
    fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: jsonBox.value })
      .then(function (response) {
        var retryAfter = response.headers.get('Retry-After');
        return response.text().then(function (text) {
          var body = null;
          try { body = JSON.parse(text); } catch (ignore) { body = null; }
          return { status: response.status, ok: response.ok, body: body, text: text, retryAfter: retryAfter };
        });
      })
      .then(function (result) {
        var ms = Date.now() - started;
        responseBox.textContent = result.body ? JSON.stringify(result.body, null, 2) : result.text;
        plain.textContent = '';
        if (!result.ok || !result.body || !result.body.answers) {
          plain.appendChild(refusal(result.status, result.body, result.retryAfter));
          return;
        }
        var questions = request && request.questions ? request.questions : {};
        Object.keys(result.body.answers).forEach(function (name) {
          var answer = result.body.answers[name];
          var question = questions[name];
          plain.appendChild(answer.type === 'noul' || answer.type === 'score' || result.body.model ? modelAnswer(name, answer, question) : ruleAnswer(name, answer, question));
        });
        plain.appendChild(el('p', { class: 'decide-note', text: 'Answered in ' + ms + ' ms, measured in this browser, network included.' }));
      })
      .catch(function () {
        plain.textContent = '';
        plain.appendChild(el('div', { class: 'decide-result is-refused' }, [el('p', { class: 'decide-headline', text: 'Could not reach the API. Check the connection and try again.' })]));
      })
      .then(function () { sendButton.disabled = false; });
  }

  // ---------- start ----------

  function exampleButtons(id, examples, prefix) {
    var holder = document.getElementById(id);
    examples.forEach(function (example) {
      holder.appendChild(button(example.title, { class: 'button button-secondary', 'data-example': prefix + ':' + example.id }));
    });
    holder.appendChild(button('Start blank', { class: 'button button-secondary', 'data-example': prefix + ':blank' }));
  }

  exampleButtons('rules-examples', RULE_EXAMPLES, 'rules');
  exampleButtons('clef-examples', CLEF_EXAMPLES, 'clef');
  rules = fromRuleExample(RULE_EXAMPLES[0]);
  clef = fromClefExample(CLEF_EXAMPLES[0]);
  renderClef();
  renderRules();
  writeJson(true);
  clearAnswer();
  sendButton.disabled = false;
  document.getElementById('decide-status').textContent = 'Ready. Pick an example or fill in your own.';
  var linked = tabFromAddress();
  if (linked && linked.id !== 'tab-rules') { showTab(linked, true); }
}());
