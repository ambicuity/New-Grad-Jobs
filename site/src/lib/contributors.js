// Contributors view model: maps contributors.json (all-contributorsrc format)
// and optional GitHub API stats to the rows the contributors view renders.
// Pure — enrichment returns new objects rather than mutating the input.

import { BBG } from './theme.js';

export const PROJECT_OWNER = 'ambicuity';
export const REPO_SLUG = `${PROJECT_OWNER}/New-Grad-Jobs`;

/**
 * @typedef {object} Contributor
 * @property {string} handle
 * @property {string} name
 * @property {string} profile
 * @property {string} avatar
 * @property {'maintainer'|'core'|'contributor'} role
 * @property {string} region
 * @property {number} commits
 * @property {number} prs
 * @property {number} add
 * @property {number} del
 * @property {string} since
 * @property {string} last
 * @property {string[]} langs
 * @property {string[]} areas
 * @property {string} bio
 * @property {string} social
 */

/**
 * @typedef {object} RepoInfo
 * @property {string} name
 * @property {string} desc
 * @property {number} stars
 * @property {number} forks
 * @property {number} watchers
 * @property {number} issues
 * @property {number} prs_open
 * @property {[string, number][]} langs
 * @property {string} license
 * @property {string} default_branch
 * @property {string} release
 * @property {string} released
 */

/**
 * Repo card defaults. Live stars/forks/issues/PRs come from the GitHub API
 * (see applyGhEnrichment); these are the fallbacks when it is unavailable.
 * @type {RepoInfo}
 */
export const DEFAULT_REPO = Object.freeze({
  name: REPO_SLUG,
  desc: 'open-source new-grad job board · scrapes ~200 careers pages (greenhouse, lever, workday, jobspy) and publishes a live feed.',
  stars: 0, forks: 0, watchers: 0, issues: 0, prs_open: 0,
  langs: [['Python', 78], ['TS', 14], ['JS', 6], ['Other', 2]],
  license: 'MIT', default_branch: 'main', release: 'rolling', released: 'live',
});

// all-contributors contribution type → the design's `area` taxonomy.
const CONTRIB_AREA = {
  code: 'core', bug: 'core', ideas: 'core', maintenance: 'core', review: 'core',
  doc: 'ui', design: 'ui', test: 'ci', infra: 'infra', tool: 'cli',
  platform: 'infra', data: 'data', research: 'ml',
};

// Languages associated with each contribution type, in this repo.
const CONTRIB_LANGS = {
  code: ['Python', 'TS'], bug: ['Python'], maintenance: ['Python'], doc: ['Markdown'],
  design: ['TS'], test: ['Python'], infra: ['YAML', 'Bash'], tool: ['Bash'],
};

const uniq = (xs) => [...new Set(xs)];

export function deriveRole(login, contributions) {
  if (login === PROJECT_OWNER) return 'maintainer';
  if (contributions.length >= 3) return 'core';
  return 'contributor';
}

export function deriveAreas(contributions) {
  const out = uniq(contributions.map((c) => CONTRIB_AREA[c]).filter(Boolean));
  return out.length ? out : ['core'];
}

export function deriveLangs(contributions) {
  const out = uniq(contributions.flatMap((c) => CONTRIB_LANGS[c] || []));
  return out.length ? out : ['—'];
}

