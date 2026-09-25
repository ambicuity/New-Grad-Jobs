// Build-time SEO generator: escaping, JobPosting JSON-LD validity, location
// parsing, and the full generate pass against temp dirs (with and without data).
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  cleanText, decodeEntities, escapeHtml, jsonForScript, toParagraphs, truncate,
} from '../scripts/seo/text.mjs';
import { parseLocation, splitLocations } from '../scripts/seo/location.mjs';
import {
  baseSalary, buildJobPosting, employmentType, isSafeJobId, locationProps, parsePostedAt,
} from '../scripts/seo/jobposting.mjs';
import {
  JOB_PAGE_CSP, PRERENDER_MARKER, injectPrerender, renderJobPage, renderPrerenderList, renderRobots, renderSitemap,
} from '../scripts/seo/render.mjs';
import { generateSeo } from '../scripts/seo/generate.mjs';
import { APP_CSP, injectCsp } from '../scripts/seo/vite-plugin.mjs';
import { safeHttpUrl } from '../src/lib/safe-url.js';

const LS = String.fromCharCode(0x2028);
const PS = String.fromCharCode(0x2029);
const SITE = 'https://jobs.example.test';
const JOB = {
  job_id: 'job_a1b2c3',
  company: 'Acme <Corp>',
  title: 'Software Engineer, New Grad </script><script>alert(1)</script>',
  location: 'San Francisco, CA',
  url: 'https://boards.example.com/acme/1',
  posted_at: '2026-09-20T10:00:00.123456',
  comp: { min: 120000, max: 150000, currency: 'USD' },
  category: { name: 'Software Engineering' },
  source: 'Greenhouse',
};

const ldBlocks = (html) => [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);

describe('text helpers', () => {
  it('escapeHtml escapes the five HTML metacharacters', () => {
    expect(escapeHtml(`<a href="x">'&'</a>`)).toBe('&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;');
    expect(escapeHtml(null)).toBe('');
  });

  it('jsonForScript cannot break out of a script block and still parses', () => {
    const value = { t: `</script><!-- & ${LS} ${PS}` };
    const out = jsonForScript(value);
    expect(out).not.toMatch(new RegExp(`[<>&${LS}${PS}]`));
    expect(JSON.parse(out)).toEqual(value);
  });

  it('decodeEntities / cleanText handle scraped entities once', () => {
    expect(decodeEntities('A&nbsp;&amp;&nbsp;B &mdash; &#39;x&#x27; &bogus;')).toBe("A & B — 'x' &bogus;");
    expect(cleanText('  <b>Hi</b>\n\n there&amp;co ')).toBe('Hi there&co');
  });

  it('toParagraphs splits long text at sentence boundaries', () => {
    const text = Array.from({ length: 30 }, (_, i) => `Sentence number ${i} is here and it is long enough.`).join(' ');
    const paras = toParagraphs(text);
    expect(paras.length).toBeGreaterThan(1);
    expect(paras.join(' ')).toBe(cleanText(text));
    expect(toParagraphs('')).toEqual([]);
  });

  it('truncate cuts on a word boundary with an ellipsis', () => {
    expect(truncate('short', 10)).toBe('short');
    const t = truncate('the quick brown fox jumps over the lazy dog', 20);
    expect(t.length).toBeLessThanOrEqual(20);
    expect(t.endsWith('…')).toBe(true);
  });
});

describe('safeHttpUrl', () => {
  it('allows only absolute http(s) URLs', () => {
    expect(safeHttpUrl('https://a.example/x?y=1')).toBe('https://a.example/x?y=1');
    expect(safeHttpUrl(' http://a.example ')).toBe('http://a.example/');
    for (const bad of ['javascript:alert(1)', 'data:text/html,x', '/relative', 'nope', '', null, 42]) {
      expect(safeHttpUrl(bad)).toBe('');
    }
  });
});

