import { describe, expect, it } from 'vitest';
import { parseFrontMatter, renderInline, renderMarkdown } from '../scripts/seo/markdown.mjs';

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
});

describe('renderMarkdown', () => {
  it('renders headings, paragraphs, lists and quotes', () => {
    const { html, headings } = renderMarkdown('# Title\n\nOne line\nsame para.\n\n- a\n- b\n\n1. x\n2) y\n\n> note\n\n## Sub');
    expect(html).toBe([
      '<h1>Title</h1>',
      '<p>One line same para.</p>',
      '<ul>\n<li>a</li>\n<li>b</li>\n</ul>',
      '<ol>\n<li>x</li>\n<li>y</li>\n</ol>',
      '<blockquote><p>note</p></blockquote>',
      '<h2>Sub</h2>',
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
