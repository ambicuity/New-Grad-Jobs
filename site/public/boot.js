// Boot watchdog (classic script, independent of the app bundle so it still
// runs when the bundle fails to download or throws before mounting).
// If the app hasn't replaced #root's static boot content within 10 s, reveal
// the "failed to load" notice that index.html ships hidden inside #root.
// React's createRoot().render() replaces #root's children on mount, which
// removes both the notice and its marker — so a late mount cleans it up.
(function () {
  'use strict';
  var BOOT_TIMEOUT_MS = 10000;
  window.setTimeout(function () {
    var notice = document.querySelector('#root [data-ngj-boot-fail]');
    if (notice) notice.hidden = false;
  }, BOOT_TIMEOUT_MS);
})();
