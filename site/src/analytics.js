// GoatCounter, loaded 3 s after window load so it never competes with the
// job data for bandwidth. Lives in a module (not an inline <script>) so the
// production CSP needs no 'unsafe-inline' for scripts.

const GC_ENDPOINT = 'https://riteshrana.goatcounter.com/count';
const GC_SCRIPT = 'https://gc.zgo.at/count.js';
const DELAY_AFTER_LOAD_MS = 3000;

export function loadAnalytics(doc = document) {
  if (window.goatcounter || doc.querySelector('script[data-goatcounter]')) return;
  const s = doc.createElement('script');
  s.async = true;
  s.dataset.goatcounter = GC_ENDPOINT;
  s.src = GC_SCRIPT;
  doc.head.appendChild(s);
}

export function scheduleAnalytics(win = window) {
  const later = () => win.setTimeout(() => loadAnalytics(win.document), DELAY_AFTER_LOAD_MS);
  if (win.document.readyState === 'complete') later();
  else win.addEventListener('load', later, { once: true });
}

scheduleAnalytics();
