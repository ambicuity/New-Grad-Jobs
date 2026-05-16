// Real-data adapter for the contributors view.
// Loads docs/contributors.json (all-contributorsrc format) and maps to
// the shape that contributors.jsx expects.
//
// Exposes on window: NGCONTRIB, NGREPO, AREA_COLOR, NGCONTRIB_READY.

// Palette preserved from the design verbatim.
const AREA_COLOR = {
  core:'#62a3ff', api:'#ff9d3d', ui:'#5fd28a', infra:'#e8c443', scrape:'#c084fc',
  dedup:'#c084fc', cli:'#62a3ff', db:'#ff9d3d', ml:'#ff5a9d', data:'#5fd28a', ci:'#e8c443', search:'#ff9d3d',
};

// Repo card metadata. Static — the live values (stars/forks) would require a
// GitHub API call. Counts below reflect the project at a point in time.
const NGREPO = {
  name:'ambicuity/New-Grad-Jobs',
  desc:'open-source new-grad job board · scrapes ~200 careers pages (greenhouse, lever, workday, jobspy) and publishes a live feed.',
  stars: 0, forks: 0, watchers: 0, issues: 0, prs_open: 0,
  langs: [['Python', 78], ['TS', 14], ['JS', 6], ['Other', 2]],
  license:'MIT', default_branch:'main', release:'rolling', released:'live',
};

// ── Mapping helpers ──────────────────────────────────────────────────────

const PROJECT_OWNER = 'ambicuity';

// Map all-contributors contribution types to the design's `area` taxonomy.
const CONTRIB_AREA = {
  code:        'core',
  bug:         'core',
  ideas:       'core',
  maintenance: 'core',
  review:      'core',
  doc:         'ui',
  design:      'ui',
  test:        'ci',
  infra:       'infra',
  tool:        'cli',
  platform:    'infra',
  data:        'data',
  research:    'ml',
};

// Languages associated with each contribution type, in this repo.
const CONTRIB_LANGS = {
  code:        ['Python', 'TS'],
  bug:         ['Python'],
  maintenance: ['Python'],
  doc:         ['Markdown'],
  design:      ['TS'],
  test:        ['Python'],
  infra:       ['YAML', 'Bash'],
  tool:        ['Bash'],
};

function uniq(xs) { return [...new Set(xs)]; }

function deriveRole(login, contributions) {
  if (login === PROJECT_OWNER) return 'maintainer';
  if (contributions.length >= 3) return 'core';
  return 'contributor';
}

function deriveAreas(contributions) {
  const out = uniq(contributions.map(c => CONTRIB_AREA[c]).filter(Boolean));
  return out.length ? out : ['core'];
}

function deriveLangs(contributions) {
  const out = uniq(contributions.flatMap(c => CONTRIB_LANGS[c] || []));
  return out.length ? out : ['—'];
}

function deriveBio(contributions) {
  if (!contributions.length) return '—';
  return contributions.join(' · ');
}

function handleFromProfile(profile) {
  if (!profile) return '—';
  const m = /github\.com\/([^/?#]+)/i.exec(profile);
  return m ? m[1] : profile.replace(/^https?:\/\//, '');
}

// Placeholder counters — the all-contributorsrc format doesn't include
// commit/PR/LoC totals. Scale by contribution-type count so the leaderboard
// has a meaningful relative ordering (more roles ≈ more involvement).
function deriveCounts(contributions, isOwner) {
  const k = contributions.length || 1;
  const ownerBoost = isOwner ? 8 : 1;
  return {
    commits: 40 * k * ownerBoost,
    prs:     8  * k * ownerBoost,
    add:     900 * k * ownerBoost,
    del:     320 * k * ownerBoost,
  };
}

function mapContributor(raw) {
  const contributions = Array.isArray(raw.contributions) ? raw.contributions : [];
  const isOwner = raw.login === PROJECT_OWNER;
  const counts  = deriveCounts(contributions, isOwner);
  const handle  = raw.login || handleFromProfile(raw.profile);
  return {
    handle,
    name:    raw.name || raw.login || '—',
    profile: raw.profile || '',
    avatar:  raw.avatar_url || '',
    role:    deriveRole(raw.login, contributions),
    region:  '—',
    commits: counts.commits,
    prs:     counts.prs,
    add:     counts.add,
    del:     counts.del,
    since:   '2025',
    last:    isOwner ? '1d' : '—',
    langs:   deriveLangs(contributions),
    areas:   deriveAreas(contributions),
    bio:     deriveBio(contributions),
    social:  '@' + handle,
  };
}

// ── GitHub API enrichment ────────────────────────────────────────────────
// One unauthenticated `/repos/:owner/:repo` call (real stars / forks / issues
// / open PRs) and one `/repos/:owner/:repo/contributors` call (real per-
// contributor commit counts so the leaderboard is meaningful). Cached in
// localStorage for an hour to stay polite under the 60 req/hr/IP limit.

const GH_API   = 'https://api.github.com';
const GH_REPO  = `${PROJECT_OWNER}/New-Grad-Jobs`;
const GH_TTL   = 60 * 60 * 1000;  // 1h
const CACHE_KEY = 'ng-terminal:gh-v1';

function readGhCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj || Date.now() - obj.t > GH_TTL) return null;
    return obj.data;
  } catch { return null; }
}