export function handleFromProfile(profile) {
  if (!profile) return '—';
  const m = /github\.com\/([^/?#]+)/i.exec(profile);
  return m ? m[1] : profile.replace(/^https?:\/\//, '');
}

// Placeholder counters — all-contributorsrc has no commit/PR/LoC totals.
// Scale by contribution-type count so the leaderboard has a meaningful
// relative ordering until real GitHub counts arrive.
function deriveCounts(contributions, isOwner) {
  const k = contributions.length || 1;
  const boost = isOwner ? 8 : 1;
  return { commits: 40 * k * boost, prs: 8 * k * boost, add: 900 * k * boost, del: 320 * k * boost };
}

/** @returns {Contributor} */
export function mapContributor(raw) {
  const r = raw || {};
  const contributions = Array.isArray(r.contributions) ? r.contributions : [];
  const isOwner = r.login === PROJECT_OWNER;
  const handle = r.login || handleFromProfile(r.profile);
  return {
    handle,
    name: r.name || r.login || '—',
    profile: r.profile || '',
    avatar: r.avatar_url || '',
    role: deriveRole(r.login, contributions),
    region: '—',
    ...deriveCounts(contributions, isOwner),
    since: '2025',
    last: isOwner ? '1d' : '—',
    langs: deriveLangs(contributions),
    areas: deriveAreas(contributions),
    bio: contributions.length ? contributions.join(' · ') : '—',
    social: '@' + handle,
  };
}

export const byCommitsDesc = (a, b) => b.commits - a.commits;

/**
 * Merge GitHub stats into the contributor list + repo card. Commits are real;
 * PRs / LoC are derived from commits (~20% PRs, ~25 LoC added and ~8 deleted
 * per commit) since GitHub's per-author LoC endpoint is async and unreliable.
 * @param {Contributor[]} contributors
 * @param {RepoInfo} repo
 * @param {{repo: Partial<RepoInfo>, contribs: {login: string, contributions: number}[]}|null} gh
 * @returns {{contributors: Contributor[], repo: RepoInfo}}
 */
export function applyGhEnrichment(contributors, repo, gh) {
  if (!gh) return { contributors: [...contributors].sort(byCommitsDesc), repo };
  const byLogin = new Map((gh.contribs || []).map((c) => [c.login.toLowerCase(), c.contributions]));
  const enriched = contributors.map((p) => {
    const real = byLogin.get(p.handle.toLowerCase());
    if (real == null) return p;
    return {
      ...p,
      commits: real,
      prs: Math.max(1, Math.round(real * 0.2)),
      add: Math.max(50, real * 25),
      del: Math.max(20, real * 8),
    };
  });
  return { contributors: enriched.sort(byCommitsDesc), repo: { ...repo, ...gh.repo } };
}

/** Normalise the three GitHub API responses into the enrichment payload. */
export function buildGhPayload(repoJson, contribsJson, prsJson) {
  const repo = repoJson || {};
  const prs = prsJson || { total_count: 0 };
  return {
    repo: {
      stars: repo.stargazers_count ?? 0,
      forks: repo.forks_count ?? 0,
      watchers: repo.subscribers_count ?? 0,
      issues: repo.open_issues_count ?? 0,
      prs_open: prs.total_count ?? 0,
      license: (repo.license && repo.license.spdx_id) || 'MIT',
    },
    contribs: (Array.isArray(contribsJson) ? contribsJson : [])
      .filter((c) => c && typeof c.login === 'string')
      .map((c) => ({ login: c.login, contributions: c.contributions })),
  };
}

/**
 * @typedef {object} ContribFilters
 * @property {Set<string>} role
 * @property {Set<string>} area
 * @property {Set<string>} lang
 */

/** @returns {ContribFilters} */
export function EMPTY_CONTRIB_FILTERS() {
  return { role: new Set(), area: new Set(), lang: new Set() };
}

export function filterContributors(list, filters, q) {
  const needle = (q || '').toLowerCase();
  return list.filter((c) => {
    if (filters.role.size && !filters.role.has(c.role)) return false;
    if (filters.area.size && !c.areas.some((a) => filters.area.has(a))) return false;
    if (filters.lang.size && !c.langs.some((l) => filters.lang.has(l))) return false;
    if (!needle) return true;
    const hay = `${c.handle} ${c.name} ${c.region} ${c.bio} ${c.langs.join(' ')} ${c.areas.join(' ')}`.toLowerCase();
    return hay.includes(needle);
  });
}

/** "5h" / "2d" → hours for recency sort (smaller = more recent; unknown = 999). */
export function lastScore(s) {
  const m = /^(\d+)(h|d)/.exec(s || '');
  if (!m) return 999;
  return parseInt(m[1], 10) * (m[2] === 'h' ? 1 : 24);
}

/** Sorted copy; `dir` 1 = natural order (most commits/PRs/LoC, A→Z, most recent). */
export function sortContributors(list, key, dir) {
  const out = list.slice();
  const cmp = {
    commits: (a, b) => b.commits - a.commits,
    prs: (a, b) => b.prs - a.prs,
    add: (a, b) => b.add - a.add,
    handle: (a, b) => a.handle.localeCompare(b.handle),
    last: (a, b) => lastScore(a.last) - lastScore(b.last),
    since: (a, b) => a.since.localeCompare(b.since),
  }[key];
  return cmp ? out.sort((a, b) => dir * cmp(a, b)) : out;
}

export function contributorTotals(list) {
  return list.reduce(
    (t, c) => ({ commits: t.commits + c.commits, prs: t.prs + c.prs, add: t.add + c.add, del: t.del + c.del }),
    { commits: 0, prs: 0, add: 0, del: 0 },
  );
}

/** Contributors whose last commit reads as within ~2 days ("5h", "1d", "2d"). */
export function activeThisWeek(list) {
  return list.filter((c) => /h$|^1d|^2d/.test(c.last)).length;
}

/** 1-based rank of `c` in `list` by `key` (descending). */
export function rankIn(list, key, c) {
  const sorted = [...list].sort((a, b) => b[key] - a[key]);
  return sorted.findIndex((x) => x.handle === c.handle) + 1;
}

export function roleColor(role) {
  if (role === 'maintainer') return BBG.acc;
  if (role === 'core') return BBG.acc2;
  return BBG.dim;
}

/** Deterministic 26-week activity curve seeded by the handle (decorative). */
export function sparkValues(handle) {
  const seed = (handle || 'a').charCodeAt(0);
  return Array.from({ length: 26 }, (_, i) => {
    const v = (Math.sin(seed + i * 0.7) + Math.sin(seed * 0.3 + i * 1.3) + 2) / 4;
    return Math.max(0.05, v + (i / 40));
  });
}

/** Hue (0-359) + two-letter monogram for the pseudo-avatar. */
export function avatarMonogram(handle) {
  const h = Array.from(handle || '').reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 0);
  return { hue: h % 360, initials: (handle || '').replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase() };
}

/** Map a GitHub /commits response to the RECENT COMMITS rows. */
export function mapRecentCommits(data, formatAgo) {
  return (Array.isArray(data) ? data : []).map((d) => ({
    sha: (d.sha || '').slice(0, 7),
    msg: ((d.commit && d.commit.message) || '').split('\n')[0].slice(0, 80),
    ago: formatAgo(d.commit && d.commit.author && d.commit.author.date),
    url: d.html_url || '',
  }));
}
