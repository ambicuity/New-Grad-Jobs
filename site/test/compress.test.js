import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { brotliDecompressSync } from 'node:zlib';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  BROTLI_DATA_FILES, brotliBytes, removeBrotliSibling, writeBrotliSibling, writeBrotliSiblings,
} from '../scripts/seo/compress.mjs';

describe('brotli siblings', () => {
  let dir;
  beforeEach(async () => { dir = await mkdtemp(join(tmpdir(), 'ngj-br-')); });
  afterEach(() => rm(dir, { recursive: true, force: true }));

  it('writes a .br that round-trips to the same bytes and is smaller', async () => {
    const json = JSON.stringify({ jobs: Array.from({ length: 200 }, (_, i) => ({ id: `job_${i}`, title: 'Software Engineer, New Grad' })) });
    await writeFile(join(dir, 'jobs-index.json'), json);
    const out = await writeBrotliSibling(join(dir, 'jobs-index.json'));
    expect(out.raw).toBe(Buffer.byteLength(json));
    expect(out.br).toBeLessThan(out.raw / 4);
    expect(brotliDecompressSync(await readFile(join(dir, 'jobs-index.json.br'))).toString()).toBe(json);
  });

  it('returns null for a missing source and never writes', async () => {
    expect(await writeBrotliSibling(join(dir, 'nope.json'))).toBeNull();
    expect(existsSync(join(dir, 'nope.json.br'))).toBe(false);
  });

  it('writes every present data file and skips absent ones; removeBrotliSibling is idempotent', async () => {
    await writeFile(join(dir, 'jobs-index.json'), '{"jobs":[]}');
    const logs = [];
    const written = await writeBrotliSiblings(dir, BROTLI_DATA_FILES, { log: (m) => logs.push(m) });
    expect(written.map((w) => w.path.split('/').pop())).toEqual(['jobs-index.json']);
    expect(logs[0]).toMatch(/\[brotli\] jobs-index\.json/);
    await removeBrotliSibling(join(dir, 'jobs-index.json'));
    await removeBrotliSibling(join(dir, 'jobs-index.json'));
    expect(existsSync(join(dir, 'jobs-index.json.br'))).toBe(false);
  });

  it('brotliBytes is deterministic for the same input', () => {
    const a = brotliBytes(Buffer.from('x'.repeat(5000)));
    expect(a.equals(brotliBytes(Buffer.from('x'.repeat(5000))))).toBe(true);
  });
});
