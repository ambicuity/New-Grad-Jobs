// Build-time landing pages: /jobs/<category>/, /jobs/at/<company>/,
// /jobs/in/<metro>/, /jobs/remote/, /jobs/no-visa-restriction/,
// /jobs/new-this-week/ and the /jobs/ hub. Every number on a page is derived
// from the job data handed in (hard rule: no invented counts).
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  LANDING_ROOT, buildLandingPages, landingPageUrl, renderLandingHub, renderLandingPage, slugify,
} from '../scripts/seo/landing.mjs';
import { JOB_PAGE_CSP, PRERENDER_MARKER, renderPrerenderList, renderSitemap } from '../scripts/seo/render.mjs';
import { generateSeo } from '../scripts/seo/generate.mjs';
import { parsePostedAt } from '../scripts/seo/jobposting.mjs';
import { escapeHtml } from '../scripts/seo/text.mjs';

const SITE = 'https://jobs.example.test';
const GENERATED_AT = new Date('2026-09-25T12:00:00Z');
const ldBlocks = (html) => [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);

let seq = 0;
function entry({
  company = 'Acme', title = 'Software Engineer, New Grad', location = 'San Francisco, CA',
  category = 'software_engineering', categoryName = 'Software Engineering', flags = { no_sponsorship: false, us_citizenship_required: false },
  posted_at = '2026-09-20T10:00:00Z', first_seen = posted_at,
} = {}) {
  seq += 1;
  const job = {
    job_id: `job_${String(seq).padStart(6, '0')}`, company, title, location, url: `https://boards.example.com/${seq}`,
    posted_at, first_seen, flags, category: { id: category, name: categoryName, emoji: 'x' }, source: 'Greenhouse',
  };
  return { job, posted: parsePostedAt(posted_at), description: '', posting: null };
}

const repeat = (n, make) => Array.from({ length: n }, (_, i) => make(i));

describe('slugify', () => {
  it('lower-cases, strips accents and punctuation, collapses dashes', () => {
    expect(slugify('New York, NY')).toBe('new-york-ny');
    expect(slugify('  Montréal, QC ')).toBe('montreal-qc');
    expect(slugify('Acme <Corp> & Sons!!')).toBe('acme-corp-sons');
    expect(slugify('software_engineering')).toBe('software-engineering');
  });

  it('returns an empty string for junk and caps the length', () => {
    expect(slugify('!!!')).toBe('');
    expect(slugify(null)).toBe('');
    expect(slugify('a'.repeat(200)).length).toBeLessThanOrEqual(60);
  });
});

