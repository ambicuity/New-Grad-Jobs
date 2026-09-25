// Canonical job categories — the single source of truth shared with
// scripts/ngj/taxonomy.py (CATEGORY_PATTERNS), jobs.json (meta.categories) and
// the README. tests/test_category_taxonomy_sync.py parses this file, so keep
// the object-literal shapes below (one `key: 'CODE'` pair per entry).

// Canonical category id (from jobs.json `job.category.id`) → short type code.
// This is the ONLY source of the terminal's type column/filters, so the site
// stays in step with meta.categories rather than re-deriving a taxonomy.
export const CATEGORY_TYPE = {
  software_engineering: 'SWE',
  frontend: 'FE',
  backend: 'BE',
  mobile: 'MOBILE',
  security: 'SEC',
  data_ml: 'ML',
  data_engineering: 'DATA',
  data_analyst: 'ANALYST',
  business_analyst: 'BIZ',
  infrastructure_sre: 'INFRA',
  product_management: 'PM',
  project_management: 'PROJ',
  quant_finance: 'QUANT',
  hardware: 'HW',
  engineering: 'ENG',
  design: 'DESIGN',
  marketing: 'MKT',
  sales: 'SALES',
  accounting_finance: 'FIN',
  consulting: 'CONSULT',
  human_resources: 'HR',
  legal: 'LEGAL',
  customer_support: 'SUPPORT',
  supply_chain: 'SUPPLY',
  healthcare: 'HEALTH',
  education: 'EDU',
  public_sector: 'GOV',
  arts_entertainment: 'ARTS',
  management: 'MGMT',
  other: 'OTHER',
};

export const TYPE_LABEL = {
  SWE: 'swe', FE: 'frontend', BE: 'backend', MOBILE: 'mobile', SEC: 'security', ML: 'ml', DATA: 'data eng',
  ANALYST: 'data analyst', BIZ: 'business analyst', INFRA: 'infra', PM: 'product', PROJ: 'project', QUANT: 'quant',
  HW: 'hardware', ENG: 'engineering', DESIGN: 'design', MKT: 'marketing', SALES: 'sales', FIN: 'finance',
  CONSULT: 'consulting', HR: 'hr', LEGAL: 'legal', SUPPORT: 'support', SUPPLY: 'supply chain', HEALTH: 'healthcare',
  EDU: 'education', GOV: 'government', ARTS: 'arts & media', MGMT: 'management', OTHER: 'other',
};

// Order of the ROLE filter chips: tech tracks first, then business functions.
export const TYPE_ORDER = [
  'SWE', 'FE', 'BE', 'MOBILE', 'SEC', 'ML', 'DATA', 'ANALYST', 'INFRA', 'PM', 'PROJ', 'QUANT', 'HW', 'ENG',
  'DESIGN', 'BIZ', 'MKT', 'SALES', 'FIN', 'CONSULT', 'HR', 'LEGAL', 'SUPPORT', 'SUPPLY', 'HEALTH', 'EDU', 'GOV',
  'ARTS', 'MGMT', 'OTHER',
];

// company_tier.tier exactly as the scraper publishes it. The feed has no
// headcount data, so the rail shows the tier itself rather than a size guess.
export const TIER_ORDER = ['faang_plus', 'unicorn', 'other'];
export const TIER_LABEL = { faang_plus: 'faang+', unicorn: 'unicorn', other: 'other' };

export const RMT_LABEL = { remote: 'remote', hybrid: 'hybrid', onsite: 'onsite' };
export const RMT_ORDER = ['remote', 'hybrid', 'onsite'];
