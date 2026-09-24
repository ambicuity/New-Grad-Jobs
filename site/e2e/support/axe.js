// axe-core scan against WCAG 2.2 AA. The gate is zero serious/critical
// violations; every finding (any impact) is attached to the test report.
import AxeBuilder from '@axe-core/playwright';
import { expect } from './test.js';

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'];
const BLOCKING = new Set(['serious', 'critical']);

const MAX_NODES = 3;
const MAX_HTML = 160;
const summarize = (v) => `${v.impact} ${v.id}: ${v.help} — ${v.nodes.slice(0, MAX_NODES)
  .map((n) => `${n.target.join(' ')} ${n.html.slice(0, MAX_HTML)}`).join(' | ')}`;

export async function expectNoSeriousA11yViolations(page, testInfo, { include } = {}) {
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS);
  if (include) builder = builder.include(include);
  const results = await builder.analyze();
  await testInfo.attach('axe-violations', {
    body: JSON.stringify(results.violations, null, 2),
    contentType: 'application/json',
  });
  const blocking = results.violations.filter((v) => BLOCKING.has(v.impact)).map(summarize);
  expect(blocking, 'serious/critical WCAG 2.2 AA violations').toEqual([]);
}
