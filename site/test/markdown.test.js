import { describe, expect, it } from 'vitest';
import { EVIDENCE_LEVELS, evidenceLevel, hasEvidenceBlocks, parseFrontMatter, renderInline, renderMarkdown } from '../scripts/seo/markdown.mjs';

describe('parseFrontMatter', () => {
  it('splits key: value front matter from the body', () => {
    const { meta, body } = parseFrontMatter('---\ntitle: Hello\ndescription: "A thing"\nupdated: 2026-09-25\n---\n# Hi\n');
    expect(meta).toEqual({ title: 'Hello', description: 'A thing', updated: '2026-09-25' });
    expect(body).toBe('# Hi\n');
  });

  it('returns an empty meta without front matter', () => {
    expect(parseFrontMatter('just text')).toEqual({ meta: {}, body: 'just text' });
    expect(parseFrontMatter(null)).toEqual({ meta: {}, body: '' });
  });
});

describe('renderInline', () => {
  it('escapes HTML before applying markup', () => {
    expect(renderInline('<b>x</b> **bold** _it_ `co<de>`')).toBe('&lt;b&gt;x&lt;/b&gt; <strong>bold</strong> <em>it</em> <code>co&lt;de&gt;</code>');
  });

  it('links only to http(s) or relative targets', () => {
    expect(renderInline('[site](https://example.test/a)')).toBe('<a href="https://example.test/a" rel="noopener noreferrer">site</a>');
    expect(renderInline('[board](../../jobs/)')).toBe('<a href="../../jobs/">board</a>');
    expect(renderInline('[bad](javascript:alert(1))')).toBe('bad');
    expect(renderInline('[bad](data:text/html,x)')).toBe('bad');
  });

  it('does not treat snake_case as italics', () => {
    expect(renderInline('use job_id and first_seen')).toBe('use job_id and first_seen');
  });

  it('preserves query parameters in source links without double-escaping ampersands', () => {
    expect(renderInline('[source](https://example.test/?id=1&lang=en)'))
      .toBe('<a href="https://example.test/?id=1&amp;lang=en" rel="noopener noreferrer">source</a>');
    expect(renderInline('[source](https://example.test/?id=1&literal=&quot;)'))
      .toContain('href="https://example.test/?id=1&amp;literal=&amp;quot;"');
  });
});

describe('renderMarkdown', () => {
  it('renders headings, paragraphs, lists and quotes', () => {
    const { html, headings } = renderMarkdown('# Title\n\nOne line\nsame para.\n\n- a\n- b\n\n1. x\n2) y\n\n> note\n\n## Sub');
    expect(html).toBe([
      '<h1 id="title">Title</h1>',
      '<p>One line same para.</p>',
      '<ul>\n<li>a</li>\n<li>b</li>\n</ul>',
      '<ol>\n<li>x</li>\n<li>y</li>\n</ol>',
      '<blockquote><p>note</p></blockquote>',
      '<h2 id="sub">Sub</h2>',
    ].join('\n'));
    expect(headings).toEqual([{ level: 1, text: 'Title' }, { level: 2, text: 'Sub' }]);
  });

  it('never emits raw HTML from the source', () => {
    const { html } = renderMarkdown('<script>alert(1)</script>\n\n- <img src=x>');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
    expect(html).toContain('<li>&lt;img src=x&gt;</li>');
  });

  it('handles empty input', () => {
    expect(renderMarkdown('')).toEqual({ html: '', headings: [] });
  });
});

describe('tables', () => {
  it('preserves a heading or paragraph immediately after a table', () => {
    for (const following of ['## Next step', 'Read the next step.']) {
      const { html } = renderMarkdown(`| A | B |\n| --- | --- |\n| 1 | 2 |\n${following}\n`);
      expect(html).toContain(following.startsWith('##')
        ? '<h2 id="next-step">Next step</h2>' : '<p>Read the next step.</p>');
    }
  });

  it('renders a pipe table with thead and tbody', () => {
    const { html } = renderMarkdown('| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n');
    expect(html).toContain('<table>');
    expect(html).toContain('<thead>');
    expect(html).toContain('<th>A</th>');
    expect(html).toContain('<th>B</th>');
    expect(html).toContain('<tbody>');
    expect(html).toContain('<td>1</td>');
    expect(html).toContain('<td>4</td>');
    expect(html).toContain('</table>');
  });

  it('honours column alignment markers', () => {
    const { html } = renderMarkdown('| L | C | R |\n| :--- | :---: | ---: |\n| a | b | c |\n');
    expect(html).toContain('style="text-align:left"');
    expect(html).toContain('style="text-align:center"');
    expect(html).toContain('style="text-align:right"');
  });

  it('does not mistake a single pipe line for a table without a delimiter row', () => {
    const { html } = renderMarkdown('not | a | table\nwithout | a | delimiter\n\nmore text\n');
    expect(html).not.toContain('<table>');
    expect(html).toContain('<p>not | a | table without | a | delimiter</p>');
  });

  it('escapes cell content and runs inline markup inside cells', () => {
    const { html } = renderMarkdown('| x | y |\n| --- | --- |\n| <b>html</b> | **bold** |\n');
    expect(html).not.toContain('<b>html</b>');
    expect(html).toContain('&lt;b&gt;html&lt;/b&gt;');
    expect(html).toContain('<strong>bold</strong>');
  });
});

