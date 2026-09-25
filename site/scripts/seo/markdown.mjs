// A deliberately small Markdown renderer for the repo's own guide content
// (site/content/guides/*.md). It covers what the guides use — headings,
// paragraphs, lists, blockquotes, bold, italics, inline code and links — and
// nothing else, so no dependency is needed. Every piece of text is escaped;
// link targets must be http(s) or a relative path with no scheme.

import { safeHttpUrl } from '../../src/lib/safe-url.js';
import { escapeHtml } from './text.mjs';

const FRONT_MATTER_RE = /^---\n([\s\S]*?)\n---\n?/;
const RELATIVE_URL_RE = /^(?:\.{1,2}\/|\/|#)[^\s"'<>]*$/;

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

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { flushAll(); continue; }
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      const text = heading[2].trim();
      headings.push({ level, text });
      out.push(`<h${level}>${renderInline(text)}</h${level}>`);
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
