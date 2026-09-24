// Canonical job categories — the single source of truth shared with
// scripts/update_jobs.py (CATEGORY_PATTERNS), jobs.json (meta.categories) and
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
  infrastructure_sre: 'INFRA',
  product_management: 'PM',
  quant_finance: 'QUANT',
  hardware: 'HW',
  other: 'OTHER',
};

export const TYPE_LABEL = { SWE: 'swe', FE: 'frontend', BE: 'backend', MOBILE: 'mobile', SEC: 'security', ML: 'ml', DATA: 'data', INFRA: 'infra', PM: 'product', QUANT: 'quant', HW: 'hardware', OTHER: 'other' };

// Order of the ROLE filter chips.
export const TYPE_ORDER = ['SWE', 'FE', 'BE', 'MOBILE', 'SEC', 'ML', 'DATA', 'INFRA', 'PM', 'QUANT', 'HW', 'OTHER'];

export const SIZE_LABEL = { S: '<50', M: '50–500', L: '500–5k', XL: '5k+' };
export const SIZE_ORDER = ['S', 'M', 'L', 'XL'];

export const RMT_LABEL = { remote: 'remote', hybrid: 'hybrid', onsite: 'onsite' };
export const RMT_ORDER = ['remote', 'hybrid', 'onsite'];

// company_tier.tier → company-size bucket.
export const TIER_SIZE = {
  faang_plus: 'XL',
  unicorn: 'L',
  other: 'M',
};
