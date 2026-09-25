#!/usr/bin/env node
// Regenerate public/og-image.png (1200×630 social card) from the HTML template
// below with headless Chrome. The PNG is committed, so this only needs to run
// when the design changes:
//   node scripts/og-image.mjs            (auto-detects Chrome / Chromium)
//   CHROME=/path/to/chrome node scripts/og-image.mjs
// Output is deterministic for a given Chrome build: static template, bundled
// JetBrains Mono (no network), no dates or live numbers.

import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { copyFile, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'public', 'og-image.png');
const FONT_DIR = join(ROOT, 'node_modules', '@fontsource', 'jetbrains-mono', 'files');
const WIDTH = 1200;
const HEIGHT = 630;
// Headless Chrome occasionally lingers after writing the screenshot on macOS.
const CHROME_TIMEOUT_MS = 60000;

const CHROME_CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);

const font = (weight) => pathToFileURL(join(FONT_DIR, `jetbrains-mono-latin-${weight}-normal.woff2`)).href;

const TEMPLATE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@font-face { font-family: JBM; font-weight: 400; src: url(${font(400)}) format('woff2'); }
@font-face { font-family: JBM; font-weight: 700; src: url(${font(700)}) format('woff2'); }
* { box-sizing: border-box; margin: 0; }
html, body { width: ${WIDTH}px; height: ${HEIGHT}px; background: #000; overflow: hidden; }
body { font-family: JBM, monospace; color: #e8e8e8; padding: 56px 72px; position: relative; }
body::before { content: ''; position: absolute; inset: 24px; border: 2px solid #2a2a2a; }
.bar { display: flex; align-items: center; gap: 14px; font-size: 22px; color: #6e6e6e; letter-spacing: 1px; }
.dot { width: 14px; height: 14px; border-radius: 50%; background: #5fd28a; }
.live { color: #5fd28a; font-weight: 700; }
.mark { margin-top: 56px; font-size: 150px; line-height: 1; font-weight: 700; color: #ff9d3d; letter-spacing: 6px; }
.name { margin-top: 18px; font-size: 76px; line-height: 1; font-weight: 700; color: #e8e8e8; }
.name .sep { color: #6e6e6e; font-weight: 400; padding-right: 20px; }
.tag { margin-top: 40px; font-size: 30px; color: #e8e8e8; }
.tag .dim { color: #6e6e6e; }
.prompt { position: absolute; left: 72px; bottom: 60px; font-size: 26px; color: #6e6e6e; }
.prompt b { color: #ff9d3d; font-weight: 700; }
.cursor { display: inline-block; width: 16px; height: 30px; background: #ff9d3d; vertical-align: -5px; margin-left: 6px; }
.url { position: absolute; right: 72px; bottom: 60px; font-size: 24px; color: #62a3ff; }
</style></head><body>
<div class="bar"><span class="dot"></span><span class="live">LIVE</span><span>· updated every ~30 min</span></div>
<div class="mark">NGJ</div>
<div class="name"><span class="sep">·</span>New Grad Jobs</div>
<div class="tag">new grad &amp; entry-level roles in every field <span class="dim">straight from company career APIs</span></div>
<div class="prompt"><b>CMD&gt;</b> filter --new-grad<span class="cursor"></span></div>
<div class="url">jobs.riteshrana.engineer</div>
</body></html>`;

async function main() {
  const chrome = CHROME_CANDIDATES.find((p) => existsSync(p));
  if (!chrome) {
    console.error('Chrome/Chromium not found — set CHROME=/path/to/chrome');
    process.exit(1);
  }
  if (!existsSync(FONT_DIR)) {
    console.error('JetBrains Mono not installed — run `npm ci` first');
    process.exit(1);
  }
  const dir = await mkdtemp(join(tmpdir(), 'ngj-og-'));
  try {
    const html = join(dir, 'og.html');
    await writeFile(html, TEMPLATE);
    const shot = join(dir, 'og.png');
    try {
      execFileSync(chrome, [
        '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--disable-extensions', '--use-mock-keychain', '--hide-scrollbars', '--force-device-scale-factor=1',
        '--allow-file-access-from-files', `--user-data-dir=${join(dir, 'profile')}`,
        `--window-size=${WIDTH},${HEIGHT}`, '--virtual-time-budget=2000',
        `--screenshot=${shot}`, pathToFileURL(html).href,
      ], { stdio: 'inherit', timeout: CHROME_TIMEOUT_MS });
    } catch (err) {
      // A lingering Chrome is killed by the timeout; the screenshot may still be complete.
      if (!existsSync(shot)) throw err;
      console.warn(`chrome did not exit cleanly (${err.code || err.message}); screenshot was written`);
    }
    await copyFile(shot, OUT);
    console.log(`wrote ${OUT}`);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

main();