describe('location parsing', () => {
  it('splits multi-location strings', () => {
    expect(splitLocations('SF, CA | NYC, NY; Remote, US • Austin')).toEqual(['SF, CA', 'NYC, NY', 'Remote, US', 'Austin']);
  });

  it('resolves US states, Canadian provinces and explicit countries', () => {
    expect(parseLocation('Hawthorne, CA').places).toEqual([{ locality: 'Hawthorne', region: 'CA', country: 'US' }]);
    expect(parseLocation('Toronto, ON, CA').places).toEqual([{ locality: 'Toronto', region: 'ON', country: 'CA' }]);
    expect(parseLocation('United States-California-Sunnyvale').places)
      .toEqual([{ locality: 'Sunnyvale', region: 'California', country: 'US' }]);
    expect(parseLocation('Bengaluru, Karnataka, India').places[0]).toMatchObject({ locality: 'Bengaluru', country: 'IN' });
  });

  it('keeps a city that shares its name with the state as the locality', () => {
    expect(parseLocation('New York, NY').places[0]).toEqual({ locality: 'New York', region: 'NY', country: 'US' });
    expect(parseLocation('New York, New York, United States').places[0]).toEqual({ locality: 'New York', region: 'New York', country: 'US' });
  });

  it('detects remote roles and their applicant countries', () => {
    expect(parseLocation('Remote - US')).toEqual({ remote: true, places: [], remoteCountries: ['US'] });
    expect(parseLocation('Remote, Canada; Remote, United Kingdom').remoteCountries).toEqual(['CA', 'GB']);
    expect(parseLocation('Hybrid - San Francisco').remote).toBe(false);
  });
});

describe('JobPosting fields', () => {
  it('parsePostedAt treats naive timestamps as UTC and rejects junk', () => {
    expect(parsePostedAt('2026-09-24T14:50:21.850000').toISOString()).toBe('2026-09-24T14:50:21.850Z');
    expect(parsePostedAt('2026-09-24T00:15:00Z').toISOString()).toBe('2026-09-24T00:15:00.000Z');
    expect(parsePostedAt('not a date')).toBeNull();
    expect(parsePostedAt(undefined)).toBeNull();
  });

  it('employmentType only when stated', () => {
    expect(employmentType('Software Engineering Intern')).toBe('INTERN');
    expect(employmentType('Engineer (Part-Time)')).toBe('PART_TIME');
    expect(employmentType('Contract Engineer')).toBe('CONTRACTOR');
    expect(employmentType('Engineer', 'Role Type: Full-time')).toBe('FULL_TIME');
    expect(employmentType('New Grad Software Engineer', 'great team')).toBeNull();
  });

  it('baseSalary requires a disclosed amount and ISO currency', () => {
    expect(baseSalary({ min: 100000, max: 150000, currency: 'USD' })).toEqual({
      '@type': 'MonetaryAmount', currency: 'USD',
      value: { '@type': 'QuantitativeValue', minValue: 100000, maxValue: 150000, unitText: 'YEAR' },
    });
    expect(baseSalary({ min: 40, max: 40, currency: 'usd' }).value).toEqual({ '@type': 'QuantitativeValue', value: 40, unitText: 'HOUR' });
    expect(baseSalary({ min: 100000, max: 150000 })).toBeNull();
    expect(baseSalary({ currency: 'USD' })).toBeNull();
    expect(baseSalary(null)).toBeNull();
  });

  it('locationProps: on-site → jobLocation, remote → TELECOMMUTE + applicantLocationRequirements', () => {
    expect(locationProps('Seattle, WA')).toEqual({
      jobLocation: [{ '@type': 'Place', address: { '@type': 'PostalAddress', addressLocality: 'Seattle', addressRegion: 'WA', addressCountry: 'US' } }],
    });
    expect(locationProps('Remote - Canada')).toEqual({
      jobLocationType: 'TELECOMMUTE',
      applicantLocationRequirements: [{ '@type': 'Country', name: 'Canada' }],
    });
    const mixed = locationProps('San Francisco, CA, US; Remote, US');
    expect(mixed.jobLocation).toHaveLength(1);
    expect(mixed.jobLocationType).toBe('TELECOMMUTE');
    expect(locationProps('Remote')).toBeNull();
  });

  it('isSafeJobId only allows path-safe ids', () => {
    expect(isSafeJobId('job_abc123')).toBe(true);
    for (const bad of ['../etc', 'a/b', '', 'job id', null]) expect(isSafeJobId(bad)).toBe(false);
  });
});

