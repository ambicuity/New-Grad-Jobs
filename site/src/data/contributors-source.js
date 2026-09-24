// Loads contributors.json and enriches it with GitHub API stats: one
// unauthenticated /repos call (stars / forks / issues), /contributors (real
// per-author commit counts) and a search for open PRs. Cached in localStorage
// for an hour to stay polite under the 60 req/hr/IP limit.

import {
  DEFAULT_REPO, REPO_SLUG, applyGhEnrichment, buildGhPayload, mapContributor,
} from '../lib/contributors.js';

export const CONTRIBUTORS_URL = './contributors.json';
const GH_API = 'https://api.github.com';
const GH_TTL_MS = 60 * 60 * 1000;
const CACHE_KEY = 'ng-terminal:gh-v1';
// A slow or hanging api.github.com must not keep the contributors view on its
// loading state forever — give up and fall back to placeholders after this.
export const GH_TIMEOUT_MS = 6000;

function storage() {
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null;
  } catch {
    return null;
  }
}

export function readGhCache(store = storage(), now = Date.now()) {
  try {
    const raw = store && store.getItem(CACHE_KEY);
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj || now - obj.t > GH_TTL_MS) return null;
    return obj.data;
  } catch {
    return null;
  }
}

export function writeGhCache(data, store = storage(), now = Date.now()) {
  try {
    if (store) store.setItem(CACHE_KEY, JSON.stringify({ t: now, data }));
  } catch (err) {
    console.warn('[terminal] could not cache github stats:', err && err.message);
  }
}

export async function fetchGitHubMeta(fetchImpl = fetch, timeoutMs = GH_TIMEOUT_MS) {
  const cached = readGhCache();
  if (cached) return cached;
  const ctrl = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
  const opts = { headers: { Accept: 'application/vnd.github+json' }, signal: ctrl ? ctrl.signal : undefined };
  try {
    const [repoRes, contribRes, prsRes] = await Promise.all([
      fetchImpl(`${GH_API}/repos/${REPO_SLUG}`, opts),
      fetchImpl(`${GH_API}/repos/${REPO_SLUG}/contributors?per_page=100`, opts),
      fetchImpl(`${GH_API}/search/issues?q=repo:${REPO_SLUG}+type:pr+state:open&per_page=1`, opts),
    ]);
    if (!repoRes.ok || !contribRes.ok) {
      console.warn('[terminal] github api unavailable, falling back to placeholders');
      return null;
    }
    const data = buildGhPayload(
      await repoRes.json(),
      await contribRes.json(),
      prsRes.ok ? await prsRes.json() : null,
    );
    writeGhCache(data);
    return data;
  } catch (err) {
    console.warn('[terminal] github api fetch failed:', err && err.message);
    return null;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

/**
 * @typedef {object} ContributorsState
 * @property {import('../lib/contributors.js').Contributor[]} contributors
 * @property {import('../lib/contributors.js').RepoInfo} repo
 */

/**
 * Never rejects: on failure resolves with an empty roster and the default repo card.
 * @returns {Promise<ContributorsState>}
 */
export async function loadContributors(fetchImpl = fetch) {
  try {
    const r = await fetchImpl(CONTRIBUTORS_URL, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`contributors.json: HTTP ${r.status}`);
    const d = await r.json();
    const list = ((d && d.contributors) || []).map(mapContributor);
    const gh = await fetchGitHubMeta(fetchImpl);
    return applyGhEnrichment(list, DEFAULT_REPO, gh);
  } catch (err) {
    console.error('[terminal] failed to load contributors.json:', err);
    return { contributors: [], repo: DEFAULT_REPO };
  }
}
