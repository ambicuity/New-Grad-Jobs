// Display formatters shared by the terminal views.

/**
 * "$120–180k" for a [low, high] tuple in thousands; "—" when undisclosed.
 * @param {[number|null, number|null]|null|undefined} c
 */
export function fmtComp(c) {
  if (!Array.isArray(c) || c[0] == null || c[1] == null) return '—';
  return `$${c[0]}–${c[1]}k`;
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