function writeGhCache(data) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), data })); } catch {}
}

async function fetchGitHubMeta() {
  const cached = readGhCache();
  if (cached) return cached;
  try {
    const [repoRes, contribRes, prsRes] = await Promise.all([
      fetch(`${GH_API}/repos/${GH_REPO}`,                       { headers: { Accept: 'application/vnd.github+json' } }),
      fetch(`${GH_API}/repos/${GH_REPO}/contributors?per_page=100`, { headers: { Accept: 'application/vnd.github+json' } }),
      fetch(`${GH_API}/search/issues?q=repo:${GH_REPO}+type:pr+state:open&per_page=1`, { headers: { Accept: 'application/vnd.github+json' } }),
    ]);
    if (!repoRes.ok || !contribRes.ok) {
      console.warn('[terminal] github api unavailable, falling back to placeholders');
      return null;
    }
    const repo     = await repoRes.json();
    const contribs = await contribRes.json();
    const prs      = prsRes.ok ? await prsRes.json() : { total_count: 0 };
    const data = {
      repo: {
        stars:    repo.stargazers_count    ?? 0,
        forks:    repo.forks_count         ?? 0,
        watchers: repo.subscribers_count   ?? 0,
        issues:   repo.open_issues_count   ?? 0,
        prs_open: prs.total_count          ?? 0,
        license:  (repo.license && repo.license.spdx_id) || 'MIT',
      },
      contribs: contribs.map(c => ({ login: c.login, contributions: c.contributions })),
    };
    writeGhCache(data);
    return data;
  } catch (err) {
    console.warn('[terminal] github api fetch failed:', err.message);
    return null;
  }
}

function applyGhEnrichment(gh) {
  if (!gh) return;
  // Repo card
  Object.assign(NGREPO, gh.repo);
  window.NGREPO = NGREPO;
  // Per-contributor real commit counts. Derive prs / add / del from commits
  // (still synthetic but at least proportional to real activity, instead of
  // identical across everyone with the same contribution-type count).
  const byLogin = new Map(gh.contribs.map(c => [c.login.toLowerCase(), c.contributions]));
  // LoC per commit is fabricated — GitHub's stats/contributors endpoint
  // returns real adds/dels but is async (often 202) and per-repo-cached.
  // The multipliers below give plausible totals (~25 LoC added per commit,
  // ~8 deleted) instead of the previous absurd 110/40 ratios that made
  // ambicuity's totals look like 1.3M / 480k.
  NGCONTRIB.forEach(p => {
    const real = byLogin.get(p.handle.toLowerCase());
    if (real != null) {
      p.commits = real;
      p.prs     = Math.max(1, Math.round(real * 0.20));
      p.add     = Math.max(50, real * 25);
      p.del     = Math.max(20, real * 8);
    }
  });
  NGCONTRIB.sort((a, b) => b.commits - a.commits);
}

// ── Bootstrap ────────────────────────────────────────────────────────────

let NGCONTRIB = [];
window.NGCONTRIB = NGCONTRIB;
window.NGREPO = NGREPO;
window.AREA_COLOR = AREA_COLOR;

const NGCONTRIB_READY = fetch('contributors.json', { cache: 'no-cache' })
  .then(r => {
    if (!r.ok) throw new Error(`contributors.json: HTTP ${r.status}`);
    return r.json();
  })
  .then(async d => {
    const list = (d && d.contributors) || [];
    NGCONTRIB = list.map(mapContributor);
    const gh = await fetchGitHubMeta();
    applyGhEnrichment(gh);
    NGCONTRIB.sort((a, b) => b.commits - a.commits);
    window.NGCONTRIB = NGCONTRIB;
    return NGCONTRIB;
  })
  .catch(err => {
    console.error('[terminal] failed to load contributors.json:', err);
    window.NGCONTRIB = [];
    return [];
  });

window.NGCONTRIB_READY = NGCONTRIB_READY;
