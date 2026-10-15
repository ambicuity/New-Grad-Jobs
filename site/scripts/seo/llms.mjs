// /llms.txt (https://llmstxt.org): a Markdown map of the site for language
// models and agents. H1, a blockquote summary, detail paragraphs (no
// headings), then H2 sections of "- [name](url): notes" links, with
// "## Optional" last. Every count is computed from the published data at
// build time; with no data the counts are left out rather than guessed.

import { REPO_URL } from './render.mjs';

const num = (n) => n.toLocaleString('en-US');
const roles = (n) => `${num(n)} open role${n === 1 ? '' : 's'}`;
const isCount = (n) => typeof n === 'number' && Number.isFinite(n) && n >= 0;
const iso = (date) => (date ? date.toISOString().replace(/\.\d{3}Z$/, 'Z') : '');
// One list line: brackets in the name and line breaks anywhere would break the list syntax.
const oneLine = (text) => String(text ?? '').replace(/\s+/g, ' ').trim();
const link = (name, url, notes) => `- [${oneLine(name).replace(/[[\]]/g, '')}](${url})${oneLine(notes) ? `: ${oneLine(notes)}` : ''}`;

/**
 * @param {{
 *   siteUrl: string,
 *   generatedAt: Date|null,
 *   totalJobs: number|null,
 *   guides: {slug: string, title: string, description?: string}[],
 *   legal: {slug: string, title: string, description?: string}[],
 *   categories: {path: string, name: string, count: number}[],
 * }} args
 * @returns {string}
 */
export function renderLlmsTxt({ siteUrl, generatedAt, totalJobs, guides, legal, categories }) {
  const site = siteUrl.replace(/\/+$/, '');
  const hasData = isCount(totalJobs) && totalJobs > 0;
  const snapshot = hasData
    ? ` This build lists ${roles(totalJobs)}${generatedAt ? ` as of ${iso(generatedAt)}` : ''}.`
    : '';

  const out = [
    '# NGJ · New Grad Jobs',
    '',
    `> NGJ is a free, fully automated board of new grad and entry-level jobs in every field (software, data, engineering, finance, marketing, sales, healthcare and more) in the United States, Canada and India. It pulls postings straight from employers' own careers systems (Greenhouse, Lever, Ashby, SmartRecruiters, Oracle HCM, Rippling, UKG, ADP, Workable, Paylocity, SuccessFactors, iCIMS, Workday) and from Indeed, filters them by published rules, and republishes them as static pages and JSON about every 30 minutes.${snapshot}`,
    '',
    'NGJ is a discovery service, not an employer or recruiter. It has no accounts and no server: everything is a static file on GitHub Pages, regenerated on every run. Listings can change or close between runs, so check `meta.generated_at` in jobs.json and send people to the employer\'s own posting (the `url` field) to confirm details and apply.',
    '',
    'For data, prefer the files below to crawling the HTML pages: jobs.json holds every open listing in one request. Each job has `job_id` (stable: "job_" + 20 hex characters, also used in `/job/<job_id>/` page URLs), `title`, `company`, `location`, `url` (the employer\'s posting), `posted_at` and `first_seen` (ISO 8601 UTC), `source` (the careers system it came from), `category` (`{id, name}`), `company_tier`, `flags` (`no_sponsorship`, `us_citizenship_required`), `comp` (salary only when the posting states it, else null), `is_closed` and `description` (a plain-text excerpt of at most 3,000 characters, empty for some sources such as Workday; the full cleaned description, up to 50,000 characters, is in descriptions/<0-f>.json keyed by job_id).',
    '',
    'Visa labels are literal: "no restriction stated" means the posting states no sponsorship or citizenship restriction, not that the role sponsors visas. NGJ never estimates salaries or counts.',
    '',
    'Licensing: NGJ\'s code, guides and documentation are MIT licensed. Job titles, descriptions and employer names belong to the employers and source platforms that published them and are not covered by NGJ\'s licence. Credit the employer and link the original posting when you quote a listing, and do not imply that NGJ or an employer endorses anything. See the copyright policy below.',
    '',
    '## Data files',
    '',
    link('jobs.json', `${site}/jobs.json`, 'every open listing with a description excerpt; schema in the README'),
    link('jobs-index.json', `${site}/jobs-index.json`, 'the same listings without descriptions (what the board loads first); descriptions are sharded in descriptions/<0-f>.json by job_id'),
    link('feed.xml', `${site}/feed.xml`, 'RSS of newly discovered roles; per-category, remote and no-visa-restriction feeds live under feeds/'),
    link('health.json', `${site}/health.json`, 'telemetry for the latest run: status, per-source counts and failures'),
    link('sitemap.xml', `${site}/sitemap.xml`, 'every static page, including one page per open job'),
    '',
    '## About and policies',
    '',
    link('How this board works', `${site}/about/`, 'sources, inclusion rules and the latest run\'s numbers'),
    ...legal.map((p) => link(p.title, `${site}/${p.slug}/index.md`, p.description)),
    link('Third-party licences', `${site}/third-party-licenses.txt`, 'licence texts for the software and font bundled with the site'),
  ];

  if (guides.length) {
    out.push('', '## Guides', '', ...guides.map((g) => link(g.title, `${site}/guides/${g.slug}/index.md`, g.description)));
  }

  if (hasData && categories.length) {
    out.push(
      '',
      '## Browse',
      '',
      link('All landing pages', `${site}/jobs/`, 'jobs by role, company, metro, country, remote and visa'),
      ...categories.map((c) => link(`${c.name} jobs`, `${site}/${c.path}`, roles(c.count))),
    );
  }

  out.push(
    '',
    '## Optional',
    '',
    link('jobs-extended.json', `${site}/jobs-extended.json`, 'near misses: postings that fail only soft rules (internship or co-op, level III+, outside US/CA/IN, 60 to 120 days old); never counted'),
    link('corpus-index.json', `${site}/corpus-index.json`, 'every unique posting the latest run saw, before filtering (large)'),
    link('Interactive board', `${site}/`, 'the JavaScript job board; filters are kept in the URL query string'),
    link('Source repository', REPO_URL, 'MIT-licensed scraper and site; README documents the jobs.json schema'),
    link('config.yml', `${REPO_URL}/blob/main/config.yml`, 'every configured employer board and the filter signals'),
    link('Architecture', `${REPO_URL}/blob/main/docs/architecture.md`, 'how a run fetches, filters and publishes'),
    '',
  );
  return out.join('\n');
}
