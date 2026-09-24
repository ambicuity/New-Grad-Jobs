import { describe, expect, it } from 'vitest';
import {
  DEFAULT_REPO, EMPTY_CONTRIB_FILTERS, activeThisWeek, applyGhEnrichment, avatarMonogram,
  buildGhPayload, contributorTotals, deriveAreas, deriveLangs, deriveRole, filterContributors,
  handleFromProfile, lastScore, mapContributor, mapRecentCommits, rankIn, roleColor,
  sortContributors, sparkValues,
} from './contributors.js';
import { toggleFacet } from './filters.js';
import { BBG } from './theme.js';

const OWNER_RAW = {
  login: 'ambicuity', name: 'Ritesh Rana', avatar_url: 'https://a/1', profile: 'https://github.com/ambicuity',
  contributions: ['doc', 'design', 'code', 'test'],
};
const DEV_RAW = { login: 'dev1', name: 'Dev One', profile: 'https://github.com/dev1', contributions: ['code'] };

describe('derive helpers', () => {
  it('deriveRole', () => {
    expect(deriveRole('ambicuity', [])).toBe('maintainer');
    expect(deriveRole('x', ['a', 'b', 'c'])).toBe('core');
    expect(deriveRole('x', ['a'])).toBe('contributor');
  });

  it('deriveAreas / deriveLangs dedupe and fall back', () => {
    expect(deriveAreas(['code', 'bug', 'doc'])).toEqual(['core', 'ui']);
    expect(deriveAreas(['unknown'])).toEqual(['core']);
    expect(deriveLangs(['code', 'test'])).toEqual(['Python', 'TS']);
    expect(deriveLangs([])).toEqual(['—']);
  });

  it('handleFromProfile', () => {
    expect(handleFromProfile('https://github.com/someone?tab=repos')).toBe('someone');
    expect(handleFromProfile('https://example.com/me')).toBe('example.com/me');
    expect(handleFromProfile('')).toBe('—');
  });
});

describe('mapContributor', () => {
  it('maps the owner with boosted placeholder counts', () => {
    const c = mapContributor(OWNER_RAW);
    expect(c).toMatchObject({
      handle: 'ambicuity', name: 'Ritesh Rana', role: 'maintainer', last: '1d',
      commits: 40 * 4 * 8, prs: 8 * 4 * 8, add: 900 * 32, del: 320 * 32,
      bio: 'doc · design · code · test', social: '@ambicuity', avatar: 'https://a/1',
    });
  });

  it('copes with missing fields', () => {
    const c = mapContributor({ profile: 'https://github.com/ghost' });
    expect(c).toMatchObject({ handle: 'ghost', name: '—', role: 'contributor', bio: '—', commits: 40, last: '—' });
    expect(mapContributor(null).handle).toBe('—');
  });
});

describe('applyGhEnrichment', () => {
  const list = [mapContributor(DEV_RAW), mapContributor(OWNER_RAW)];

  it('without GitHub data sorts by placeholder commits and keeps the repo', () => {
    const out = applyGhEnrichment(list, DEFAULT_REPO, null);
    expect(out.contributors.map((c) => c.handle)).toEqual(['ambicuity', 'dev1']);
    expect(out.repo).toBe(DEFAULT_REPO);
  });

  it('merges real commit counts (case-insensitive) without mutating input', () => {
    const gh = { repo: { stars: 99 }, contribs: [{ login: 'DEV1', contributions: 500 }, { login: 'ambicuity', contributions: 1 }] };
    const out = applyGhEnrichment(list, DEFAULT_REPO, gh);
    expect(out.contributors[0]).toMatchObject({ handle: 'dev1', commits: 500, prs: 100, add: 12500, del: 4000 });
    expect(out.contributors[1]).toMatchObject({ handle: 'ambicuity', commits: 1, prs: 1, add: 50, del: 20 });
    expect(out.repo.stars).toBe(99);
    expect(out.repo.name).toBe(DEFAULT_REPO.name);
    expect(list[0].commits).toBe(40);
    expect(DEFAULT_REPO.stars).toBe(0);
  });

  it('leaves contributors without GitHub stats unchanged', () => {
    const out = applyGhEnrichment(list, DEFAULT_REPO, { repo: {} });
    expect(out.contributors.find((c) => c.handle === 'dev1').commits).toBe(40);
  });
});

describe('buildGhPayload', () => {
  it('normalises the three API responses', () => {
    const out = buildGhPayload(
      { stargazers_count: 10, forks_count: 2, subscribers_count: 3, open_issues_count: 4, license: { spdx_id: 'Apache-2.0' } },
      [{ login: 'a', contributions: 5 }, { nope: true }, null],
      { total_count: 7 },
    );
    expect(out).toEqual({
      repo: { stars: 10, forks: 2, watchers: 3, issues: 4, prs_open: 7, license: 'Apache-2.0' },
      contribs: [{ login: 'a', contributions: 5 }],
    });
  });

  it('falls back to zeros / MIT', () => {
    expect(buildGhPayload(null, 'x', null)).toEqual({
      repo: { stars: 0, forks: 0, watchers: 0, issues: 0, prs_open: 0, license: 'MIT' },
      contribs: [],
    });
  });
});

