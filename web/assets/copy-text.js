/*
 * A copy button for a block of text. An element with data-copy-button="ID"
 * gets a button, as its first child, that copies the text of the element with
 * that id. The button is made here, so a page without JavaScript shows no
 * button that does nothing; the text itself can still be selected. The label
 * comes from data-copy-label. Nothing is sent anywhere.
 */
(function () {
  'use strict';

  if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') { return; }

  Array.prototype.forEach.call(document.querySelectorAll('[data-copy-button]'), function (row) {
    var source = document.getElementById(row.getAttribute('data-copy-button'));
    if (!source) { return; }
    var label = row.getAttribute('data-copy-label') || 'Copy';
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button-primary';
    button.textContent = label;
    button.addEventListener('click', function () {
      navigator.clipboard.writeText(source.textContent).then(function () {
        button.textContent = 'Copied';
        setTimeout(function () { button.textContent = label; }, 1500);
      }, function () {
        button.textContent = 'Copy failed: select the text instead';
      });
    });
    row.insertBefore(button, row.firstChild);
  });
})();