describe('buildLandingPages', () => {
  const entries = [
    ...repeat(4, () => entry({ company: 'SpaceX', location: 'Hawthorne, CA' })),
    ...repeat(3, () => entry({ company: 'OpenAI', location: 'San Francisco, California, United States', category: 'data_ml', categoryName: 'Data Science & ML' })),
    ...repeat(2, () => entry({ company: 'Tiny Co', location: 'Remote - US', title: 'Remote Software Engineer' })),
    ...repeat(5, (i) => entry({ company: `Co ${i}`, location: i % 2 ? 'New York, NY' : 'New York, New York, United States' })),
    ...repeat(3, () => entry({ company: 'Shopify', location: 'Toronto, ON, Canada' })),
    ...repeat(2, () => entry({ company: 'Flipkart', location: 'Bengaluru, Karnataka, India' })),
    entry({ company: 'Anduril', location: 'Costa Mesa, CA', flags: { no_sponsorship: false, us_citizenship_required: true } }),
    entry({ company: 'Ripple', location: 'Chicago, IL', flags: { no_sponsorship: true, us_citizenship_required: false } }),
    entry({ company: 'Old Co', location: 'Austin, TX', posted_at: '2026-08-01T00:00:00Z' }),
    entry({ company: 'Fresh Co', location: 'Austin, TX', posted_at: '2026-08-01T00:00:00Z', first_seen: '2026-09-24T00:00:00Z' }),
    entry({ company: 'Misc', location: 'Denver, CO', category: 'other', categoryName: 'Other' }),
    entry({ company: 'No Cat', location: 'Denver, CO', category: '', categoryName: '' }),
  ];
  const { hub, pages } = buildLandingPages(entries, { generatedAt: GENERATED_AT, minCompanyJobs: 3, minLocationJobs: 4 });
  const byPath = Object.fromEntries(pages.map((p) => [p.path, p]));

  it('makes one page per real category, never for "other" or missing categories', () => {
    const cats = pages.filter((p) => p.kind === 'category').map((p) => p.path).sort();
    expect(cats).toEqual(['jobs/data-ml/', 'jobs/software-engineering/']);
    expect(byPath['jobs/software-engineering/'].entries).toHaveLength(entries.length - 3 - 2);
    expect(byPath['jobs/software-engineering/'].boardQuery).toBe('role=SWE');
    expect(byPath['jobs/data-ml/'].boardQuery).toBe('role=ML');
  });

  it('makes company pages only above the threshold, sorted by open roles', () => {
    const companies = pages.filter((p) => p.kind === 'company');
    expect(companies.map((p) => p.path)).toEqual(['jobs/at/spacex/', 'jobs/at/openai/', 'jobs/at/shopify/']);
    expect(companies[0].entries).toHaveLength(4);
    expect(companies[0].boardQuery).toBe('co=SpaceX');
  });

  it('groups metros across spellings and state names, and only above the threshold', () => {
    const locations = pages.filter((p) => p.kind === 'location');
    expect(locations.map((p) => p.path)).toEqual(['jobs/in/new-york-ny/', 'jobs/in/hawthorne-ca/']);
    expect(byPath['jobs/in/new-york-ny/'].entries).toHaveLength(5);
    expect(byPath['jobs/in/new-york-ny/'].name).toBe('New York, NY');
    expect(byPath['jobs/in/new-york-ny/'].boardQuery).toBe('metro=New+York%2C+NY');
  });

  it('makes country pages for Canada and India from parsed locations', () => {
    expect(byPath['jobs/in/canada/'].entries).toHaveLength(3);
    expect(byPath['jobs/in/india/'].entries).toHaveLength(2);
    expect(byPath['jobs/in/canada/'].boardQuery).toBe('country=CA');
    expect(pages.some((p) => p.path === 'jobs/in/united-states/')).toBe(false);
  });

  it('remote, no-visa-restriction and new-this-week pages use the same rules as the board filters', () => {
    expect(byPath['jobs/remote/'].entries.map((e) => e.job.company)).toEqual(['Tiny Co', 'Tiny Co']);
    expect(byPath['jobs/remote/'].boardQuery).toBe('remote=remote');
    const visa = byPath['jobs/no-visa-restriction/'].entries.map((e) => e.job.company);
    expect(visa).not.toContain('Anduril');
    expect(visa).not.toContain('Ripple');
    expect(visa).toContain('SpaceX');
    expect(byPath['jobs/no-visa-restriction/'].boardQuery).toBe('visa=none');
    const fresh = byPath['jobs/new-this-week/'].entries.map((e) => e.job.company);
    expect(fresh).toContain('Fresh Co');
    expect(fresh).not.toContain('Old Co');
    expect(byPath['jobs/new-this-week/'].boardQuery).toBe('new=168');
  });

  it('orders every page newest first and gives it real counts', () => {
    for (const page of pages) {
      const times = page.entries.map((e) => e.posted.getTime());
      expect(times).toEqual([...times].sort((a, b) => b - a));
      expect(page.title).toContain(`(${page.entries.length} open)`);
      expect(page.description).toMatch(new RegExp(`\\b${page.entries.length}\\b`));
    }
    expect(hub.path).toBe(`${LANDING_ROOT}/`);
    expect(hub.pages).toBe(pages);
  });

  it('returns nothing without jobs', () => {
    expect(buildLandingPages([], { generatedAt: GENERATED_AT })).toEqual({ hub: null, pages: [] });
  });

  it('honours the company page cap', () => {
    const many = repeat(40, (i) => [entry({ company: `C${i}` }), entry({ company: `C${i}` }), entry({ company: `C${i}` })]).flat();
    const { pages: capped } = buildLandingPages(many, { generatedAt: GENERATED_AT, maxCompanies: 5 });
    expect(capped.filter((p) => p.kind === 'company')).toHaveLength(5);
  });
});

