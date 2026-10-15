// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';
import {
  GUIDES_READ_KEY, GUIDES_SAVED_KEY, initGuidePage, initGuides, initGuidesIndex, matchesGuide, normalizeText,
} from './guides-client.js';
import { renderGuidePage, renderGuidesIndex } from '../../scripts/seo/guides.mjs';

const SITE = 'https://jobs.example.test';
const g = (slug, title, section, formats, description = '') => ({
  slug, title, section, formats, description, order: 1, updated: '2026-09-30', published: '2026-09-25',
  useWhen: 'Read this when x.', youGet: 'You get y.', words: 500, readMinutes: 2, html: '<h2 id="a">A</h2>', headings: [{ level: 2, text: 'A' }],
});
const GUIDES = [
  g('ats-friendly-resume', 'An ATS-friendly résumé', 'Résumé and applications', ['checklist']),
  g('negotiation', 'Negotiating a new grad offer', 'Offers', ['script', 'checklist'], 'How to ask about compensation'),
  g('opt-and-stem-opt', 'OPT and STEM OPT', 'International students', ['official']),
];

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return { getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => data.set(k, String(v)), data };
}

function load(html) {
  document.documentElement.innerHTML = html.replace(/^[\s\S]*?<html[^>]*>/, '').replace(/<\/html>\s*$/, '');
}

const visible = () => [...document.querySelectorAll('.card')].filter((c) => !c.hidden).map((c) => c.dataset.guide);
const type = (value) => {
  const q = document.getElementById('guide-q');
  q.value = value;
  q.dispatchEvent(new Event('input', { bubbles: true }));
};

describe('matchesGuide / normalizeText', () => {
  const card = { slug: 'ats-friendly-resume', text: 'an ats-friendly résumé checklist', formats: ['checklist'] };
  const sets = { read: new Set(['ats-friendly-resume']), saved: new Set() };

  it('folds accents and case so "resume" finds "résumé"', () => {
    expect(normalizeText('Résumé  ATS')).toBe('resume  ats');
    expect(matchesGuide(card, { query: 'RESUME ats', view: 'all', format: '' }, sets)).toBe(true);
    expect(matchesGuide(card, { query: 'resume visa', view: 'all', format: '' }, sets)).toBe(false);
  });

  it('applies the view and format filters', () => {
    expect(matchesGuide(card, { query: '', view: 'unread', format: '' }, sets)).toBe(false);
    expect(matchesGuide(card, { query: '', view: 'saved', format: '' }, sets)).toBe(false);
    expect(matchesGuide(card, { query: '', view: 'all', format: 'script' }, sets)).toBe(false);
    expect(matchesGuide(card, { query: '', view: 'all', format: 'checklist' }, sets)).toBe(true);
  });
});

