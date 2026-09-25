#!/usr/bin/env node
// Copy the tiny e2e fixture dataset (test/fixtures/*) over dist/ so
// `npm run build:fixtures && npm run preview` serves deterministic data.
// Fixture files overwrite any fetched/generated data that the build copied
// in from public/.

import { cp, readdir, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BROTLI_DATA_FILES, removeBrotliSibling, writeBrotliSibling } from './seo/compress.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const FIXTURES = join(ROOT, 'test', 'fixtures');
const DIST = join(ROOT, 'dist');
// Generated data that may have been copied from public/ (fetch-data) — removed
// first so no live shard or feed leaks into a fixture run.
const GENERATED = ['jobs.json', 'jobs-index.json', 'jobs-extended.json', 'corpus-index.json', 'descriptions', 'feed.xml', 'feeds', 'health.json'];

async function main() {
  if (!existsSync(DIST)) {
    console.error('dist/ not found — run `vite build` first');
    process.exit(1);
  }
  await Promise.all(GENERATED.map((rel) => rm(join(DIST, rel), { recursive: true, force: true })));
  const entries = await readdir(FIXTURES);
  await Promise.all(entries.map((name) => cp(join(FIXTURES, name), join(DIST, name), { recursive: true, force: true })));
  // The build wrote .br siblings for the live data; regenerate them for the fixtures.
  for (const name of BROTLI_DATA_FILES) {
    await removeBrotliSibling(join(DIST, name));
    await writeBrotliSibling(join(DIST, name));
  }
  console.log(`Copied fixtures into dist/: ${entries.join(', ')} (+ brotli siblings)`);
}

main();
