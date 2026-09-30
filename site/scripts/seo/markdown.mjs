// A deliberately small Markdown renderer for the repo's own guide content
// (site/content/guides/*.md). It covers what the guides use — headings,
// paragraphs, lists, blockquotes, bold, italics, inline code and links — and
// nothing else, so no dependency is needed. Every piece of text is escaped;
// link targets must be http(s) or a relative path with no scheme.

import { safeHttpUrl } from '../../src/lib/safe-url.js';
import { escapeHtml } from './text.mjs';

const FRONT_MATTER_RE = /^---\n([\s\S]*?)\n---\n?/;
const RELATIVE_URL_RE = /^(?:\.{1,2}\/|\/|#)[^\s"'<>]*$/;
const TABLE_DELIM_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/;
const TABLE_ROW_RE = /\|/;

/** Split optional `---` front matter (key: value lines) from the body. */
export function parseFrontMatter(source) {
  const text = String(source ?? '').replace(/\r\n/g, '\n');
  const m = FRONT_MATTER_RE.exec(text);
  if (!m) return { meta: {}, body: text };
  const meta = {};
  for (const line of m[1].split('\n')) {
    const idx = line.indexOf(':');
    if (idx > 0) meta[line.slice(0, idx).trim()] = line.slice(idx + 1).trim().replace(/^["']|["']$/g, '');
  }
  return { meta, body: text.slice(m[0].length) };
}

function safeHref(target) {
  const t = String(target || '').trim();
  return safeHttpUrl(t) || (RELATIVE_URL_RE.test(t) ? t : null);
}

/** Inline markup on already-escaped text: code, bold, italics, links. */
export function renderInline(text) {
  let out = escapeHtml(text);
  out = out.replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`);
  // One level of parentheses inside the target ("javascript:alert(1)") is consumed so the link is rejected whole.
  out = out.replace(/\[([^\]]+)\]\(([^()\s]*(?:\([^()\s]*\))?[^()\s]*)\)/g, (whole, label, target) => {
    const href = safeHref(target);
    if (!href) return label;
    const external = /^https?:/i.test(href);
    return `<a href="${escapeHtml(href)}"${external ? ' rel="noopener noreferrer"' : ''}>${label}</a>`;
  });
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[\s(])_([^_]+)_(?=[\s.,;:!?)]|$)/g, '$1<em>$2</em>');
  return out;
}

/** Evidence levels for cited claims. Order matches the badge colour ramp (best evidence first). */
export const EVIDENCE_LEVELS = Object.freeze([
  { id: 'official', label: 'OFFICIAL', swatch: '#5fd28a', description: 'USCIS / DHS / FTC / BLS / employer policy' },
  { id: 'primary', label: 'PRIMARY SOURCE', swatch: '#62a3ff', description: 'Company careers page / actual job posting' },
  { id: 'observational', label: 'OBSERVATIONAL', swatch: '#e8c443', description: 'Patterns observed from job postings/data' },
  { id: 'practical', label: 'PRACTICAL ADVICE', swatch: '#ff9d3d', description: 'Recommended workflow' },
  { id: 'candidate', label: 'CANDIDATE EXPERIENCE', swatch: '#c084fc', description: 'Anecdotal / community experience' },
]);

const EVIDENCE_BLOCK_RE = /^:::\s*evidence\s+([a-z]+)\s*$/;

/** Look up the badge info for a level id; returns null for unknown levels. */
export function evidenceLevel(id) {
  const found = EVIDENCE_LEVELS.find((l) => l.id === id);
  return found || null;
}

/** True if the source uses `::: evidence <level>` blocks (used by the renderer). */
export function hasEvidenceBlocks(body) {
  return EVIDENCE_BLOCK_RE.test(String(body ?? '').split('\n', 1)[0]) || /(^|\n):::\s*evidence\s+[a-z]+\s*\n/.test(String(body ?? ''));
}

/**
 * Render a Markdown body to HTML.
 * @returns {{html: string, headings: {level: number, text: string}[]}}
 */
export function renderMarkdown(body) {
  const lines = String(body ?? '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  const headings = [];
  let para = [];
  let list = null; // { tag: 'ul'|'ol', items: string[] }
  let quote = [];

  const flushPara = () => {
    if (para.length) out.push(`<p>${renderInline(para.join(' '))}</p>`);
    para = [];
  };
  const flushList = () => {
    if (list) out.push(`<${list.tag}>\n${list.items.map((i) => `<li>${renderInline(i)}</li>`).join('\n')}\n</${list.tag}>`);
    list = null;
  };
  const flushQuote = () => {
    if (quote.length) out.push(`<blockquote><p>${renderInline(quote.join(' '))}</p></blockquote>`);
    quote = [];
  };
  const flushAll = () => { flushPara(); flushList(); flushQuote(); };

  /** A heading slug the build, the index, and the in-page fragments all agree on. */
  const slugifyHeading = (text) => {
    const ascii = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
    return ascii.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  };

  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i];
    const line = raw.trimEnd();
    if (!line.trim()) { flushAll(); continue; }
    // Pipe table: a header row, a delimiter row, then one or more body rows.
    // Detect by peeking at the next non-blank line and confirming it is the
    // delimiter pattern (`| --- | --- |`).
    if (TABLE_ROW_RE.test(line)) {
      const next = (lines[i + 1] || '').trimEnd();
      if (TABLE_DELIM_RE.test(next)) {
        flushAll();
        const splitCells = (row) => row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
        const header = splitCells(line);
        const aligns = splitCells(next).map((c) => {
          const left = c.startsWith(':');
          const right = c.endsWith(':');
          if (left && right) return 'center';
          if (right) return 'right';
          if (left) return 'left';
          return null;
        });
        const body = [];
        i += 2;
        while (i < lines.length) {
          const cur = lines[i].trimEnd();
          if (!cur.trim()) break;
          if (!TABLE_ROW_RE.test(cur)) break;
          body.push(splitCells(cur));
          i += 1;
        }
        const alignAttr = (a) => a ? ` style="text-align:${a}"` : '';
        const renderRow = (cells, tag) => `<tr>${cells.map((c, idx) => `<${tag}${alignAttr(aligns[idx])}>${renderInline(c)}</${tag}>`).join('')}</tr>`;
        out.push(`<table>\n<thead>\n${renderRow(header, 'th')}\n</thead>\n${body.length ? `<tbody>\n${body.map((r) => renderRow(r, 'td')).join('\n')}\n</tbody>` : ''}\n</table>`);
        continue;
      }
    }
    // Evidence block: opens with `::: evidence <level>` and closes on the next `:::` line.
    const evOpen = EVIDENCE_BLOCK_RE.exec(line);
    if (evOpen) {
      flushAll();
      const level = evOpen[1];
      const levelInfo = evidenceLevel(level);
      const evLines = [];
      i += 1;
      while (i < lines.length) {
        const cur = lines[i].trimEnd();
        if (cur.trim() === ':::') break;
        evLines.push(cur);
        i += 1;
      }
      const inner = evLines.join('\n').trim();
      // If the level id is unknown, render the block as a plain blockquote so
      // a typo never silently disappears.
      const body = inner
        ? `<p>${renderInline(inner.replace(/\n+/g, ' '))}</p>`
        : '';
      if (levelInfo) {
        out.push(
          `<aside class="evidence" data-evidence="${escapeHtml(levelInfo.id)}" aria-label="Evidence level: ${escapeHtml(levelInfo.label)}">`
          + `<span class="evidence-badge"><span class="evidence-swatch" aria-hidden="true"></span>${escapeHtml(levelInfo.label)}</span>`
          + `<span class="evidence-body">${body}</span>`
          + `<span class="evidence-desc">${escapeHtml(levelInfo.description)}</span>`
          + `</aside>`,
        );
      } else if (body) {
        out.push(`<blockquote class="evidence-unknown">${body}<p class="dim">Evidence level "${escapeHtml(level)}" not recognised.</p></blockquote>`);
      }
      continue;
    }
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      const text = heading[2].trim();
      headings.push({ level, text });
      const id = slugifyHeading(text);
      out.push(`<h${level}${id ? ` id="${escapeHtml(id)}"` : ''}>${renderInline(text)}</h${level}>`);
      continue;
    }
    const bullet = /^\s*[-*]\s+(.+)$/.exec(line);
    const number = /^\s*\d+[.)]\s+(.+)$/.exec(line);
    if (bullet || number) {
      flushPara(); flushQuote();
      const tag = bullet ? 'ul' : 'ol';
      if (!list || list.tag !== tag) { flushList(); list = { tag, items: [] }; }
      list.items.push((bullet || number)[1].trim());
      continue;
    }
    if (line.startsWith('>')) {
      flushPara(); flushList();
      quote.push(line.replace(/^>\s?/, '').trim());
      continue;
    }
    flushList(); flushQuote();
    para.push(line.trim());
  }
  flushAll();
  return { html: out.join('\n'), headings };
}
