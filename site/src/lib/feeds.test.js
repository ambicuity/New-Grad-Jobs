import { describe, expect, it } from 'vitest';
import { EMPTY_FILTERS } from './filters.js';
import { MAIN_FEED, categoryFeedPath, feedPathFor, feedlyUrl } from './feeds.js';

const withFilters = (patch) => ({ ...EMPTY_FILTERS(), ...patch });

describe('categoryFeedPath', () => {
  it('maps a category id to its slice and everything else to the main feed', () => {
    expect(categoryFeedPath('software_engineering')).toBe('feeds/software-engineering.xml');
    expect(categoryFeedPath('data_ml')).toBe('feeds/data-ml.xml');
    expect(categoryFeedPath('other')).toBe(MAIN_FEED);
    expect(categoryFeedPath('')).toBe(MAIN_FEED);
    expect(categoryFeedPath(null)).toBe(MAIN_FEED);
  });
});

describe('feedPathFor', () => {
  it('returns the main feed for no filters, unknown input or a mixed view', () => {
    expect(feedPathFor(EMPTY_FILTERS())).toBe(MAIN_FEED);
    expect(feedPathFor(null)).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ type: new Set(['SWE']), rmt: new Set(['remote']) }))).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ type: new Set(['SWE', 'ML']) }))).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ type: new Set(['SWE']), company: new Set(['Acme']) }))).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ type: new Set(['SWE']), newWithinHours: 24 }))).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ type: new Set(['OTHER']) }))).toBe(MAIN_FEED);
  });

  it('maps a single role, remote-only or no-restriction view to its slice', () => {
    expect(feedPathFor(withFilters({ type: new Set(['SWE']) }))).toBe('feeds/software-engineering.xml');
    expect(feedPathFor(withFilters({ type: new Set(['HEALTH']) }))).toBe('feeds/healthcare.xml');
    expect(feedPathFor(withFilters({ rmt: new Set(['remote']) }))).toBe('feeds/remote.xml');
    expect(feedPathFor(withFilters({ rmt: new Set(['hybrid']) }))).toBe(MAIN_FEED);
    expect(feedPathFor(withFilters({ visa: true }))).toBe('feeds/no-visa-restriction.xml');
    expect(feedPathFor(withFilters({ visa: false }))).toBe(MAIN_FEED);
  });
});

describe('feedlyUrl', () => {
  it('encodes the absolute feed URL', () => {
    expect(feedlyUrl('https://jobs.example.test/feeds/remote.xml'))
      .toBe('https://feedly.com/i/subscription/feed/https%3A%2F%2Fjobs.example.test%2Ffeeds%2Fremote.xml');
  });
});
