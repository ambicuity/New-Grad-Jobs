// Real-data adapter for the NGJ terminal frontend.
// Loads docs/jobs.json (scraped, ~1k jobs) and maps to the shape that
// dashboard.jsx expects (the same shape the original mock data.jsx used).
//
// Exposes on window: NGJOBS, TYPE_LABEL, SIZE_LABEL, RMT_LABEL,
//                    fmtComp, daysLeft, deadlineLabel, deadlineHot,
//                    NGJOBS_READY (Promise that resolves once jobs are loaded).

// Canonical job categories — the single source of truth shared with
// scripts/update_jobs.py (CATEGORY_PATTERNS), docs/jobs.json (meta.categories),
// and the README. Keep these ids/order in step with CATEGORY_TYPE below.
const TYPE_LABEL = { SWE:'swe', FE:'frontend', BE:'backend', MOBILE:'mobile', SEC:'security', ML:'ml', DATA:'data', INFRA:'infra', PM:'product', QUANT:'quant', HW:'hardware', OTHER:'other' };
const SIZE_LABEL = { S:'<50', M:'50–500', L:'500–5k', XL:'5k+' };
const RMT_LABEL  = { remote:'remote', hybrid:'hybrid', onsite:'onsite' };

function fmtComp(c) {
  if (!Array.isArray(c) || c[0] == null || c[1] == null) return '—';
  return `$${c[0]}–${c[1]}k`;
}
function daysLeft(dl) {
  if (!dl) return 999;
  const t = new Date(dl) - new Date();
  return Math.round(t / 86400000);
}
function deadlineLabel(dl) {
  const d = daysLeft(dl);
  if (d < 0) return 'closed';
  if (d === 0) return 'today';
  if (d < 7) return `${d}d left`;
  if (d < 30) return `${Math.floor(d/7)}w left`;
  return `${Math.floor(d/30)}mo left`;
}
function deadlineHot(dl) { return daysLeft(dl) <= 14; }

// ── Mapping helpers ──────────────────────────────────────────────────────

// Canonical category id (from jobs.json `job.category.id`) → short type code.
// This is the ONLY source of the terminal's type column/filters, so the site
// stays in step with docs/jobs.json meta.categories and the README rather than
// re-deriving a separate taxonomy from job titles.
const CATEGORY_TYPE = {
  software_engineering: 'SWE',
  frontend:             'FE',
  backend:              'BE',
  mobile:               'MOBILE',
  security:             'SEC',
  data_ml:              'ML',
  data_engineering:     'DATA',
  infrastructure_sre:   'INFRA',
  product_management:   'PM',
  quant_finance:        'QUANT',
  hardware:             'HW',
  other:                'OTHER',
};

function deriveType(j) {
  const catId = (j.category || {}).id || 'other';
  return CATEGORY_TYPE[catId] || 'OTHER';
}

const TIER_SIZE = {
  faang_plus: 'XL',
  unicorn:    'L',
  other:      'M',
};

function ageString(postedAt) {
  if (!postedAt) return '—';
  const ms = Date.now() - new Date(postedAt).getTime();
  if (isNaN(ms) || ms < 0) return 'now';
  const hours = Math.floor(ms / 3600000);
  if (hours < 1)  return 'now';
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7)   return `${days}d`;
  if (days < 30)  return `${Math.floor(days/7)}w`;
  return `${Math.floor(days/30)}mo`;
}

function addDays(isoString, n) {
  const d = isoString ? new Date(isoString) : new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function compTuple(j) {
  // `comp` is published by the scraper as { min, max, currency, source } when
  // a salary range was extractable from the job posting, otherwise null.
  // The design's fmtComp expects [low, high] in thousands ($120–180k style)
  // and treats [null, null] as '—', so honor that contract.
  const c = j.comp;
  if (!c || c.min == null || c.max == null) return [null, null];
  return [Math.round(c.min / 1000), Math.round(c.max / 1000)];
}

function deriveRmt(j) {
  // The scraper doesn't publish a structured remote flag (jobs.json only has
  // location string + title). Derive remote/hybrid/onsite from that text.
  // Hybrid wins over remote when both keywords appear ("San Francisco, hybrid
  // remote" → hybrid). Pure 'remote' wins when only that keyword shows.
  const hay = `${j.location || ''} ${j.title || ''}`.toLowerCase();
  if (/\bhybrid\b/.test(hay)) return 'hybrid';
  if (/\bremote\b/.test(hay)) return 'remote';
  return 'onsite';
}

function mapJob(j) {
  const tier  = (j.company_tier || {}).tier || 'other';
  const flags = j.flags || {};
  const noSponsorship = flags.no_sponsorship === true || flags.us_citizenship_required === true;
  return {
    id:      j.id,
    co:      j.company || '—',
    role:    j.title   || '—',
    loc:     j.location || '—',
    url:     j.url || '',
    rmt:     deriveRmt(j),                   // derived from location+title text
    visa:    !noSponsorship,
    size:    TIER_SIZE[tier] || 'M',
    stack:   ['—'],                          // not in source data
    cohort:  '26',                           // all jobs are new-grad
    comp:    compTuple(j),                   // [null, null] when undisclosed
    dl:      addDays(j.posted_at, 90),       // synthetic 90-day window
    type:    deriveType(j),
    posted:  ageString(j.posted_at),
    // Raw timestamp for chronological sort. ageString() is for display only;
    // sorting on its output yields lexicographic order ("1d" < "1w" < "2d" …)
    // rather than recency. 0 here means "no timestamp" — those rows sort last
    // under the descending (newest-first) default.
    postedTs: j.posted_at ? new Date(j.posted_at).getTime() || 0 : 0,
    level:   'entry',
    desc:    (j.full_description && j.full_description.length > 60)
               ? j.full_description
               : (j.description && j.description.length > 60)
                 ? j.description
                 : `${j.company || 'This company'} is hiring for ${j.title || 'this role'}${j.location ? ' in ' + j.location : ''}. Posted via ${j.source || 'their careers page'}.`,
  };
}

// ── Bootstrap ────────────────────────────────────────────────────────────

let NGJOBS = [];
window.NGJOBS = NGJOBS;
// Surface jobs.json `meta` (notably meta.generated_at) so the LIVE indicator
// in app.jsx can render a real timestamp instead of a hardcoded one.
window.NGJOBS_META = {};

const NGJOBS_READY = fetch('jobs.json', { cache: 'no-cache' })
  .then(r => {
    if (!r.ok) throw new Error(`jobs.json: HTTP ${r.status}`);
    return r.json();
  })
  .then(d => {
    window.NGJOBS_META = d.meta || {};
    // Real jobs.json contains duplicate ids (same role on multiple sources).
    // Disambiguate by appending an index suffix when needed.
    const seen = new Map();
    NGJOBS = (d.jobs || []).map(mapJob).map(j => {
      const n = (seen.get(j.id) || 0) + 1;
      seen.set(j.id, n);
      return n === 1 ? j : { ...j, id: `${j.id}#${n}` };
    });
    window.NGJOBS = NGJOBS;
    return NGJOBS;
  })
  .catch(err => {
    console.error('[terminal] failed to load jobs.json:', err);
    window.NGJOBS = [];
    window.NGJOBS_META = {};
    return [];
  });

Object.assign(window, {
  TYPE_LABEL, SIZE_LABEL, RMT_LABEL,
  fmtComp, daysLeft, deadlineLabel, deadlineHot,
  NGJOBS_READY,
});
