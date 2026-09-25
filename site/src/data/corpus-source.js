// Loads corpus-index.json (every posting the run saw, titles only) for the
// EXPLORE tab. Fetched only when that tab is opened; prefers the Brotli
// sibling like the other data files. Never rejects.

import { parseCorpusPayload } from '../lib/explore.js';
import { brotliStreamSupported, fetchJsonPreferBrotli } from './jobs-source.js';

export const CORPUS_URL = './corpus-index.json';

/**
 * @typedef {object} CorpusState
 * @property {object[]} rows
 * @property {object} meta
 * @property {string|null} error
 * @property {'br'|'gzip'|null} encoding
 */

/** @returns {Promise<CorpusState>} */
export async function loadCorpus(fetchImpl = fetch, brotli = brotliStreamSupported()) {
  try {
    const { data, encoding } = await fetchJsonPreferBrotli(CORPUS_URL, fetchImpl, brotli);
    const { rows, meta } = parseCorpusPayload(data);
    return { rows, meta, error: null, encoding };
  } catch (err) {
    console.warn('[terminal] corpus-index.json unavailable:', err);
    return { rows: [], meta: {}, error: (err && err.message) || String(err), encoding: null };
  }
}