describe('renderLandingPage', () => {
  const hostile = entry({ company: 'Acme <Corp>', title: 'SWE </script><script>alert(1)</script>' });
  const { pages } = buildLandingPages([hostile, entry(), entry()], { generatedAt: GENERATED_AT, minCompanyJobs: 1 });
  const category = pages.find((p) => p.kind === 'category');
  const company = pages.find((p) => p.kind === 'company' && p.name === 'Acme <Corp>');

  it('escapes data, carries canonical/meta/CSP and parseable ItemList JSON-LD', () => {
    const html = renderLandingPage(category, { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: pages });
    expect(html).not.toContain('<script>alert(1)');
    expect(html).toContain('&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).toContain(`<link rel="canonical" href="${SITE}/jobs/software-engineering/">`);
    expect(html).toContain('<meta name="description" content="');
    expect(html).toContain(`content="${escapeHtml(JOB_PAGE_CSP)}"`);
    const blocks = ldBlocks(html);
    expect(blocks).toHaveLength(1);
    const data = JSON.parse(blocks[0]);
    expect(data['@type']).toBe('ItemList');
    expect(data.itemListElement).toHaveLength(3);
    expect(data.itemListElement[0]).toMatchObject({ '@type': 'ListItem', position: 1, url: `${SITE}/job/${category.entries[0].job.job_id}/` });
  });

  it('links to the job board with the matching filter and to every job page, relative to its depth', () => {
    const html = renderLandingPage(category, { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: pages });
    expect(html).toContain('href="../../?role=SWE"');
    expect(html).toContain(`href="../../job/${category.entries[0].job.job_id}/"`);
    const deep = renderLandingPage(company, { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: pages });
    expect(deep).toContain('href="../../../?co=Acme+%3CCorp%3E"');
    expect(deep).toContain(`href="../../../job/${company.entries[0].job.job_id}/"`);
    expect(deep).toContain('href="../../../jobs/"');
  });

  it('cross-links sibling landing pages and shows the generated-at date', () => {
    const html = renderLandingPage(category, { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: pages });
    expect(html).toContain('href="../../jobs/new-this-week/"');
    expect(html).toContain('2026-09-25');
  });

  it('caps the visible list and says so', () => {
    const big = repeat(320, () => entry());
    const { pages: p } = buildLandingPages(big, { generatedAt: GENERATED_AT });
    const html = renderLandingPage(p.find((x) => x.kind === 'category'), { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: p, listLimit: 300 });
    expect((html.match(/<li>/g) || []).length).toBe(300);
    expect(html).toContain('300 of 320');
  });

  it('hub lists every page with its count', () => {
    const { hub } = buildLandingPages([entry(), entry()], { generatedAt: GENERATED_AT });
    const html = renderLandingHub(hub, { siteUrl: SITE, generatedAt: GENERATED_AT, totalJobs: 2 });
    expect(html).toContain(`<link rel="canonical" href="${SITE}/jobs/">`);
    expect(html).toContain('href="../jobs/software-engineering/"');
    expect(html).toContain('href="../?"');
    expect(html).toContain('Software Engineering</a> <span class="dim">2 open</span>');
  });
});

describe('sitemap and prerender integration', () => {
  it('sitemap lists landing pages after the home page with the generated-at lastmod', () => {
    const e = entry();
    const xml = renderSitemap(SITE, GENERATED_AT, [e], [{ loc: landingPageUrl(SITE, 'jobs/remote/'), lastmod: GENERATED_AT }]);
    expect(xml).toContain(`<loc>${SITE}/jobs/remote/</loc><lastmod>2026-09-25T12:00:00.000Z</lastmod>`);
    expect(xml.indexOf('jobs/remote')).toBeLessThan(xml.indexOf('/job/job_'));
  });

  it('prerendered list carries browse links so crawlers find the landing pages', () => {
    const e = entry();
    const snippet = renderPrerenderList([e], 1, [{ path: 'jobs/software-engineering/', label: 'Software Engineering', count: 1 }]);
    expect(snippet).toContain('href="./jobs/software-engineering/"');
    expect(snippet).toContain('href="./jobs/"');
  });
});

describe('generateSeo writes landing pages', () => {
  let root;
  let publicDir;
  let distDir;
  const quiet = { log: () => {}, warn: () => {} };

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'ngj-landing-'));
    publicDir = join(root, 'public');
    distDir = join(root, 'dist');
    await mkdir(publicDir, { recursive: true });
    await mkdir(distDir, { recursive: true });
    await writeFile(join(distDir, 'index.html'), `<html><body><div id="root">${PRERENDER_MARKER}</div></body></html>`);
  });
  afterEach(() => rm(root, { recursive: true, force: true }));

  it('writes the hub, category, company and remote pages and lists them in the sitemap', async () => {
    const jobs = [
      ...repeat(3, () => entry({ company: 'SpaceX' }).job),
      entry({ company: 'Remote Co', location: 'Remote - US' }).job,
    ];
    await writeFile(join(publicDir, 'jobs.json'), JSON.stringify({ meta: { generated_at: GENERATED_AT.toISOString() }, jobs }));

    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: quiet });

    expect(stats.jobPages).toBe(4);
    expect(stats.landingPages).toBeGreaterThanOrEqual(4);
    for (const rel of ['jobs/index.html', 'jobs/software-engineering/index.html', 'jobs/at/spacex/index.html', 'jobs/remote/index.html']) {
      expect(existsSync(join(distDir, rel)), rel).toBe(true);
    }
    const sitemap = await readFile(join(distDir, 'sitemap.xml'), 'utf8');
    expect(sitemap).toContain(`<loc>${SITE}/jobs/software-engineering/</loc>`);
    expect(sitemap.match(/<url>/g)).toHaveLength(stats.sitemapUrls);
    expect(stats.sitemapUrls).toBe(1 + stats.landingPages + stats.jobPages);
    const index = await readFile(join(distDir, 'index.html'), 'utf8');
    expect(index).toContain('href="./jobs/software-engineering/"');
  });
});