describe('guides index enhancement', () => {
  let storage;
  beforeEach(() => {
    storage = memoryStorage({ [GUIDES_READ_KEY]: '["negotiation"]', [GUIDES_SAVED_KEY]: 'not json' });
    load(renderGuidesIndex(GUIDES, { siteUrl: SITE, paths: [] }));
    initGuidesIndex(document, () => storage);
  });

  it('reveals the toolbar, counts and save buttons, and reflects stored reads', () => {
    expect(document.querySelector('[data-guides-toolbar]').hidden).toBe(false);
    expect([...document.querySelectorAll('.star')].every((b) => !b.hidden)).toBe(true);
    expect(document.querySelector('[data-count="read"]').textContent).toBe('1');
    expect(document.querySelector('[data-count="unread"]').textContent).toBe('2');
    expect(document.querySelector('[data-count="saved"]').textContent).toBe('0');
    expect(document.querySelector('[data-guide="negotiation"]').classList.contains('is-read')).toBe(true);
    expect(document.querySelector('[data-guides-count]').textContent).toBe('Showing 3 of 3 guides');
  });

  it('search filters cards, hides empty sections and shows the empty state with a reset', () => {
    type('resume');
    expect(visible()).toEqual(['ats-friendly-resume']);
    expect(document.getElementById('sec-offers').hidden).toBe(true);
    expect(document.querySelector('[data-guides-count]').textContent).toBe('Showing 1 of 3 guides');
    type('zzz');
    expect(visible()).toEqual([]);
    expect(document.querySelector('[data-guides-empty]').hidden).toBe(false);
    document.querySelector('[data-reset]').click();
    expect(visible()).toHaveLength(3);
    expect(document.getElementById('guide-q').value).toBe('');
  });

  it('saving a guide persists it and the Saved view shows only saved guides', () => {
    const star = document.querySelector('[data-guide="opt-and-stem-opt"] .star');
    star.click();
    expect(star.getAttribute('aria-pressed')).toBe('true');
    expect(JSON.parse(storage.data.get(GUIDES_SAVED_KEY))).toEqual(['opt-and-stem-opt']);
    document.querySelector('[data-view="saved"]').click();
    expect(document.querySelector('[data-view="saved"]').getAttribute('aria-pressed')).toBe('true');
    expect(visible()).toEqual(['opt-and-stem-opt']);
    document.querySelector('[data-view="unread"]').click();
    expect(visible()).toEqual(['ats-friendly-resume', 'opt-and-stem-opt']);
  });

  it('filters by format', () => {
    const select = document.getElementById('guide-format');
    select.value = 'script';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    expect(visible()).toEqual(['negotiation']);
  });

  it('"/" focuses search outside text fields and Escape clears it', () => {
    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }));
    const q = document.getElementById('guide-q');
    expect(document.activeElement).toBe(q);
    type('offer');
    q.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(q.value).toBe('');
    expect(visible()).toHaveLength(3);
  });

  it('keeps working in memory when storage is unavailable', () => {
    load(renderGuidesIndex(GUIDES, { siteUrl: SITE, paths: [] }));
    initGuidesIndex(document, () => { throw new Error('blocked'); });
    const star = document.querySelector('.star');
    expect(document.querySelector('[data-guides-storage]').hidden).toBe(true);
    star.click();
    expect(star.getAttribute('aria-pressed')).toBe('true');
    expect(document.querySelector('[data-guides-storage]').hidden).toBe(false);
  });
});

describe('guide page enhancement', () => {
  it('Mark as read and Save toggle, persist, and show their state', () => {
    const storage = memoryStorage();
    load(renderGuidePage(GUIDES[1], { siteUrl: SITE, siblings: GUIDES }));
    initGuidePage(document, () => storage);
    const tools = document.querySelector('[data-guide-tools]');
    expect(tools.hidden).toBe(false);
    const read = tools.querySelector('[data-read]');
    const save = tools.querySelector('[data-save]');
    read.click();
    save.click();
    expect(read.getAttribute('aria-pressed')).toBe('true');
    expect(read.textContent).toBe('✓ Mark as read');
    expect(save.textContent).toBe('★ Save');
    expect(document.querySelector('[data-guides-storage]').hidden).toBe(true);
    expect(JSON.parse(storage.data.get(GUIDES_READ_KEY))).toEqual(['negotiation']);
    expect(JSON.parse(storage.data.get(GUIDES_SAVED_KEY))).toEqual(['negotiation']);
    read.click();
    expect(read.textContent).toBe('○ Mark as read');
    expect(read.getAttribute('aria-pressed')).toBe('false');
    expect(JSON.parse(storage.data.get(GUIDES_READ_KEY))).toEqual([]);
  });

  it('initGuides picks the page type from the html element and ignores other pages', () => {
    const storage = memoryStorage();
    load(renderGuidePage(GUIDES[0], { siteUrl: SITE, siblings: GUIDES }));
    document.documentElement.dataset.ngjGuides = 'page';
    expect(initGuides(document, () => storage)).toBe('page');
    document.documentElement.dataset.ngjGuides = 'index';
    load(renderGuidesIndex(GUIDES, { siteUrl: SITE, paths: [] }));
    document.documentElement.dataset.ngjGuides = 'index';
    expect(initGuides(document, () => storage)).toBe('index');
    delete document.documentElement.dataset.ngjGuides;
    expect(initGuides(document, () => storage)).toBe(null);
  });
});
