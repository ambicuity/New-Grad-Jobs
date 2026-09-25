// Best-effort parsing of free-text scraped job locations ("Toronto, ON, CA",
// "Remote - US", "United States-California-Sunnyvale", "SF, CA | NYC, NY")
// into the structured pieces schema.org JobPosting wants. Anything we can't
// place confidently is left out rather than guessed.

// [ISO code, display name, ...aliases (lowercase)]
const COUNTRIES = [
  ['US', 'United States', 'united states of america', 'united states', 'usa', 'u.s.a.', 'u.s.', 'us', 'puerto rico'],
  ['CA', 'Canada', 'canada'],
  ['GB', 'United Kingdom', 'united kingdom', 'uk', 'england', 'scotland', 'wales', 'great britain'],
  ['IE', 'Ireland', 'ireland'], ['ES', 'Spain', 'spain'], ['CO', 'Colombia', 'colombia'],
  ['PL', 'Poland', 'poland'], ['MX', 'Mexico', 'mexico'], ['SG', 'Singapore', 'singapore'],
  ['BR', 'Brazil', 'brazil'], ['IN', 'India', 'india'], ['AU', 'Australia', 'australia'],
  ['IL', 'Israel', 'israel'], ['DE', 'Germany', 'germany'], ['FR', 'France', 'france'],
  ['NL', 'Netherlands', 'netherlands'], ['JP', 'Japan', 'japan'], ['CN', 'China', 'china'],
  ['KR', 'South Korea', 'south korea', 'korea'], ['TW', 'Taiwan', 'taiwan'],
  ['CH', 'Switzerland', 'switzerland'], ['SE', 'Sweden', 'sweden'], ['PT', 'Portugal', 'portugal'],
  ['AR', 'Argentina', 'argentina'], ['PH', 'Philippines', 'philippines'], ['RO', 'Romania', 'romania'],
  ['CZ', 'Czechia', 'czech republic', 'czechia'], ['HK', 'Hong Kong', 'hong kong'],
  ['NZ', 'New Zealand', 'new zealand'], ['AE', 'United Arab Emirates', 'united arab emirates', 'uae'],
  ['IT', 'Italy', 'italy'], ['BE', 'Belgium', 'belgium'], ['DK', 'Denmark', 'denmark'],
  ['NO', 'Norway', 'norway'], ['FI', 'Finland', 'finland'], ['AT', 'Austria', 'austria'],
  ['VN', 'Vietnam', 'vietnam'], ['MY', 'Malaysia', 'malaysia'], ['ID', 'Indonesia', 'indonesia'],
  ['TH', 'Thailand', 'thailand'], ['EG', 'Egypt', 'egypt'], ['NG', 'Nigeria', 'nigeria'],
  ['KE', 'Kenya', 'kenya'], ['ZA', 'South Africa', 'south africa'], ['CL', 'Chile', 'chile'],
  ['PE', 'Peru', 'peru'], ['UA', 'Ukraine', 'ukraine'], ['GR', 'Greece', 'greece'],
  ['HU', 'Hungary', 'hungary'], ['EE', 'Estonia', 'estonia'], ['LT', 'Lithuania', 'lithuania'],
];

export const COUNTRY_NAME = Object.freeze(Object.fromEntries(COUNTRIES.map(([code, name]) => [code, name])));

// Longest alias first so "united states of america" wins over "united states".
const COUNTRY_ALIASES = COUNTRIES
  .flatMap(([code, , ...aliases]) => aliases.map((alias) => ({ code, alias })))
  .sort((a, b) => b.alias.length - a.alias.length);

const US_STATES = {
  AL: 'alabama', AK: 'alaska', AZ: 'arizona', AR: 'arkansas', CA: 'california', CO: 'colorado',
  CT: 'connecticut', DE: 'delaware', FL: 'florida', GA: 'georgia', HI: 'hawaii', ID: 'idaho',
  IL: 'illinois', IN: 'indiana', IA: 'iowa', KS: 'kansas', KY: 'kentucky', LA: 'louisiana',
  ME: 'maine', MD: 'maryland', MA: 'massachusetts', MI: 'michigan', MN: 'minnesota',
  MS: 'mississippi', MO: 'missouri', MT: 'montana', NE: 'nebraska', NV: 'nevada',
  NH: 'new hampshire', NJ: 'new jersey', NM: 'new mexico', NY: 'new york', NC: 'north carolina',
  ND: 'north dakota', OH: 'ohio', OK: 'oklahoma', OR: 'oregon', PA: 'pennsylvania',
  RI: 'rhode island', SC: 'south carolina', SD: 'south dakota', TN: 'tennessee', TX: 'texas',
  UT: 'utah', VT: 'vermont', VA: 'virginia', WA: 'washington', WV: 'west virginia',
  WI: 'wisconsin', WY: 'wyoming', DC: 'district of columbia',
};
const CA_PROVINCES = {
  AB: 'alberta', BC: 'british columbia', MB: 'manitoba', NB: 'new brunswick',
  NL: 'newfoundland and labrador', NS: 'nova scotia', ON: 'ontario', PE: 'prince edward island',
  QC: 'quebec', SK: 'saskatchewan',
};