describe('subscribe links', () => {
  it('category, remote and visa pages point at their own RSS slice; others at feed.xml', () => {
    const entries = [
      entry({ company: 'Acme', location: 'Remote - US' }),
      entry({ company: 'Acme' }),
      entry({ company: 'Acme' }),
    ];
    const { hub, pages } = buildLandingPages(entries, { generatedAt: GENERATED_AT, minCompanyJobs: 3 });
    const render = (page) => renderLandingPage(page, { siteUrl: SITE, generatedAt: GENERATED_AT, siblings: pages });
    const category = pages.find((p) => p.kind === 'category');
    expect(category.categoryId).toBe('software_engineering');
    expect(render(category)).toContain('href="../../feeds/software-engineering.xml"');
    expect(render(category)).toContain(`https://feedly.com/i/subscription/feed/${encodeURIComponent(`${SITE}/feeds/software-engineering.xml`)}`);
    expect(render(pages.find((p) => p.kind === 'remote'))).toContain('href="../../feeds/remote.xml"');
    expect(render(pages.find((p) => p.kind === 'visa'))).toContain('href="../../feeds/no-visa-restriction.xml"');
    expect(render(pages.find((p) => p.kind === 'company'))).toContain('href="../../../feed.xml"');
    expect(renderLandingHub(hub, { siteUrl: SITE, generatedAt: GENERATED_AT, totalJobs: 3 })).toContain('href="../feed.xml"');
  });
});
