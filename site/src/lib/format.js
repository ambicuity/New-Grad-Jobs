// Display formatters shared by the terminal views.

/**
 * "$120–180k" for a [low, high] tuple in thousands; "—" when undisclosed.
 * @param {[number|null, number|null]|null|undefined} c
 */
const COMP_PREFIX = { USD: '$', CAD: 'CA$', GBP: '£', EUR: '€' };
const LAKH_IN_THOUSANDS = 100;
const lakhs = (k) => String(Math.round((k / LAKH_IN_THOUSANDS) * 10) / 10);

/**
 * A posted range in thousands, labelled with its own currency: "$120–180k",
 * "CA$62–75k", "₹12–18L" (rupees in lakhs). Never converts between currencies.
 * @param {[number|null, number|null]} c
 * @param {string} [currency]  ISO code; USD when omitted.
 */
export function fmtComp(c, currency = 'USD') {
  if (!Array.isArray(c) || c[0] == null || c[1] == null) return '—';
  if (currency === 'INR') return `₹${lakhs(c[0])}–${lakhs(c[1])}L`;
  const prefix = COMP_PREFIX[currency];
  return prefix ? `${prefix}${c[0]}–${c[1]}k` : `${currency} ${c[0]}–${c[1]}k`;
}

/** Percentage of `part` in `whole`, or "—" when there is nothing to divide by. */
export function pct(part, whole) {
  return whole > 0 ? `${Math.round((100 * part) / whole)}%` : '—';
}

/** Compact thousands: 950 → "950", 1234 → "1.2k", 12345 → "12k". */
export function fmtK(n) {
  if (n == null) return '—';
  if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, '') + 'k';
  return n.toString();
}

/** 1-based row number, zero-padded to two digits ("01", "12", "123"). */
export function rowNumber(index) {
  return String(index + 1).padStart(2, '0');
}
