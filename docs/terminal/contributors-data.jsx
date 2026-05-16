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
  .then(d => {
    const list = (d && d.contributors) || [];
    NGCONTRIB = list.map(mapContributor);
    // Sort so the owner sits first (matches the table's initial selection).
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
