#!/usr/bin/env node
// Download the live generated data into public/ for local development:
//   npm run fetch-data            (defaults to https://jobs.riteshrana.engineer)
//   NGJ_DATA_ORIGIN=https://... npm run fetch-data
// These files are written by the scraper at CI time and are gitignored.

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ORIGIN = (process.env.NGJ_DATA_ORIGIN || 'https://jobs.riteshrana.engineer').replace(/\/+$/, '');
const PUBLIC_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'public');
const SHARDS = '0123456789abcdef'.split('').map((k) => `descriptions/${k}.json`);
const FILES = ['jobs-index.json', 'jobs.json', 'health.json', 'feed.xml', ...SHARDS];
const CONCURRENCY = 6;

async function download(rel) {
  const res = await fetch(`${ORIGIN}/${rel}`, { headers: { 'Cache-Control': 'no-cache' } });
  if (!res.ok) throw new Error(`${rel}: HTTP ${res.status}`);
  const body = Buffer.from(await res.arrayBuffer());
  // Only the fixed FILES allow-list is ever written, and never outside public/.
  if (!FILES.includes(rel)) throw new Error(`${rel}: not an expected data file`);
  const dest = resolve(join(PUBLIC_DIR, rel));
  if (!dest.startsWith(resolve(PUBLIC_DIR) + sep)) throw new Error(`${rel}: escapes public/`);
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, body);
  return { rel, bytes: body.length };
}

async function main() {
  const queue = [...FILES];
  const failures = [];
  const worker = async () => {
    while (queue.length) {
      const rel = queue.shift();
      try {
        const { bytes } = await download(rel);
        console.log(`  ok  ${rel} (${(bytes / 1024).toFixed(0)} KiB)`);
      } catch (err) {
        failures.push(rel);
        console.error(`  FAIL ${err.message}`);
      }
    }
  };
  console.log(`Fetching site data from ${ORIGIN} → public/`);
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  if (failures.length) {
    console.error(`${failures.length} file(s) failed: ${failures.join(', ')}`);
    process.exit(1);
  }
}

main();