describe('buildJobPosting', () => {
  it('has every Google-required property and round-trips through JSON', () => {
    const { posting } = buildJobPosting(JOB, 'Build things &amp; ship. <b>Grow</b>.', `${SITE}/job/job_a1b2c3/`);
    const parsed = JSON.parse(jsonForScript(posting));
    expect(parsed['@context']).toBe('https://schema.org/');
    expect(parsed['@type']).toBe('JobPosting');
    expect(parsed.title).toBe(JOB.title);
    expect(parsed.datePosted).toBe('2026-09-20T10:00:00.123Z');
    expect(parsed.hiringOrganization).toEqual({ '@type': 'Organization', name: 'Acme <Corp>' });
    expect(parsed.jobLocation[0].address.addressCountry).toBe('US');
    expect(parsed.directApply).toBe(false);
    expect(parsed.baseSalary.currency).toBe('USD');
    expect(parsed.identifier.value).toBe('job_a1b2c3');
    expect(parsed.employmentType).toBeUndefined();
    // Description is HTML with escaped text — no raw tags from the source.
    expect(parsed.description).toBe('<p>Build things &amp; ship. Grow .</p>');
  });

  it('sets validThrough 60 days after datePosted (the scraper max age)', () => {
    const { posting } = buildJobPosting(JOB, 'Desc', `${SITE}/job/job_a1b2c3/`);
    expect(posting.validThrough).toBe('2026-11-19T10:00:00.123Z');
  });

  it('falls back to a generated description and omits undisclosed salary', () => {
    const { posting } = buildJobPosting({ ...JOB, comp: null }, '', 'u');
    expect(posting.description).toContain('The full description is on the employer');
    expect(posting.baseSalary).toBeUndefined();
  });

  it('returns a reason instead of invalid markup', () => {
    expect(buildJobPosting({ ...JOB, title: '' }, '', 'u')).toEqual({ posting: null, reason: 'missing title' });
    expect(buildJobPosting({ ...JOB, company: ' ' }, '', 'u').reason).toBe('missing company');
    expect(buildJobPosting({ ...JOB, posted_at: 'x' }, '', 'u').reason).toBe('missing datePosted');
    expect(buildJobPosting({ ...JOB, location: 'Remote' }, '', 'u').reason).toBe('unresolvable location');
    expect(buildJobPosting(null).reason).toBe('no job');
  });
});

