import { useEffect, useState } from 'react';
import { descriptionShard, lookupDescription } from '../lib/descriptions.js';
import { loadDescriptionShard } from '../data/descriptions-source.js';

/**
 * Full description for `job`, lazily loaded from its description shard.
 * Returns the placeholder `job.desc` until (or unless) the shard provides text.
 * @param {import('../lib/jobs.js').Job|null} job
 */
export function useJobDescription(job, loadShard = loadDescriptionShard) {
  const jobId = job ? job.jobId : '';
  const [loaded, setLoaded] = useState({ jobId: '', text: null });

  useEffect(() => {
    const key = descriptionShard(jobId);
    if (!key) return undefined;
    let live = true;
    loadShard(key).then((shard) => {
      const text = lookupDescription(shard, jobId);
      if (live && text !== null) setLoaded({ jobId, text });
    });
    return () => { live = false; };
  }, [jobId, loadShard]);

  if (!job) return '';
  return (loaded.jobId === jobId && loaded.text) || job.desc;
}
