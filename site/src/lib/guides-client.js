// Progressive enhancement for the static /guides/ pages (served as
// /guides/guides.js next to ./saved.js; see scripts/seo/guides.mjs). The pages
// are complete without it. With it, the index gains search, All / Unread /
// Saved views and a format filter, and every guide gains "Mark as read" and
// "Save". Read and saved guides stay in this browser's localStorage and are
// never sent anywhere. No network requests, no third-party code.

import { loadSavedIds, storeSavedIds } from './saved.js';

export const GUIDES_READ_KEY = 'ngj:guides-read:v1';
export const GUIDES_SAVED_KEY = 'ngj:guides-saved:v1';

/** Lowercase with accents folded, so "resume" matches "résumé". */
export function normalizeText(value) {
  return String(value ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

/**
 * @param {{slug: string, text: string, formats: string[]}} card
 * @param {{query: string, view: 'all'|'unread'|'saved', format: string}} filters
 * @param {{read: Set<string>, saved: Set<string>}} marks
 */
export function matchesGuide(card, { query, view, format }, { read, saved }) {
  if (view === 'unread' && read.has(card.slug)) return false;
  if (view === 'saved' && !saved.has(card.slug)) return false;
  if (format && !card.formats.includes(format)) return false;
  const text = normalizeText(card.text);
  return normalizeText(query).split(/\s+/).filter(Boolean).every((word) => text.includes(word));
}

/**
 * A read/saved set backed by storage; when storage fails the set still works
 * for this page view and `toggle` returns false so the page can say so.
 */
function markStore(getStorage, key) {
  let ids = loadSavedIds(getStorage, key);
  return {
    has: (slug) => ids.has(slug),
    get set() { return ids; },
    toggle(slug) {
      const next = new Set(ids);
      if (next.has(slug)) next.delete(slug); else next.add(slug);
      ids = next;
      return storeSavedIds(getStorage, ids, key);
    },
    reload() { ids = loadSavedIds(getStorage, key); },
  };
}

const isTyping = (el) => Boolean(el && (el.isContentEditable || /^(?:INPUT|TEXTAREA|SELECT)$/.test(el.tagName)));
const reveal = (el) => { if (el) el.hidden = false; };
/** Show the "storage is blocked" note once a write fails. */
const noteStored = (doc, stored) => { if (!stored) reveal(doc.querySelector('[data-guides-storage]')); };

/** @param {Document} doc @param {() => Storage|null|undefined} getStorage */
export function initGuidesIndex(doc, getStorage) {
  const read = markStore(getStorage, GUIDES_READ_KEY);
  const saved = markStore(getStorage, GUIDES_SAVED_KEY);
  const q = doc.getElementById('guide-q');
  const formatSelect = doc.getElementById('guide-format');
  const viewButtons = [...doc.querySelectorAll('[data-view]')];
  const countLine = doc.querySelector('[data-guides-count]');
  const empty = doc.querySelector('[data-guides-empty]');
  const sections = [...doc.querySelectorAll('[data-section]')];
  const cards = [...doc.querySelectorAll('.card[data-guide]')].map((el) => ({
    el,
    slug: el.dataset.guide,
    text: el.dataset.text || '',
    formats: (el.dataset.formats || '').split(' ').filter(Boolean),
    star: el.querySelector('.star'),
    meta: el.querySelector('.meta'),
  }));
  const filters = { query: '', view: 'all', format: '' };
  const setCount = (name, n) => doc.querySelectorAll(`[data-count="${name}"]`).forEach((el) => { el.textContent = String(n); });

  function paintCard(card) {
    const isRead = read.has(card.slug);
    card.el.classList.toggle('is-read', isRead);
    let badge = card.meta?.querySelector('.tag.read');
    if (isRead && !badge && card.meta) {
      badge = doc.createElement('span');
      badge.className = 'tag read';
      badge.textContent = '✓ READ';
      card.meta.append(' ', badge);
    } else if (!isRead && badge) {
      badge.remove();
    }
    if (card.star) {
      const on = saved.has(card.slug);
      card.star.setAttribute('aria-pressed', String(on));
      card.star.textContent = on ? '★' : '☆';
    }
  }

  function apply() {
    const marks = { read: read.set, saved: saved.set };
    let shown = 0;
    for (const card of cards) {
      card.el.hidden = !matchesGuide(card, filters, marks);
      if (!card.el.hidden) shown += 1;
      paintCard(card);
    }
    for (const section of sections) {
      const n = section.querySelectorAll('.card:not([hidden])').length;
      section.hidden = n === 0;
      const label = section.querySelector('[data-section-count]');
      if (label) label.textContent = `(${n})`;
    }
    const readCount = cards.filter((c) => read.has(c.slug)).length;
    setCount('all', cards.length);
    setCount('read', readCount);
    setCount('unread', cards.length - readCount);
    setCount('saved', cards.filter((c) => saved.has(c.slug)).length);
    for (const b of viewButtons) b.setAttribute('aria-pressed', String(b.dataset.view === filters.view));
    if (countLine) countLine.textContent = `Showing ${shown} of ${cards.length} guides`;
    if (empty) empty.hidden = shown !== 0;
  }

  function reset() {
    Object.assign(filters, { query: '', view: 'all', format: '' });
    if (q) q.value = '';
    if (formatSelect) formatSelect.value = '';
    apply();
  }

  q?.addEventListener('input', () => { filters.query = q.value; apply(); });
  q?.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && q.value) { e.preventDefault(); q.value = ''; filters.query = ''; apply(); }
  });
  formatSelect?.addEventListener('change', () => { filters.format = formatSelect.value; apply(); });
  for (const b of viewButtons) b.addEventListener('click', () => { filters.view = b.dataset.view; apply(); });
  for (const card of cards) card.star?.addEventListener('click', () => { noteStored(doc, saved.toggle(card.slug)); apply(); });
  doc.querySelector('[data-reset]')?.addEventListener('click', reset);
  doc.addEventListener('keydown', (e) => {
    if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target) || !q) return;
    e.preventDefault();
    q.focus();
  });
  // Back from a guide (bfcache) or another tab: pick up marks made elsewhere.
  doc.defaultView?.addEventListener('pageshow', () => { read.reload(); saved.reload(); apply(); });
  doc.defaultView?.addEventListener('storage', () => { read.reload(); saved.reload(); apply(); });

  for (const el of [doc.querySelector('[data-guides-toolbar]'), doc.querySelector('[data-guides-progress]'), countLine]) reveal(el);
  for (const card of cards) reveal(card.star);
  apply();
  return { apply, reset };
}

