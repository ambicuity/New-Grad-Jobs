// Contributors view model: maps contributors.json (all-contributorsrc format)
// and optional GitHub API stats to the rows the contributors view renders.
// Only real data: all-contributors gives identity + contribution types, the
// GitHub API gives per-author commit counts and repo stats. Anything we don't
// know is null / empty and rendered as "—", never invented.
// Pure — enrichment returns new objects rather than mutating the input.

import { BBG } from './theme.js';
import { safeHttpUrl } from './safe-url.js';

export const PROJECT_OWNER = 'ambicuity';
export const REPO_SLUG = `${PROJECT_OWNER}/New-Grad-Jobs`;

// Handles with a GitHub Sponsors profile — mirrors `github:` in .github/FUNDING.yml.
const SPONSOR_HANDLES = new Set([PROJECT_OWNER]);

/**
 * @typedef {object} Contributor
 * @property {string} handle
 * @property {string} name
 * @property {string} profile      http(s) profile URL or ''
 * @property {string} avatar       http(s) avatar URL or ''
 * @property {'maintainer'|'core'|'contributor'} role
 * @property {string[]} types      all-contributors contribution types (code, doc, …)
 * @property {number|null} commits commits on the default branch (GitHub API), null when unknown
 * @property {string} sponsorUrl   GitHub Sponsors page, '' when the contributor has none we know of
 */

/**
 * @typedef {object} RepoInfo
 * @property {string} name
 * @property {string} desc
 * @property {number|null} stars
 * @property {number|null} forks
 * @property {number|null} issues   open issues + PRs (GitHub's open_issues_count)
 * @property {number|null} prs_open
 * @property {[string, number][]} langs  [language, % of bytes], from /languages
 * @property {string} license
 */

/**
 * Repo card before (or without) the GitHub API: counts unknown.
 * @type {RepoInfo}
 */
export const DEFAULT_REPO = Object.freeze({
  name: REPO_SLUG,
  desc: 'open-source new-grad job board · scrapes company careers APIs (greenhouse, lever, ashby, workday, jobspy) and publishes a live feed.',
  stars: null, forks: null, issues: null, prs_open: null,
  langs: [],
  license: 'MIT',
});

const uniq = (xs) => [...new Set(xs)];

export function deriveRole(login, contributions) {
  if (login === PROJECT_OWNER) return 'maintainer';
  if (contributions.length >= 3) return 'core';
  return 'contributor';
}

export function handleFromProfile(profile) {
  if (!profile) return '—';
  const m = /github\.com\/([^/?#]+)/i.exec(profile);
  return m ? m[1] : profile.replace(/^https?:\/\//, '');
}

export function sponsorUrlFor(handle) {
  return SPONSOR_HANDLES.has(handle) ? `https://github.com/sponsors/${encodeURIComponent(handle)}` : '';
}

/** @returns {Contributor} */
export function mapContributor(raw) {
  const r = raw || {};
  const types = uniq((Array.isArray(r.contributions) ? r.contributions : []).filter((t) => typeof t === 'string'));
  const handle = r.login || handleFromProfile(r.profile);
  return {
    handle,
    name: r.name || r.login || '—',
    profile: safeHttpUrl(r.profile),
    avatar: safeHttpUrl(r.avatar_url),
    role: deriveRole(r.login, types),
    types,
    commits: null,
    sponsorUrl: sponsorUrlFor(handle),
  };
}

const commitsOrMinus = (c) => (typeof c.commits === 'number' ? c.commits : -1);
export const byCommitsDesc = (a, b) => commitsOrMinus(b) - commitsOrMinus(a);

/**
 * Merge GitHub stats into the contributor list + repo card. Contributors the
 * API doesn't list (e.g. docs-only, or beyond the first 100) keep commits null.
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
    return typeof real === 'number' ? { ...p, commits: real } : p;
  });
  return { contributors: enriched.sort(byCommitsDesc), repo: { ...repo, ...gh.repo } };
}

const LANG_TOP = 4;

/**
 * GitHub /languages ({name: bytes}) → [[name, percent]] (top 4 + "Other"),
 * percentages to one decimal. Empty for missing/malformed input.
 */
export function languageShares(langsJson) {
  if (!langsJson || typeof langsJson !== 'object' || Array.isArray(langsJson)) return [];
  const entries = Object.entries(langsJson)
    .filter(([, bytes]) => typeof bytes === 'number' && bytes > 0)
    .sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, b]) => s + b, 0);
  if (!total) return [];
  const pct = (bytes) => Math.round((bytes / total) * 1000) / 10;
  const top = entries.slice(0, LANG_TOP).map(([name, bytes]) => [name, pct(bytes)]);
  const rest = entries.slice(LANG_TOP).reduce((s, [, b]) => s + b, 0);
  return rest ? [...top, ['Other', pct(rest)]] : top;
}

const numOrNull = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null);

