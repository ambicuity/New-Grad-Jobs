// Brotli siblings for the data payloads. GitHub Pages only ever gzips (and
// answers a Brotli-only request uncompressed), so the build writes
// `<file>.json.br` next to each data file: raw Brotli-11 bytes that Pages
// serves as-is. The site decodes them with the browser's native
// DecompressionStream('brotli') and falls back to the plain `.json` (host
// gzip) when that is unsupported. Measured on live data the .br is ~40%
// smaller than the host's gzip. Every sibling is verified to round-trip
// byte-for-byte before the build is allowed to keep it.

import { readFile, rm, writeFile } from 'node:fs/promises';
import { brotliCompressSync, brotliDecompressSync, constants } from 'node:zlib';

/** Data files worth a Brotli sibling (fetched by the app, large, JSON). */
export const BROTLI_DATA_FILES = ['jobs-index.json', 'jobs-extended.json', 'corpus-index.json'];
export const BROTLI_SUFFIX = '.br';

/** Brotli-11 bytes for `buffer`, with the size hint set so the encoder picks its window well. */
export function brotliBytes(buffer) {
  return brotliCompressSync(buffer, {
    params: {
      [constants.BROTLI_PARAM_QUALITY]: constants.BROTLI_MAX_QUALITY,
      [constants.BROTLI_PARAM_SIZE_HINT]: buffer.length,
    },
  });
}

/**
 * Write `<path>.br` for `path` and verify it decodes to the same bytes.
 * @returns {Promise<{path: string, raw: number, br: number}|null>} null when the source file is missing.
 */
export async function writeBrotliSibling(path) {
  let source;
  try {
    source = await readFile(path);
  } catch (err) {
    if (err && err.code === 'ENOENT') return null;
    throw err;
  }
  const encoded = brotliBytes(source);
  if (!brotliDecompressSync(encoded).equals(source)) {
    throw new Error(`brotli round-trip mismatch for ${path}`);
  }
  await writeFile(`${path}${BROTLI_SUFFIX}`, encoded);
  return { path, raw: source.length, br: encoded.length };
}

/** Remove a stale sibling (e.g. before fixtures overwrite the data file). */
export async function removeBrotliSibling(path) {
  await rm(`${path}${BROTLI_SUFFIX}`, { force: true });
}

/**
 * Write siblings for every data file present in `dir`.
 * @returns {Promise<{path: string, raw: number, br: number}[]>}
 */
export async function writeBrotliSiblings(dir, files = BROTLI_DATA_FILES, log = console) {
  const written = [];
  for (const name of files) {
    const result = await writeBrotliSibling(`${dir}/${name}`);
    if (result) written.push(result);
  }
  if (written.length) {
    log.log(`[brotli] ${written.map((w) => `${w.path.split('/').pop()} ${(w.raw / 1024).toFixed(0)}→${(w.br / 1024).toFixed(0)} KB`).join(', ')}`);
  }
  return written;
}