/** @param {Document} doc @param {() => Storage|null|undefined} getStorage */
export function initGuidePage(doc, getStorage) {
  const tools = doc.querySelector('[data-guide-tools]');
  const slug = tools?.dataset.guide;
  if (!tools || !slug) return;
  const read = markStore(getStorage, GUIDES_READ_KEY);
  const saved = markStore(getStorage, GUIDES_SAVED_KEY);
  const readButton = tools.querySelector('[data-read]');
  const saveButton = tools.querySelector('[data-save]');
  // The accessible name stays fixed; aria-pressed carries the state and only the decorative glyph changes.
  const paintButton = (button, on, glyphs) => {
    if (!button) return;
    button.setAttribute('aria-pressed', String(on));
    const glyph = button.querySelector('.glyph');
    if (glyph) glyph.textContent = on ? glyphs[1] : glyphs[0];
  };
  const paint = () => {
    paintButton(readButton, read.has(slug), ['○', '✓']);
    paintButton(saveButton, saved.has(slug), ['☆', '★']);
  };
  readButton?.addEventListener('click', () => { noteStored(doc, read.toggle(slug)); paint(); });
  saveButton?.addEventListener('click', () => { noteStored(doc, saved.toggle(slug)); paint(); });
  reveal(tools);
  paint();
}

/** Start the right enhancement for this page; returns which one ran. */
export function initGuides(doc, getStorage) {
  const kind = doc.documentElement.dataset.ngjGuides;
  if (kind === 'index') initGuidesIndex(doc, getStorage);
  else if (kind === 'page') initGuidePage(doc, getStorage);
  else return null;
  return kind;
}

// Self-start only on a guides page (never under test, where the attribute is absent at import).
if (typeof document !== 'undefined' && document.documentElement?.dataset.ngjGuides) {
  initGuides(document, () => window.localStorage);
}