describe('filter / sort / stats', () => {
  const people = [
    { handle: 'zed', name: 'Zed', region: '—', bio: 'code', role: 'core', areas: ['core'], langs: ['Python'], commits: 5, prs: 1, add: 10, del: 1, last: '2d', since: '2025' },
    { handle: 'amy', name: 'Amy', region: '—', bio: 'doc', role: 'maintainer', areas: ['ui'], langs: ['TS'], commits: 50, prs: 9, add: 100, del: 5, last: '3h', since: '2024' },
    { handle: 'bob', name: 'Bob', region: '—', bio: 'test', role: 'contributor', areas: ['ci'], langs: ['Bash'], commits: 20, prs: 4, add: 50, del: 9, last: '—', since: '2026' },
  ];
  const handles = (l) => l.map((c) => c.handle);

  it('filterContributors by role / area / lang / query', () => {
    const f = EMPTY_CONTRIB_FILTERS();
    expect(handles(filterContributors(people, f, ''))).toEqual(['zed', 'amy', 'bob']);
    expect(handles(filterContributors(people, toggleFacet(f, 'role', 'core'), ''))).toEqual(['zed']);
    expect(handles(filterContributors(people, toggleFacet(f, 'area', 'ui'), ''))).toEqual(['amy']);
    expect(handles(filterContributors(people, toggleFacet(f, 'lang', 'Bash'), ''))).toEqual(['bob']);
    expect(handles(filterContributors(people, f, 'AMY'))).toEqual(['amy']);
  });

  it('sortContributors by each key and direction', () => {
    expect(handles(sortContributors(people, 'commits', 1))).toEqual(['amy', 'bob', 'zed']);
    expect(handles(sortContributors(people, 'commits', -1))).toEqual(['zed', 'bob', 'amy']);
    expect(handles(sortContributors(people, 'prs', 1))).toEqual(['amy', 'bob', 'zed']);
    expect(handles(sortContributors(people, 'add', 1))).toEqual(['amy', 'bob', 'zed']);
    expect(handles(sortContributors(people, 'handle', 1))).toEqual(['amy', 'bob', 'zed']);
    expect(handles(sortContributors(people, 'last', 1))).toEqual(['amy', 'zed', 'bob']);
    expect(handles(sortContributors(people, 'since', 1))).toEqual(['amy', 'zed', 'bob']);
    expect(handles(sortContributors(people, 'nope', 1))).toEqual(['zed', 'amy', 'bob']);
  });

  it('lastScore converts h/d to hours', () => {
    expect(lastScore('5h')).toBe(5);
    expect(lastScore('2d')).toBe(48);
    expect(lastScore('—')).toBe(999);
    expect(lastScore(undefined)).toBe(999);
  });

  it('contributorTotals / activeThisWeek / rankIn', () => {
    expect(contributorTotals(people)).toEqual({ commits: 75, prs: 14, add: 160, del: 15 });
    expect(contributorTotals([])).toEqual({ commits: 0, prs: 0, add: 0, del: 0 });
    expect(activeThisWeek(people)).toBe(2);
    expect(rankIn(people, 'commits', people[2])).toBe(2);
  });

  it('roleColor', () => {
    expect(roleColor('maintainer')).toBe(BBG.acc);
    expect(roleColor('core')).toBe(BBG.acc2);
    expect(roleColor('contributor')).toBe(BBG.dim);
  });
});

describe('decorative helpers', () => {
  it('sparkValues is deterministic, 26 points, floored at 0.05', () => {
    const a = sparkValues('amy');
    expect(a).toHaveLength(26);
    expect(sparkValues('amy')).toEqual(a);
    expect(Math.min(...a)).toBeGreaterThanOrEqual(0.05);
    expect(sparkValues(undefined)).toEqual(sparkValues('a'));
  });

  it('avatarMonogram gives a stable hue and initials', () => {
    const m = avatarMonogram('ab-cd');
    expect(m.initials).toBe('AB');
    expect(m.hue).toBeGreaterThanOrEqual(0);
    expect(m.hue).toBeLessThan(360);
    expect(avatarMonogram('ab-cd')).toEqual(m);
    expect(avatarMonogram('')).toEqual({ hue: 0, initials: '' });
  });

  it('mapRecentCommits keeps sha7, first message line and url', () => {
    const rows = mapRecentCommits([
      { sha: '0123456789', commit: { message: 'feat: x\n\nbody', author: { date: '2026-09-24T00:00:00Z' } }, html_url: 'u' },
      {},
    ], () => '1d');
    expect(rows).toEqual([
      { sha: '0123456', msg: 'feat: x', ago: '1d', url: 'u' },
      { sha: '', msg: '', ago: '1d', url: '' },
    ]);
    expect(mapRecentCommits(null, () => '')).toEqual([]);
  });
});
