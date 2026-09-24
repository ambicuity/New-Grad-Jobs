import { useCallback, useEffect, useState } from 'react';
import { cleanDescription, descriptionShard, lookupDescription } from '../lib/descriptions.js';
import { loadDescriptionShard } from '../data/descriptions-source.js';

/**
 * @typedef {object} DescriptionState
 * @property {'none'|'loading'|'ready'|'missing'|'error'} status
 *   none: no job · missing: the feed has no description for this job ·
 *   error: the shard failed to load (retry() refetches).
 * @property {string} text   Only set when status is 'ready'.
 * @property {() => void} retry
 */

/**
 * Full description for `job`, lazily loaded from its description shard. The
 * loaded result is tagged with the job id (and attempt), so switching jobs
 * shows "loading" — never the previous job's text.
 * @param {import('../lib/jobs.js').Job|null} job
 * @returns {DescriptionState}
 */
export function useJobDescription(job, loadShard = loadDescriptionShard) {
  const jobId = job ? job.jobId : '';
  const inline = job ? job.desc : '';
  const shardKey = inline ? null : descriptionShard(jobId);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState({ jobId: '', attempt: -1, ok: false, text: '' });

  useEffect(() => {
    if (!shardKey) return undefined;
    let live = true;
    loadShard(shardKey).then(
      (shard) => { if (live) setResult({ jobId, attempt, ok: true, text: lookupDescription(shard, jobId) || '' }); },
      () => { if (live) setResult({ jobId, attempt, ok: false, text: '' }); },
    );
    return () => { live = false; };
  }, [shardKey, jobId, attempt, loadShard]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  if (!job) return { status: 'none', text: '', retry };
  if (inline) return { status: 'ready', text: cleanDescription(inline), retry };
  if (!shardKey) return { status: 'missing', text: '', retry };
  if (result.jobId !== jobId || result.attempt !== attempt) return { status: 'loading', text: '', retry };
  if (!result.ok) return { status: 'error', text: '', retry };
  return result.text
    ? { status: 'ready', text: cleanDescription(result.text), retry }
    : { status: 'missing', text: '', retry };
}
