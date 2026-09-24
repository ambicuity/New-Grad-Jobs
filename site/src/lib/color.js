// WCAG 2.x relative luminance / contrast ratio, used by the theme tests to
// keep text colours at or above AA (4.5:1).

const HEX_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

function channel(v) {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

/** @param {string} hex  '#rgb' or '#rrggbb' */
export function relativeLuminance(hex) {
  const m = HEX_RE.exec(hex);
  if (!m) throw new Error(`not a hex colour: ${hex}`);
  const full = m[1].length === 3 ? m[1].split('').map((c) => c + c).join('') : m[1];
  const [r, g, b] = [0, 2, 4].map((i) => channel(parseInt(full.slice(i, i + 2), 16)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Contrast ratio between two colours (1–21), order-independent. */
export function contrastRatio(a, b) {
  const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
