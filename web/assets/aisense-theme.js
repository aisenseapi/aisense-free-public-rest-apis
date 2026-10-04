/*
 * aisense-theme.js - the moon button in the header.
 *
 * Pages follow the system setting through prefers-color-scheme in
 * aisense.css. The button fixes the other theme with data-theme on <html> and
 * remembers it in localStorage. A choice that matches the system setting is
 * dropped, so the page follows the system again.
 *
 * Loaded in <head> without defer, so a stored choice is applied before the
 * first paint and a dark page never flashes light. tools/site_nav.py writes
 * the script tag and the button into every page.
 */
(function () {
  var root = document.documentElement;
  var KEY = 'aisense-theme';
  var media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function systemDark() { return !!(media && media.matches); }

  function stored() {
    try { return window.localStorage.getItem(KEY); } catch (error) { return null; }
  }

  function remember(theme) {
    try {
      if (theme) { window.localStorage.setItem(KEY, theme); } else { window.localStorage.removeItem(KEY); }
    } catch (error) { /* Private mode or blocked storage: the choice lasts for this page only. */ }
  }

  function apply(theme) {
    if (theme === 'dark' || theme === 'light') { root.setAttribute('data-theme', theme); } else { root.removeAttribute('data-theme'); }
  }

  function isDark() {
    var theme = root.getAttribute('data-theme');
    return theme ? theme === 'dark' : systemDark();
  }

  function sync() {
    var buttons = document.querySelectorAll('.theme-toggle');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed', isDark() ? 'true' : 'false');
    }
  }

  apply(stored());

  document.addEventListener('click', function (event) {
    var button = event.target && event.target.closest ? event.target.closest('.theme-toggle') : null;
    if (!button) { return; }
    var next = isDark() ? 'light' : 'dark';
    var follow = (next === 'dark') === systemDark();
    apply(follow ? null : next);
    remember(follow ? null : next);
    sync();
  });

  document.addEventListener('DOMContentLoaded', sync);
  if (media && media.addEventListener) { media.addEventListener('change', sync); }
})();