describe('heading anchors', () => {
  it('generates a slugged id from the heading text', () => {
    const { html } = renderMarkdown('## Why this Company?\n\nbody\n');
    expect(html).toContain('<h2 id="why-this-company">Why this Company?</h2>');
  });

  it('strips diacritics, punctuation and collapses whitespace', () => {
    const { html } = renderMarkdown('# Études & Stages — 2026!\n');
    expect(html).toContain('id="etudes-stages-2026"');
  });

  it('produces matching ids for headings and the in-page fragments that link to them', () => {
    const src = '## Step 1\n\nbody\n\nSee [Step 1](#step-1) below.\n';
    const { html } = renderMarkdown(src);
    expect(html).toContain('id="step-1"');
    expect(html).toContain('href="#step-1"');
  });
});

describe('evidence levels', () => {
  it('exposes the canonical level order, ids and swatches', () => {
    expect(EVIDENCE_LEVELS.map((l) => l.id)).toEqual(['official', 'primary', 'observational', 'practical', 'candidate']);
    expect(evidenceLevel('official')).toMatchObject({ id: 'official', label: 'OFFICIAL' });
    expect(evidenceLevel('nope')).toBeNull();
  });

  it('detects whether a body uses evidence blocks', () => {
    expect(hasEvidenceBlocks('')).toBe(false);
    expect(hasEvidenceBlocks('plain text\nno markers\n')).toBe(false);
    expect(hasEvidenceBlocks('::: evidence official\nUSCIS page\n:::\n')).toBe(true);
  });

  it('renders an evidence block as an <aside> with the right level, badge and body', () => {
    const { html } = renderMarkdown('::: evidence official\nUSCIS lists 12 months of OPT.\n:::\n');
    expect(html).toContain('<aside class="evidence" data-evidence="official"');
    expect(html).toContain('OFFICIAL');
    expect(html).toContain('USCIS lists 12 months of OPT.');
    expect(html).toContain('class="evidence-swatch"');
    expect(html).not.toContain('<blockquote');
  });

  it('renders every supported level with its own swatch colour', () => {
    for (const level of EVIDENCE_LEVELS) {
      const { html } = renderMarkdown(`::: evidence ${level.id}\nx\n:::\n`);
      expect(html).toContain(`data-evidence="${level.id}"`);
      expect(html).toContain(level.label);
    }
  });

  it('keeps evidence blocks after lists, paragraphs and headings', () => {
    const src = [
      '## Heading',
      '',
      '- one',
      '- two',
      '',
      '::: evidence practical',
      'A workflow you should try.',
      ':::',
      '',
      'More text.',
    ].join('\n');
    const { html } = renderMarkdown(src);
    expect(html.indexOf('<h2 id="heading">Heading</h2>')).toBeGreaterThan(-1);
    expect(html.indexOf('<li>one</li>')).toBeGreaterThan(-1);
    expect(html.indexOf('data-evidence="practical"')).toBeGreaterThan(html.indexOf('<li>two</li>'));
    expect(html.indexOf('<p>More text.</p>')).toBeGreaterThan(html.indexOf('data-evidence="practical"'));
  });

  it('renders an unknown level as a blockquote with a visible warning', () => {
    const { html } = renderMarkdown('::: evidence bogus\ntext\n:::\n');
    expect(html).toContain('<blockquote class="evidence-unknown">');
    expect(html).toContain('Evidence level "bogus" not recognised.');
  });

  it('escapes the level id and body, never emits raw HTML', () => {
    const { html } = renderMarkdown('::: evidence official\n<script>alert(1)</script>\n:::\n');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
  });
});
