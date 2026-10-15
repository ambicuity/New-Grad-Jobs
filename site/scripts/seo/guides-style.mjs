// Stylesheet and CSP for the /guides/ index and guide pages. The shared static
// page CSS plus the guides layout: cards, reading paths, the 30-second brief,
// a sticky "On this page" column on wide screens. System fonts only (monospace
// for chrome, the system sans for long-form text), no web fonts, no CDN.
// The CSP is the static-page one plus our own same-origin script (guides.js),
// which only filters the list and remembers read/saved guides in localStorage.

import { createHash } from 'node:crypto';
import { JOB_PAGE_CSS } from './render.mjs';

const SANS = 'system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';

const GUIDE_CSS = [
  'main.wide{max-width:1180px}',
  // Author display rules (grid, flex) would otherwise override the hidden attribute.
  '[hidden]{display:none!important}',
  '.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}',
  `.prose,.card .summary,.lede,.hero p,.path-body p,.brief p{font-family:${SANS}}`,
  '.hero{border-bottom:1px solid #2a2a2a;padding-bottom:16px;margin-bottom:18px}',
  '.hero h1{font-size:26px;margin-bottom:8px}',
  '.hero p{font-size:15px;line-height:1.6;color:#c8c8c8;max-width:760px;margin:0 0 8px}',
  '.hero p.stats{font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#8a8a8a;letter-spacing:.4px}',
  '.panel{border:1px solid #2a2a2a;background:#0a0a0a;padding:12px 14px;margin:0 0 14px}',
  '.panel-h{font-size:12px;font-weight:700;letter-spacing:.8px;color:#ff9d3d;margin:0 0 10px}',
  // Reading paths: a wrap of chip-like <summary> elements; the open one spans the row.
  '.path-list{display:flex;flex-wrap:wrap;gap:8px}',
  '.path{border:1px solid #3a3a3a;background:#000}',
  '.path[open]{flex-basis:100%;border-color:#ff9d3d}',
  '.path summary{cursor:pointer;list-style:none;padding:5px 10px;min-height:32px;display:flex;align-items:center;gap:8px;font-size:13px}',
  '.path summary::-webkit-details-marker{display:none}',
  '.path[open] summary{background:#ff9d3d;color:#000;font-weight:700}',
  '.path summary .n{color:#8a8a8a;font-size:11px}',
  '.path[open] summary .n{color:#000}',
  '.path-body{padding:10px 14px 12px}',
  '.path-body p{margin:0 0 8px;color:#c8c8c8;font-size:14px}',
  '.path-body ol{margin:0;padding-left:22px}',
  '.path-body li{margin:0 0 6px}',
  '.path-body .dim{font-size:12px}',
  // Toolbar (revealed by guides.js).
  '.toolbar{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center;margin:0 0 12px}',
  '.toolbar input,.toolbar select{font:inherit;color:#e8e8e8;background:#0a0a0a;border:1px solid #3a3a3a;padding:8px 10px;min-height:38px;width:100%}',
  '.toolbar input:focus-visible,.toolbar select:focus-visible,button:focus-visible,summary:focus-visible{outline:1px solid #ff9d3d;outline-offset:2px}',
  '.views{display:flex;border:1px solid #3a3a3a}',
  '.views button{font:inherit;font-size:12px;background:#000;color:#c8c8c8;border:0;border-right:1px solid #3a3a3a;padding:8px 10px;min-height:38px;cursor:pointer;white-space:nowrap}',
  '.views button:last-child{border-right:0}',
  '.views button[aria-pressed=true]{background:#ff9d3d;color:#000;font-weight:700}',
  '.progress{font-size:12px;color:#8a8a8a;margin:0 0 10px}',
  '.progress strong{color:#5fd28a}',
  // Section chips: one scrolling row.
  '.chips{display:flex;gap:6px;overflow-x:auto;padding:0 0 8px;margin:0 0 6px;scrollbar-width:thin}',
  '.chips a{flex:none;display:inline-flex;align-items:center;min-height:30px;padding:0 10px;border:1px solid #2a2a2a;color:#c8c8c8;text-decoration:none;font-size:12px;white-space:nowrap}',
  '.chips a:hover{border-color:#ff9d3d;color:#ff9d3d}',
  '.chips .n{color:#8a8a8a;margin-left:6px}',
  '.count{font-size:12px;color:#8a8a8a;margin:6px 0 10px}',
  '.empty{border:1px dashed #3a3a3a;padding:16px;margin:0 0 16px;text-align:center}',
  '.linkish{font:inherit;background:none;border:0;color:#ff9d3d;text-decoration:underline;cursor:pointer;padding:4px}',
  // Sections and cards.
  '.sec{margin:0 0 10px;scroll-margin-top:12px}',
  '.sec>details>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;border-bottom:1px solid #2a2a2a;padding:8px 0;margin:14px 0 10px}',
  '.sec>details>summary::-webkit-details-marker{display:none}',
  '.sec>details>summary::before{content:"▸";color:#ff9d3d;font-size:12px}',
  '.sec>details[open]>summary::before{content:"▾"}',
  '.sec h2{margin:0;border:0;padding:0;color:#ff9d3d;font-size:12px}',
  '.sec h2 .n{color:#8a8a8a;font-weight:400}',
  '.cards{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:10px}',
  '.card{position:relative;border:1px solid #2a2a2a;background:#0a0a0a;padding:12px 44px 12px 14px}',
  '.card:hover{border-color:#3a3a3a}',
  '.card h3{margin:0 0 6px;font-size:14px;line-height:1.4}',
  '.card h3 a{color:#ff9d3d;text-decoration:none}',
  '.card h3 a:hover,.card h3 a:focus-visible{text-decoration:underline}',
  // The whole card is the link target; the star button sits above the stretched link.
  '.card h3 a::after{content:"";position:absolute;inset:0}',
  '.card .summary{margin:6px 0 0;font-size:14px;line-height:1.55;color:#c8c8c8}',
  '.meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:11px;color:#8a8a8a;margin:0}',
  '.tag{display:inline-block;border:1px solid #3a3a3a;padding:0 6px;font-size:10px;letter-spacing:.6px;color:#c8c8c8}',
  '.tag.read{border-color:#5fd28a;color:#5fd28a}',
  '.star{position:absolute;top:8px;right:8px;z-index:1;width:32px;height:32px;font-size:16px;line-height:1;background:none;border:1px solid transparent;color:#8a8a8a;cursor:pointer}',
  '.star:hover{border-color:#3a3a3a}',
  '.star[aria-pressed=true]{color:#ff9d3d}',
  '.card.is-read{border-left:2px solid #5fd28a}',
  // Guide page.
  '.layout{display:grid;grid-template-columns:minmax(0,1fr);gap:28px}',
  '@media (min-width:1000px){.layout{grid-template-columns:minmax(0,740px) 260px;justify-content:space-between}}',
  '.kicker{font-size:11px;letter-spacing:.8px;color:#ff9d3d;margin:0 0 6px}',
  '.guide h1{font-size:26px;margin:0 0 8px}',
  '.lede{font-size:16px;line-height:1.6;color:#c8c8c8;margin:0 0 10px}',
  '.tools{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}',
  '.tools button{font:inherit;font-size:12px;background:#000;color:#e8e8e8;border:1px solid #3a3a3a;padding:6px 12px;min-height:34px;cursor:pointer}',
  '.tools button[aria-pressed=true]{border-color:#5fd28a;color:#5fd28a}',
  '.tools button[data-save][aria-pressed=true]{border-color:#ff9d3d;color:#ff9d3d}',
  '.brief{border:1px solid #ff9d3d;background:#0a0a0a;padding:12px 14px;margin:18px 0}',
  '.brief p.brief-h{font:700 11px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.8px;color:#ff9d3d;margin:0 0 8px}',
  '.brief p{margin:0 0 6px;font-size:15px;line-height:1.55}',
  '.brief p:last-child{margin:0}',
  '.brief strong{color:#fff}',
  '.prose{font-size:16px;line-height:1.7}',
  '.prose p,.prose li{overflow-wrap:anywhere}',
  '.prose h2{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:17px;margin:30px 0 10px;scroll-margin-top:12px}',
  '.prose h3{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px;scroll-margin-top:12px}',
  '.prose table{font-size:13px}',
  '.prose .evidence,.prose blockquote{font-size:14px}',
  '.toc-side{display:none}',
  '@media (min-width:1000px){.toc-side{display:block;position:sticky;top:16px;align-self:start;max-height:calc(100vh - 32px);overflow:auto;margin:0}.toc-inline{display:none}}',
  '.toc-h{font-size:11px;font-weight:700;letter-spacing:.8px;color:#8a8a8a;margin:0 0 6px}',
  '.toc ol{margin:0;padding-left:18px}',
  '.toc li{margin:0 0 2px;line-height:1.4}',
  '.toc-inline summary{cursor:pointer;font-size:11px;font-weight:700;letter-spacing:.8px;color:#8a8a8a;min-height:24px}',
  '.pager{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:28px 0 8px}',
  '.pager a{display:block;border:1px solid #2a2a2a;padding:10px 12px;text-decoration:none;min-height:44px}',
  '.pager a:hover{border-color:#ff9d3d}',
  '.pager .dir{display:block;font-size:11px;color:#8a8a8a;letter-spacing:.6px}',
  '.pager [rel=next]{grid-column:2;text-align:right}',
  // Phones: paths in two compact columns and a shorter hero, so the first cards sit near the first screen.
  '@media (max-width:600px){.hero{padding-bottom:10px;margin-bottom:12px}.hero p{font-size:14px;line-height:1.5}.panel{padding:10px}.panel-h{margin-bottom:8px}.path-list{display:grid;grid-template-columns:1fr 1fr;gap:6px}.path[open]{grid-column:1/-1}.path summary{font-size:12px;padding:4px 8px;min-height:36px;line-height:1.3}.chips{margin-bottom:0}.progress{display:none}}',
  '@media (max-width:600px){.toolbar{grid-template-columns:1fr 1fr}.toolbar .search{grid-column:1/-1}.views{grid-column:1/-1}.views button{flex:1}.hero h1,.guide h1{font-size:22px}.pager{grid-template-columns:1fr}.pager [rel=next]{grid-column:1}}',
].join('');

export const GUIDE_PAGE_CSS = JOB_PAGE_CSS + GUIDE_CSS;

const cspHash = (text) => `'sha256-${createHash('sha256').update(text, 'utf8').digest('base64')}'`;

export const GUIDE_PAGE_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  `style-src ${cspHash(GUIDE_PAGE_CSS)}`,
  "img-src 'self'",
  "connect-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
].join('; ');
