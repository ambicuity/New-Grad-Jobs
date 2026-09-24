import { describe, expect, it } from 'vitest';
import {
  DEFAULT_REPO, EMPTY_CONTRIB_FILTERS, applyGhEnrichment, avatarMonogram, buildGhPayload, commitRank,
  contributorTotals, deriveRole, facetOptions, filterContributors, handleFromProfile, isGhPayload,
  isRecentCommitRows, langColor, languageShares, mapContributor, mapRecentCommits, roleColor,
  sortContributors, sponsorUrlFor,
} from './contributors.js';
import { toggleFacet } from './filters.js';
import { BBG } from './theme.js';

const OWNER_RAW = {
  login: 'ambicuity', name: 'Ritesh Rana', avatar_url: 'https://a.example/1', profile: 'https://github.com/ambicuity',
  contributions: ['doc', 'design', 'code', 'test'],
};
const DEV_RAW = { login: 'dev1', name: 'Dev One', profile: 'https://github.com/dev1', contributions: ['code'] };

describe('derive helpers', () => {
  it('deriveRole', () => {
    expect(deriveRole('ambicuity', [])).toBe('maintainer');
    expect(deriveRole('x', ['a', 'b', 'c'])).toBe('core');
    expect(deriveRole('x', ['a'])).toBe('contributor');
  });

  it('handleFromProfile', () => {
    expect(handleFromProfile('https://github.com/someone?tab=repos')).toBe('someone');
    expect(handleFromProfile('https://example.com/me')).toBe('example.com/me');
    expect(handleFromProfile('')).toBe('—');
  });

  it('sponsorUrlFor only knows FUNDING.yml handles', () => {
    expect(sponsorUrlFor('ambicuity')).toBe('https://github.com/sponsors/ambicuity');
    expect(sponsorUrlFor('dev1')).toBe('');
  });
});

describe('mapContributor', () => {
  it('maps only real fields; commits unknown until GitHub stats arrive', () => {
    expect(mapContributor(OWNER_RAW)).toEqual({
      handle: 'ambicuity', name: 'Ritesh Rana', profile: 'https://github.com/ambicuity', avatar: 'https://a.example/1',
      role: 'maintainer', types: ['doc', 'design', 'code', 'test'], commits: null,
      sponsorUrl: 'https://github.com/sponsors/ambicuity',
    });
  });

  it('copes with missing fields and drops unsafe URLs', () => {
    const c = mapContributor({ profile: 'https://github.com/ghost', avatar_url: 'javascript:alert(1)', contributions: ['code', 'code', 3] });
    expect(c).toMatchObject({ handle: 'ghost', name: '—', role: 'contributor', types: ['code'], avatar: '', sponsorUrl: '' });
    expect(mapContributor({ login: 'x', profile: 'javascript:alert(1)' }).profile).toBe('');
    expect(mapContributor(null).handle).toBe('—');
  });
});

describe('GitHub enrichment', () => {
  const list = [mapContributor(DEV_RAW), mapContributor(OWNER_RAW)];

  it('without GitHub data keeps commits unknown and the default repo', () => {
    const out = applyGhEnrichment(list, DEFAULT_REPO, null);
    expect(out.contributors.every((c) => c.commits === null)).toBe(true);
    expect(out.repo).toBe(DEFAULT_REPO);
    expect(DEFAULT_REPO.langs).toEqual([]);
    expect(DEFAULT_REPO.stars).toBeNull();
  });

  it('applies real commit counts and sorts unknowns last', () => {
    const gh = buildGhPayload({ stargazers_count: 5 }, [{ login: 'DEV1', contributions: 12 }], { total_count: 2 }, { Python: 90, JavaScript: 10 });
    const out = applyGhEnrichment(list, DEFAULT_REPO, gh);
    expect(out.contributors.map((c) => [c.handle, c.commits])).toEqual([['dev1', 12], ['ambicuity', null]]);
    expect(out.repo).toMatchObject({ name: DEFAULT_REPO.name, stars: 5, prs_open: 2, langs: [['Python', 90], ['JavaScript', 10]] });
    expect(list[0].commits).toBeNull(); // input not mutated
  });

  it('buildGhPayload tolerates garbage', () => {
    expect(buildGhPayload(null, 'x', null, null)).toEqual({
      repo: { stars: null, forks: null, issues: null, prs_open: null }, contribs: [],
    });
    expect(buildGhPayload({ license: { spdx_id: 'MIT' } }, [{ login: 'a' }, null], null, null).repo.license).toBe('MIT');
  });

  it('languageShares: top 4 + Other, one decimal', () => {
    expect(languageShares({ A: 50, B: 20, C: 10, D: 10, E: 5, F: 5 }))
      .toEqual([['A', 50], ['B', 20], ['C', 10], ['D', 10], ['Other', 10]]);
    expect(languageShares({ Python: 592910, JavaScript: 3949, Makefile: 1809 }))
      .toEqual([['Python', 99.0], ['JavaScript', 0.7], ['Makefile', 0.3]]);
    expect(languageShares(null)).toEqual([]);
    expect(languageShares([])).toEqual([]);
    expect(languageShares({ A: 0, B: 'x' })).toEqual([]);
  });

  it('isGhPayload validates cached shape', () => {
    expect(isGhPayload(buildGhPayload({}, [{ login: 'a', contributions: 1 }], null, { Py: 1 }))).toBe(true);
    expect(isGhPayload({ repo: {}, contribs: [{ login: 1 }] })).toBe(false);
    expect(isGhPayload({ repo: [], contribs: [] })).toBe(false);
    expect(isGhPayload({ repo: { langs: 'x' }, contribs: [] })).toBe(false);
    expect(isGhPayload(null)).toBe(false);
  });
});