const US_STATE_NAMES = new Set(Object.values(US_STATES));
const CA_PROVINCE_NAMES = new Set(Object.values(CA_PROVINCES));
const REGION_CODE_BY_NAME = new Map([
  ...Object.entries(US_STATES).map(([code, name]) => [name, code]),
  ...Object.entries(CA_PROVINCES).map(([code, name]) => [name, code]),
]);

/** Two-letter US state / Canadian province code for a code or full name, else null. */
export function regionCode(region) {
  if (typeof region !== 'string' || !region.trim()) return null;
  const upper = region.trim().toUpperCase();
  if (upper.length === 2 && (US_STATES[upper] || CA_PROVINCES[upper])) return upper;
  return REGION_CODE_BY_NAME.get(region.trim().toLowerCase()) || null;
}
const WORK_MODE_WORDS = /\b(remote|hybrid|on-?site|in[- ]office|flexible|friendly|hq|preferred|select locations|amer|apac|emea|latam)\b/gi;

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const aliasRe = new Map(COUNTRY_ALIASES.map(({ alias }) => [alias, new RegExp(`(^|[^a-z])${escapeRe(alias)}($|[^a-z])`, 'i')]));

export const isRemoteText = (text) => /\bremote\b/i.test(text || '') && !/\bremote[- ]friendly\b/i.test(text || '');

/** Split a multi-location string into individual segments. */
export function splitLocations(location) {
  return String(location || '')
    .split(/\s*(?:;|\||•|·|\/|\bor\b)\s*/i)
    .map((s) => s.trim())
    .filter(Boolean);
}

function countryFromAliases(segment) {
  // Two-letter aliases ("us", "uk") are only trusted as standalone uppercase tokens.
  for (const { code, alias } of COUNTRY_ALIASES) {
    if (alias.length <= 3 && !alias.includes('.')) {
      if (new RegExp(`(^|[^A-Za-z])${alias.toUpperCase()}($|[^A-Za-z])`).test(segment)) return code;
    } else if (aliasRe.get(alias).test(segment)) {
      return code;
    }
  }
  return null;
}

const tokensOf = (segment) => segment
  .replace(/\([^)]*\)/g, (m) => ` ${m.slice(1, -1)} `)
  .split(/\s*,\s*|\s+-\s+|(?<=[a-z])-(?=[A-Z])|:\s*/)
  .map((t) => t.replace(WORK_MODE_WORDS, ' ').replace(/[-–]+/g, ' ').replace(/\s+/g, ' ').trim())
  .filter(Boolean);

/**
 * Parse one location segment.
 * @returns {{locality?: string, region?: string, country?: string, remote: boolean}}
 */
export function parseSegment(segment) {
  const remote = isRemoteText(segment);
  const tokens = tokensOf(segment);
  let country = countryFromAliases(segment);
  let region;
  let locality;
  for (const tok of tokens) {
    const lower = tok.toLowerCase();
    const upper = tok.toUpperCase();
    const isCountry = COUNTRY_ALIASES.some(({ alias }) => alias === lower) || lower === 'united states of america';
    if (isCountry) continue;
    if (!region && tok.length === 2 && tok === upper && (US_STATES[upper] || CA_PROVINCES[upper])) {
      // "CA" is California unless a Canadian province was already seen.
      region = upper;
      continue;
    }
    if (!region && (US_STATE_NAMES.has(lower) || CA_PROVINCE_NAMES.has(lower))) {
      region = tok;
      continue;
    }
    if (!locality && /[a-z]/i.test(tok) && tok.length > 1) locality = tok;
  }
  // Region → country when no explicit country was named.
  if (region) {
    const upper = region.toUpperCase();
    const lower = region.toLowerCase();
    const isProvince = CA_PROVINCES[upper] || CA_PROVINCE_NAMES.has(lower);
    const isState = US_STATES[upper] || US_STATE_NAMES.has(lower);
    if (!country) country = isState && !(isProvince && !US_STATES[upper]) ? 'US' : isProvince ? 'CA' : null;
    // "Toronto, ON, CA": trailing "CA" after a province is Canada, not California.
    if (country === 'US' && isProvince && !isState) country = 'CA';
  }
  // "New York, NY": the city shares its name with the state, so the first token
  // was read as the region and the code as the locality. Put them back.
  if (locality && region && locality.length === 2 && locality === locality.toUpperCase()
    && (US_STATES[locality] || CA_PROVINCES[locality]) && region.length > 2) {
    [locality, region] = [region, locality];
  }
  const out = { remote };
  if (locality) out.locality = locality;
  if (region) out.region = region;
  if (country) out.country = country;
  return out;
}

/**
 * Structured view of a job's location string.
 * @returns {{remote: boolean, places: {locality?: string, region?: string, country?: string}[], remoteCountries: string[]}}
 */
export function parseLocation(location) {
  const segments = splitLocations(location).map(parseSegment);
  const places = segments
    .filter((s) => !s.remote && (s.locality || s.country))
    .map(({ locality, region, country }) => ({ locality, region, country }));
  const remoteSegs = segments.filter((s) => s.remote);
  const remoteCountries = [...new Set(remoteSegs.map((s) => s.country).filter(Boolean))];
  return { remote: remoteSegs.length > 0, places, remoteCountries };
}
