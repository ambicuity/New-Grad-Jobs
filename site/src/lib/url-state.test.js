import { describe, expect, it } from 'vitest';
import { defaultView, parseViewState, sameView, serializeViewState } from './url-state.js';
import { EMPTY_FILTERS, toggleFacet, toggleVisa } from './filters.js';

const view = (over = {}) => ({ ...defaultView(), ...over });

describe('defaultView', () => {
  it('is the hiring tab, no query, empty filters, newest first, nothing selected', () => {
    const v = defaultView();
    expect(v).toMatchObject({ tab: 'hiring', q: '', sort: { key: 'posted', dir: -1 }, job: null, savedOnly: false });
    expect(v.filters).toEqual(EMPTY_FILTERS());
  });
});

describe('serializeViewState', () => {
  it('writes nothing for the default view', () => {
    expect(serializeViewState(defaultView())).toBe('');
  });

  it('writes every non-default field', () => {
    let filters = toggleFacet(EMPTY_FILTERS(), 'type', 'SWE');
    filters = toggleFacet(filters, 'type', 'ML');
    filters = toggleFacet(filters, 'rmt', 'remote');
    filters = toggleFacet(filters, 'tier', 'unicorn');
    filters = toggleFacet(filters, 'company', 'AT&T, Inc.');
    filters = toggleVisa(filters, true);
    const out = serializeViewState(view({
      tab: 'contributors', q: 'data eng', filters, sort: { key: 'comp', dir: 1 }, job: 'job_abc', savedOnly: true,
    }));
    const p = new URLSearchParams(out);
    expect(out.startsWith('?')).toBe(true);
    expect(p.get('tab')).toBe('contributors');
    expect(p.get('q')).toBe('data eng');
    expect(p.getAll('role')).toEqual(['SWE', 'ML']);
    expect(p.getAll('remote')).toEqual(['remote']);
    expect(p.getAll('tier')).toEqual(['unicorn']);
    expect(p.getAll('co')).toEqual(['AT&T, Inc.']);
    expect(p.get('visa')).toBe('none');
    expect(p.get('sort')).toBe('comp-asc');
    expect(p.get('job')).toBe('job_abc');
    expect(p.get('saved')).toBe('1');
  });

  it('writes visa=restricted for the restricted-only filter', () => {
    expect(serializeViewState(view({ filters: toggleVisa(EMPTY_FILTERS(), false) }))).toBe('?visa=restricted');
  });

  it('keeps unrelated params (utm tags etc.) from the base search', () => {
    const out = serializeViewState(view({ q: 'x' }), '?utm_source=reddit&q=old&job=stale');
    const p = new URLSearchParams(out);
    expect(p.get('utm_source')).toBe('reddit');
    expect(p.get('q')).toBe('x');
    expect(p.has('job')).toBe(false);
  });
});

describe('parseViewState', () => {
  it('round-trips a serialized view', () => {
    let filters = toggleFacet(EMPTY_FILTERS(), 'type', 'SWE');
    filters = toggleFacet(filters, 'company', 'Palantir');
    filters = toggleVisa(filters, false);
    const v = view({ q: 'kitsap', filters, sort: { key: 'co', dir: -1 }, job: 'job_1', savedOnly: true });
    expect(parseViewState(serializeViewState(v))).toEqual(v);
  });

  it('returns the default view for an empty or missing search', () => {
    expect(parseViewState('')).toEqual(defaultView());
    expect(parseViewState(undefined)).toEqual(defaultView());
  });

  it('drops unknown facet values, bad sorts and oversized strings', () => {
    const long = 'x'.repeat(500);
    const v = parseViewState(`?role=SWE&role=NOPE&remote=moon&tier=S&visa=maybe&sort=deadline-asc&tab=admin&job=${long}&co=${long}&saved=yes`);
    expect([...v.filters.type]).toEqual(['SWE']);
    expect(v.filters.rmt.size).toBe(0);
    expect(v.filters.tier.size).toBe(0);
    expect(v.filters.company.size).toBe(0);
    expect(v.filters.visa).toBeNull();
    expect(v.sort).toEqual({ key: 'posted', dir: -1 });
    expect(v.tab).toBe('hiring');
    expect(v.job).toBeNull();
    expect(v.savedOnly).toBe(false);
  });

  it('truncates an oversized query instead of dropping it', () => {
    expect(parseViewState(`?q=${'a'.repeat(300)}`).q).toHaveLength(200);
  });

  it('maps legacy #contributors / #hiring hash links to the tab', () => {
    expect(parseViewState('', '#contributors').tab).toBe('contributors');
    expect(parseViewState('', '#hiring').tab).toBe('hiring');
    expect(parseViewState('', '#job-list').tab).toBe('hiring');
    // An explicit ?tab wins over a stale hash.
    expect(parseViewState('?tab=hiring', '#contributors').tab).toBe('hiring');
  });
});

describe('sameView', () => {
  it('compares views by their serialized form', () => {
    expect(sameView(defaultView(), defaultView())).toBe(true);
    expect(sameView(defaultView(), view({ q: 'a' }))).toBe(false);
  });
});