describe('renderers', () => {
  const posted = parsePostedAt(JOB.posted_at);

  it('job page escapes everything, has a strict CSP and parseable JSON-LD', () => {
    const { posting } = buildJobPosting(JOB, 'Desc', `${SITE}/job/job_a1b2c3/`);
    const html = renderJobPage({ job: JOB, description: 'Desc', posted, posting, siteUrl: SITE });
    expect(html).not.toContain('<script>alert(1)');
    expect(html).toContain('&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).toContain(`<link rel="canonical" href="${SITE}/job/job_a1b2c3/">`);
    expect(html).toContain('href="../../?job=job_a1b2c3"');
    expect(html).toContain('href="https://boards.example.com/acme/1"');
    expect(html).toContain('Content-Security-Policy');
    expect(JOB_PAGE_CSP).toMatch(/default-src 'none'/);
    expect(JOB_PAGE_CSP).not.toMatch(/script-src/);
    const blocks = ldBlocks(html);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).not.toMatch(/<\//);
    expect(JSON.parse(blocks[0]).title).toBe(JOB.title);
  });

  it('job page breadcrumb link keeps its underline (not colour-only, WCAG 1.4.1)', () => {
    const html = renderJobPage({ job: JOB, description: 'Desc', posted, posting: null, siteUrl: SITE });
    expect(html).toContain('<nav class="crumb"');
    expect(html).not.toMatch(/\.crumb a\{[^}]*text-decoration:\s*none/);
  });

  it('job page drops non-http apply URLs and omits JSON-LD when unavailable', () => {
    const html = renderJobPage({ job: { ...JOB, url: 'javascript:alert(1)' }, description: '', posted, posting: null, siteUrl: SITE });
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('APPLY ON EMPLOYER SITE');
    expect(ldBlocks(html)).toHaveLength(0);
  });

  it('prerender list has real links and escaped text; marker injection', () => {
    const snippet = renderPrerenderList([{ job: JOB, posted }], 10);
    expect(snippet).toContain('<a href="./job/job_a1b2c3/">');
    expect(snippet).toContain('Acme &lt;Corp&gt;');
    expect(snippet).toContain('latest 1 of 10');
    expect(renderPrerenderList([], 0)).toBe('');
    const page = `<div id="root">${PRERENDER_MARKER}</div>`;
    expect(injectPrerender(page, snippet)).toEqual({ html: `<div id="root">${snippet}</div>`, injected: true });
    expect(injectPrerender('<div></div>', snippet).injected).toBe(false);
    // `$&`-style patterns in data must not be interpreted by String.replace.
    expect(injectPrerender(PRERENDER_MARKER, '$&').html).toBe('$&');
  });

  it('sitemap and robots', () => {
    const xml = renderSitemap(SITE, posted, [{ job: JOB, posted }]);
    expect(xml).toContain(`<loc>${SITE}/</loc>`);
    expect(xml).toContain(`<loc>${SITE}/job/job_a1b2c3/</loc><lastmod>2026-09-20T10:00:00.123Z</lastmod>`);
    expect(renderRobots(SITE)).toBe(`User-agent: *\nAllow: /\n\nSitemap: ${SITE}/sitemap.xml\n`);
  });

  it('app CSP is injected right after <meta charset>', () => {
    const out = injectCsp('<head>\n  <meta charset="UTF-8">\n</head>', APP_CSP);
    expect(out).toMatch(/<meta charset="UTF-8">\n {2}<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https:\/\/gc.zgo.at;/);
    expect(injectCsp('<head></head>', 'x')).toContain('<head>\n  <meta http-equiv="Content-Security-Policy" content="x">');
    expect(APP_CSP).not.toMatch(/unsafe-eval|script-src[^;]*unsafe-inline/);
  });
});

describe('generateSeo', () => {
  let root;
  let publicDir;
  let distDir;
  const quiet = { log: () => {}, warn: () => {} };
  const INDEX = `<html><body><div id="root">${PRERENDER_MARKER}</div></body></html>`;

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), 'ngj-seo-'));
    publicDir = join(root, 'public');
    distDir = join(root, 'dist');
    await mkdir(join(publicDir, 'descriptions'), { recursive: true });
    await mkdir(distDir, { recursive: true });
    await writeFile(join(distDir, 'index.html'), INDEX);
  });
  afterEach(() => rm(root, { recursive: true, force: true }));

  it('writes job pages, sitemap, robots and the prerendered list', async () => {
    const jobs = [
      JOB,
      { ...JOB, job_id: 'job_b00001', title: 'Remote Dev', location: 'Remote - US', posted_at: '2026-09-22T00:00:00Z' },
      { ...JOB, job_id: 'job_c00002', is_closed: true },
      { ...JOB, job_id: '../evil' },
      { ...JOB, job_id: 'job_d00003', location: 'Remote' },
    ];
    await writeFile(join(publicDir, 'jobs.json'), JSON.stringify({ meta: { generated_at: '2026-09-24T00:00:00Z' }, jobs }));
    await writeFile(join(publicDir, 'descriptions', 'a.json'), JSON.stringify({ job_a1b2c3: 'From the shard &amp; more.' }));

    const stats = await generateSeo({ publicDir, distDir, siteUrl: `${SITE}/`, prerenderLimit: 2, log: quiet });
    // Landing pages: hub + company (Acme, 3 roles) + remote (2) + new-this-week (3) = 4.
    expect(stats).toMatchObject({ jobPages: 3, jsonLd: 2, jsonLdSkipped: { 'unresolvable location': 1 }, landingPages: 4, sitemapUrls: 8, prerendered: 2 });
    expect((await readdir(join(distDir, 'job'))).sort()).toEqual(['job_a1b2c3', 'job_b00001', 'job_d00003']);

    const page = await readFile(join(distDir, 'job', 'job_a1b2c3', 'index.html'), 'utf8');
    expect(page).toContain('<p>From the shard &amp; more.</p>');
    const remote = JSON.parse(ldBlocks(await readFile(join(distDir, 'job', 'job_b00001', 'index.html'), 'utf8'))[0]);
    expect(remote.jobLocationType).toBe('TELECOMMUTE');
    expect(remote.applicantLocationRequirements).toEqual([{ '@type': 'Country', name: 'United States' }]);

    const index = await readFile(join(distDir, 'index.html'), 'utf8');
    expect(index).not.toContain(PRERENDER_MARKER);
    // Newest first: the remote job (09-22) precedes JOB (09-20).
    expect(index.indexOf('job_b00001')).toBeLessThan(index.indexOf('job_a1b2c3'));
    const sitemap = await readFile(join(distDir, 'sitemap.xml'), 'utf8');
    expect(sitemap.match(/<url>/g)).toHaveLength(8);
    expect(sitemap).toContain(`<loc>${SITE}/jobs/at/acme-corp/</loc>`);
    expect(sitemap).toContain(`<loc>${SITE}/</loc><lastmod>2026-09-24T00:00:00.000Z</lastmod>`);
    expect(existsSync(join(distDir, 'robots.txt'))).toBe(true);
  });

  it('falls back to jobs-index.json when jobs.json is missing or malformed', async () => {
    await writeFile(join(publicDir, 'jobs.json'), '{not json');
    await writeFile(join(publicDir, 'jobs-index.json'), JSON.stringify({ jobs: [JOB] }));
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: quiet });
    expect(stats.source).toBe('jobs-index.json');
    expect(stats.jobPages).toBe(1);
  });

  it('succeeds with no data: robots + home-only sitemap, marker removed, warning logged', async () => {
    const warnings = [];
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: { log: () => {}, warn: (m) => warnings.push(m) } });
    expect(stats).toMatchObject({ jobPages: 0, sitemapUrls: 1, prerendered: 0 });
    expect(warnings.join('\n')).toMatch(/no job data/);
    expect(existsSync(join(distDir, 'job'))).toBe(false);
    expect(await readFile(join(distDir, 'index.html'), 'utf8')).toBe('<html><body><div id="root"></div></body></html>');
    expect((await readFile(join(distDir, 'sitemap.xml'), 'utf8')).match(/<url>/g)).toHaveLength(1);
    expect(existsSync(join(distDir, 'robots.txt'))).toBe(true);
  });

  it('succeeds when dist/index.html is missing', async () => {
    await rm(join(distDir, 'index.html'));
    await writeFile(join(publicDir, 'jobs.json'), JSON.stringify({ jobs: [JOB] }));
    const warnings = [];
    const stats = await generateSeo({ publicDir, distDir, siteUrl: SITE, log: { log: () => {}, warn: (m) => warnings.push(m) } });
    expect(stats.jobPages).toBe(1);
    expect(warnings.join('\n')).toMatch(/index.html not found/);
  });
});