/** Normalise the GitHub API responses into the enrichment payload. */
export function buildGhPayload(repoJson, contribsJson, prsJson, langsJson) {
  const repo = repoJson || {};
  const repoOut = {
    stars: numOrNull(repo.stargazers_count),
    forks: numOrNull(repo.forks_count),
    issues: numOrNull(repo.open_issues_count),
    prs_open: numOrNull(prsJson && prsJson.total_count),
  };
  if (repo.license && typeof repo.license.spdx_id === 'string') repoOut.license = repo.license.spdx_id;
  const langs = languageShares(langsJson);
  if (langs.length) repoOut.langs = langs;
  return {
    repo: repoOut,
    contribs: (Array.isArray(contribsJson) ? contribsJson : [])
      .filter((c) => c && typeof c.login === 'string' && typeof c.contributions === 'number')
      .map((c) => ({ login: c.login, contributions: c.contributions })),
  };
}

/** True when `data` looks like a buildGhPayload() result (for cache validation). */
export function isGhPayload(data) {
  return Boolean(data) && typeof data === 'object'
    && Boolean(data.repo) && typeof data.repo === 'object' && !Array.isArray(data.repo)
    && Array.isArray(data.contribs)
    && data.contribs.every((c) => c && typeof c.login === 'string' && typeof c.contributions === 'number')
    && (data.repo.langs === undefined || (Array.isArray(data.repo.langs)
      && data.repo.langs.every((l) => Array.isArray(l) && typeof l[0] === 'string' && typeof l[1] === 'number')));
}

/**
 * @typedef {object} ContribFilters
 * @property {Set<string>} role
 * @property {Set<string>} type
 */

/** @returns {ContribFilters} */
export function EMPTY_CONTRIB_FILTERS() {
  return { role: new Set(), type: new Set() };
}

const ROLE_ORDER = ['maintainer', 'core', 'contributor'];

/** Filter chip options present in the data (roles in rank order, types by frequency). */
export function facetOptions(list) {
  const counts = new Map();
  list.forEach((c) => c.types.forEach((t) => counts.set(t, (counts.get(t) || 0) + 1)));
  const roles = ROLE_ORDER.filter((r) => list.some((c) => c.role === r));
  const types = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([t]) => t);
  return { roles, types };
}

export function filterContributors(list, filters, q) {
  const needle = (q || '').toLowerCase();
  return list.filter((c) => {
    if (filters.role.size && !filters.role.has(c.role)) return false;
    if (filters.type.size && !c.types.some((t) => filters.type.has(t))) return false;
    if (!needle) return true;
    const hay = `${c.handle} ${c.name} ${c.role} ${c.types.join(' ')}`.toLowerCase();
    return hay.includes(needle);
  });
}

/** Sorted copy; `dir` 1 = natural order (most commits first, A→Z). Unknown commits sort last. */
export function sortContributors(list, key, dir) {
  const out = list.slice();
  const cmp = {
    commits: byCommitsDesc,
    handle: (a, b) => a.handle.localeCompare(b.handle),
  }[key];
  return cmp ? out.sort((a, b) => dir * cmp(a, b)) : out;
}

/** Sum of known commit counts, and how many contributors have one. */
export function contributorTotals(list) {
  return list.reduce(
    (t, c) => (typeof c.commits === 'number' ? { commits: t.commits + c.commits, known: t.known + 1 } : t),
    { commits: 0, known: 0 },
  );
}

/** 1-based rank of `c` by commits among contributors with a known count, or null. */
export function commitRank(list, c) {
  if (!c || typeof c.commits !== 'number') return null;
  return list.filter((x) => typeof x.commits === 'number' && x.commits > c.commits).length + 1;
}

export function roleColor(role) {
  if (role === 'maintainer') return BBG.acc;
  if (role === 'core') return BBG.acc2;
  return BBG.dim;
}

const LANG_COLOR = {
  Python: BBG.acc2, JavaScript: BBG.warn, TypeScript: '#62a3ff', HTML: BBG.acc, CSS: '#c084fc',
  Shell: BBG.ok, Makefile: '#ff5a9d', Other: BBG.dim,
};
export const langColor = (lang) => LANG_COLOR[lang] || BBG.acc;

/** Hue (0-359) + two-letter monogram for the pseudo-avatar. */
export function avatarMonogram(handle) {
  const h = Array.from(handle || '').reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 0);
  return { hue: h % 360, initials: (handle || '').replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase() };
}

const SHA_RE = /^[0-9a-f]{7,40}$/i;

/**
 * Map a GitHub /commits response to the RECENT COMMITS rows. `date` is kept
 * raw (ISO) so "ago" is computed at render time, not frozen into the cache.
 * @returns {{sha: string, msg: string, date: string, url: string}[]}
 */
export function mapRecentCommits(data) {
  return (Array.isArray(data) ? data : [])
    .filter((d) => d && typeof d.sha === 'string' && SHA_RE.test(d.sha))
    .map((d) => ({
      sha: d.sha.slice(0, 7),
      msg: String((d.commit && d.commit.message) || '').split('\n')[0].slice(0, 80),
      date: String((d.commit && d.commit.author && d.commit.author.date) || ''),
      url: safeHttpUrl(d.html_url) || `https://github.com/${REPO_SLUG}/commit/${d.sha}`,
    }));
}

/** True when `rows` has the shape mapRecentCommits() produces (cache validation). */
export function isRecentCommitRows(rows) {
  return Array.isArray(rows) && rows.every((r) => r && typeof r === 'object'
    && typeof r.sha === 'string' && SHA_RE.test(r.sha) && typeof r.msg === 'string'
    && typeof r.date === 'string' && typeof r.url === 'string' && (r.url === '' || safeHttpUrl(r.url) === r.url));
}
