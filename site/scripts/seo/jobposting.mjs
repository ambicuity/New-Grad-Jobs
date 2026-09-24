// schema.org JobPosting for one job, per Google's job-posting structured data
// guidelines: required title, description, datePosted, hiringOrganization and
// jobLocation — or, for remote roles, jobLocationType=TELECOMMUTE plus
// applicantLocationRequirements. Returns null (and a reason) when a required
// property can't be filled honestly, so no page ships invalid markup.

import { escapeHtml, toParagraphs } from './text.mjs';
import { COUNTRY_NAME, parseLocation } from './location.mjs';

const JOB_ID_RE = /^[A-Za-z0-9_-]{1,80}$/;
const CURRENCY_RE = /^[A-Z]{3}$/;
// Ranges whose upper bound is below this are hourly rates, not annual salaries.
const HOURLY_MAX = 1000;

/** Job ids become directory names — only allow a strict, path-safe charset. */
export const isSafeJobId = (id) => typeof id === 'string' && JOB_ID_RE.test(id);

/**
 * posted_at as a Date. The scraper emits both "…Z" and naive
 * "2026-09-24T14:50:21.850000" timestamps; naive ones are UTC.
 */
export function parsePostedAt(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const v = value.trim();
  const hasZone = /(Z|[+-]\d\d:?\d\d)$/i.test(v);
  const withZone = hasZone || !v.includes('T') ? v : `${v.replace(/(\.\d{3})\d+/, '$1')}Z`;
  const d = new Date(withZone);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** employmentType only when the posting states it; never inferred from "new grad". */
export function employmentType(title, description) {
  const t = String(title || '');
  if (/\bintern(ship)?s?\b|\bco-?op\b/i.test(t)) return 'INTERN';
  if (/\bpart[- ]time\b/i.test(t)) return 'PART_TIME';
  if (/\b(contract|contractor)\b/i.test(t)) return 'CONTRACTOR';
  if (/\bfull[- ]time\b/i.test(t)) return 'FULL_TIME';
  const labelled = /(employment|job|role|position|work)\s+type\s*:?\s*(full|part)[- ]time/i.exec(String(description || ''));
  if (labelled) return labelled[2].toLowerCase() === 'full' ? 'FULL_TIME' : 'PART_TIME';
  return null;
}

/** baseSalary only when a range/amount *and* an ISO currency were disclosed. */
export function baseSalary(comp) {
  if (!comp || typeof comp !== 'object') return null;
  const currency = typeof comp.currency === 'string' ? comp.currency.toUpperCase() : '';
  if (!CURRENCY_RE.test(currency)) return null;
  const num = (x) => (typeof x === 'number' && Number.isFinite(x) && x > 0 ? x : null);
  const min = num(comp.min);
  const max = num(comp.max);
  if (min == null && max == null) return null;
  const unitText = (max ?? min) < HOURLY_MAX ? 'HOUR' : 'YEAR';
  const value = min != null && max != null && max !== min
    ? { '@type': 'QuantitativeValue', minValue: Math.min(min, max), maxValue: Math.max(min, max), unitText }
    : { '@type': 'QuantitativeValue', value: max ?? min, unitText };
  return { '@type': 'MonetaryAmount', currency, value };
}

const MAX_PLACES = 10;

function placeOf({ locality, region, country }) {
  const address = { '@type': 'PostalAddress' };
  if (locality) address.addressLocality = locality;
  if (region) address.addressRegion = region;
  if (country) address.addressCountry = country;
  return { '@type': 'Place', address };
}

/**
 * Location properties for the JobPosting, or null when none can be derived.
 * Remote roles need an applicant country; if the remote part names none we
 * fall back to the countries of any on-site locations in the same posting.
 */
export function locationProps(location) {
  const { remote, places, remoteCountries } = parseLocation(location);
  const props = {};
  if (places.length) props.jobLocation = places.slice(0, MAX_PLACES).map(placeOf);
  if (remote) {
    const countries = remoteCountries.length
      ? remoteCountries
      : [...new Set(places.map((p) => p.country).filter(Boolean))];
    if (countries.length) {
      props.jobLocationType = 'TELECOMMUTE';
      props.applicantLocationRequirements = countries.map((code) => ({ '@type': 'Country', name: COUNTRY_NAME[code] || code }));
    }
  }
  return props.jobLocation || props.jobLocationType ? props : null;
}

/** Description as HTML paragraphs (entity-escaped text) for JSON-LD and the page. */
export function descriptionHtml(paragraphs) {
  return paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join('\n');
}

/** Fallback copy when no description text was scraped. */
export function fallbackDescription(job) {
  const where = job.location ? ` in ${job.location}` : '';
  return `${job.title} at ${job.company}${where}. The full description is on the employer's application page.`;
}

/**
 * @param {object} job        raw job from jobs.json / jobs-index.json
 * @param {string} description plain-text description ('' when unknown)
 * @param {string} pageUrl    absolute canonical URL of the job page
 * @returns {{posting: object|null, reason?: string}}
 */
export function buildJobPosting(job, description, pageUrl) {
  if (!job || typeof job !== 'object') return { posting: null, reason: 'no job' };
  const title = typeof job.title === 'string' ? job.title.trim() : '';
  const company = typeof job.company === 'string' ? job.company.trim() : '';
  if (!title) return { posting: null, reason: 'missing title' };
  if (!company) return { posting: null, reason: 'missing company' };
  const posted = parsePostedAt(job.posted_at);
  if (!posted) return { posting: null, reason: 'missing datePosted' };
  const location = locationProps(job.location);
  if (!location) return { posting: null, reason: 'unresolvable location' };

  const paragraphs = toParagraphs(description);
  const html = descriptionHtml(paragraphs.length ? paragraphs : [fallbackDescription({ ...job, title, company })]);
  const posting = {
    '@context': 'https://schema.org/',
    '@type': 'JobPosting',
    title,
    description: html,
    datePosted: posted.toISOString(),
    hiringOrganization: { '@type': 'Organization', name: company },
    ...location,
    directApply: false,
    url: pageUrl,
  };
  if (isSafeJobId(job.job_id)) {
    posting.identifier = { '@type': 'PropertyValue', name: 'NGJ', value: job.job_id };
  }
  const type = employmentType(title, description);
  if (type) posting.employmentType = type;
  const salary = baseSalary(job.comp);
  if (salary) posting.baseSalary = salary;
  return { posting };
}
