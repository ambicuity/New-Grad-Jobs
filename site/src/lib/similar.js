// "SIMILAR ROLES" in the detail pane: other open roles of the same type,
// preferring the same company, then the same location, then the newest.

export const SIMILAR_LIMIT = 3;

const COMPANY_WEIGHT = 2;
const LOCATION_WEIGHT = 1;

/**
 * @param {import('./jobs.js').Job|null} job
 * @param {import('./jobs.js').Job[]} jobs
 * @param {number} [limit]
 * @returns {import('./jobs.js').Job[]}
 */
export function similarJobs(job, jobs, limit = SIMILAR_LIMIT) {
  if (!job) return [];
  const score = (x) => (x.co === job.co ? COMPANY_WEIGHT : 0) + (x.loc === job.loc ? LOCATION_WEIGHT : 0);
  // The same posting mirrored on another source is not a "similar" role.
  const isDuplicate = (x) => x.co === job.co && x.role === job.role && x.loc === job.loc;
  return jobs
    .filter((x) => x.type === job.type && x.id !== job.id && !x.closed && !isDuplicate(x))
    .map((x) => ({ x, s: score(x) }))
    .sort((a, b) => (b.s - a.s)
      || (b.x.postedTs - a.x.postedTs)
      || (a.x.id < b.x.id ? -1 : a.x.id > b.x.id ? 1 : 0))
    .slice(0, limit)
    .map(({ x }) => x);
}