describe('filter / sort / stats', () => {
  const people = [
    { handle: 'zed', name: 'Zed', role: 'core', types: ['code', 'test'], commits: 5 },
    { handle: 'amy', name: 'Amy', role: 'maintainer', types: ['doc'], commits: 50 },
    { handle: 'bob', name: 'Bob', role: 'contributor', types: ['code'], commits: null },
  ];
  const handles = (l) => l.map((c) => c.handle);

  it('facetOptions derives chips from the data', () => {
    expect(facetOptions(people)).toEqual({ roles: ['maintainer', 'core', 'contributor'], types: ['code', 'doc', 'test'] });
    expect(facetOptions([])).toEqual({ roles: [], types: [] });
  });

  it('filterContributors by role / type / query', () => {
    const f = EMPTY_CONTRIB_FILTERS();
    expect(handles(filterContributors(people, f, ''))).toEqual(['zed', 'amy', 'bob']);
    expect(handles(filterContributors(people, toggleFacet(f, 'role', 'core'), ''))).toEqual(['zed']);
    expect(handles(filterContributors(people, toggleFacet(f, 'type', 'code'), ''))).toEqual(['zed', 'bob']);
    expect(handles(filterContributors(people, f, 'AMY'))).toEqual(['amy']);
    expect(handles(filterContributors(people, f, 'test'))).toEqual(['zed']);
  });

  it('sortContributors by commits (unknown last) and handle', () => {
    expect(handles(sortContributors(people, 'commits', 1))).toEqual(['amy', 'zed', 'bob']);
    expect(handles(sortContributors(people, 'commits', -1))).toEqual(['bob', 'zed', 'amy']);
    expect(handles(sortContributors(people, 'handle', 1))).toEqual(['amy', 'bob', 'zed']);
    expect(handles(sortContributors(people, 'nope', 1))).toEqual(['zed', 'amy', 'bob']);
  });

  it('contributorTotals / commitRank ignore unknown counts', () => {
    expect(contributorTotals(people)).toEqual({ commits: 55, known: 2 });
    expect(contributorTotals([])).toEqual({ commits: 0, known: 0 });
    expect(commitRank(people, people[0])).toBe(2);
    expect(commitRank(people, people[1])).toBe(1);
    expect(commitRank(people, people[2])).toBeNull();
    expect(commitRank(people, null)).toBeNull();
  });

  it('roleColor / langColor', () => {
    expect(roleColor('maintainer')).toBe(BBG.acc);
    expect(roleColor('core')).toBe(BBG.acc2);
    expect(roleColor('contributor')).toBe(BBG.dim);
    expect(langColor('Other')).toBe(BBG.dim);
    expect(langColor('Brainfuck')).toBe(BBG.acc);
  });
});

describe('avatars and commits', () => {
  it('avatarMonogram gives a stable hue and initials', () => {
    const m = avatarMonogram('ab-cd');
    expect(m.initials).toBe('AB');
    expect(m.hue).toBeGreaterThanOrEqual(0);
    expect(m.hue).toBeLessThan(360);
    expect(avatarMonogram('ab-cd')).toEqual(m);
    expect(avatarMonogram('')).toEqual({ hue: 0, initials: '' });
  });

  it('mapRecentCommits keeps sha7, first line, raw date and a safe url', () => {
    const rows = mapRecentCommits([
      { sha: '0123456789abcdef', commit: { message: 'feat: x\n\nbody', author: { date: '2026-09-24T00:00:00Z' } }, html_url: 'https://github.com/o/r/commit/0123456' },
      { sha: 'abcdef0123', commit: { message: 'y' }, html_url: 'javascript:alert(1)' },
      { sha: 'not-a-sha' },
      {},
    ]);
    expect(rows).toEqual([
      { sha: '0123456', msg: 'feat: x', date: '2026-09-24T00:00:00Z', url: 'https://github.com/o/r/commit/0123456' },
      { sha: 'abcdef0', msg: 'y', date: '', url: 'https://github.com/ambicuity/New-Grad-Jobs/commit/abcdef0123' },
    ]);
    expect(mapRecentCommits(null)).toEqual([]);
    expect(isRecentCommitRows(rows)).toBe(true);
  });

  it('isRecentCommitRows rejects malformed cache data', () => {
    expect(isRecentCommitRows([])).toBe(true);
    expect(isRecentCommitRows(null)).toBe(false);
    expect(isRecentCommitRows([{ sha: 'zzz', msg: '', date: '', url: '' }])).toBe(false);
    expect(isRecentCommitRows([{ sha: 'abcdef0', msg: 'm', date: '', url: 'javascript:alert(1)' }])).toBe(false);
    expect(isRecentCommitRows([{ sha: 'abcdef0', msg: 1, date: '', url: '' }])).toBe(false);
  });
});
