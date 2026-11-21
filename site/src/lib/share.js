// Shareable link for a job. Prefers the static per-job page (/job/<job_id>/,
// generated at build time with JobPosting JSON-LD) and falls back to the board
// deep link (?job=<id>) for the rare job without a stable id. Near-miss postings
// have no static page (the SEO build only covers the curated set), so they always
// get the board link, with every include reason so the extended dataset loads.

/**
 * @param {{jobId?: string, id: string, nearMiss?: string[]}} job     row model (lib/jobs.js)
 * @param {{origin: string, pathname: string}} loc  window.location-like
 * @returns {string} absolute URL
 */
export function jobShareUrl(job, loc) {
  const origin = typeof loc?.origin === 'string' ? loc.origin : '';
  const pathname = typeof loc?.pathname === 'string' && loc.pathname ? loc.pathname : '/';
  // The app may live at the domain root or under a sub-path; keep everything below its directory.
  const dir = pathname.endsWith('/') ? pathname : pathname.slice(0, pathname.lastIndexOf('/') + 1);
  const reasons = Array.isArray(job?.nearMiss) ? job.nearMiss.filter((r) => typeof r === 'string' && r) : [];
  if (reasons.length === 0 && job && typeof job.jobId === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(job.jobId)) {
    return `${origin}${dir}job/${job.jobId}/`;
  }
  const params = new URLSearchParams({ job: job ? job.id : '' });
  reasons.forEach((r) => params.append('include', r));
  return `${origin}${dir}?${params.toString().replace(/\+/g, '%20')}`;
}

/**
 * Copy text to the clipboard; resolves to true on success. The async
 * Clipboard API is unavailable in insecure contexts and some embeds.
 * @param {string} text
 * @param {{clipboard?: {writeText: (t: string) => Promise<void>}}} [nav]
 */
export async function copyText(text, nav = typeof navigator !== 'undefined' ? navigator : undefined) {
  try {
    if (nav && nav.clipboard && typeof nav.clipboard.writeText === 'function') {
      await nav.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to "could not copy"
  }
  return false;
}
