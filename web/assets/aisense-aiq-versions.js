/*
 * AI SENSE AIQ versions: every version starts folded, so a link to one, such
 * as /aisense-aiq-versions#dar from the menu, opens the box it names. Without
 * this script the link still lands on the box, closed. Nothing is sent
 * anywhere.
 */
(function () {
  'use strict';

  function openNamed() {
    var id = decodeURIComponent((window.location.hash || '').slice(1));
    if (!/^[a-z]{3}$/.test(id)) { return; }
    var box = document.getElementById(id);
    if (box && box.tagName === 'DETAILS' && box.classList.contains('aiq-version')) {
      box.open = true;
      box.scrollIntoView();
    }
  }

  openNamed();
  window.addEventListener('hashchange', openNamed);
})();
