import { BBG, FONT_STACK, REPO_URL } from '../../lib/theme.js';
import { DashboardView } from './DashboardView.jsx';

/**
 * Hiring tab entry point. When jobs couldn't be fetched at all, say so (with a
 * retry) rather than rendering a dashboard of zeros that looks like "no jobs".
 * @param {{
 *   jobsState: import('../../data/jobs-source.js').JobsState,
 *   view: import('../../lib/url-state.js').ViewState,
 *   updateView: Function,
 * }} props
 */
export function HiringTab({ jobsState, view, updateView }) {
  if (jobsState.error) return <JobsLoadError reason={jobsState.error} />;
  return <DashboardView jobs={jobsState.jobs} meta={jobsState.meta} view={view} updateView={updateView} />;
}

export function JobsLoadError({ reason }) {
  return (
    <div role="alert" style={{
      height: '100%', background: BBG.bg, color: BBG.ink, padding: '32px 24px',
      fontFamily: FONT_STACK, fontSize: 12, lineHeight: 1.6,
    }}>
      <div style={{ color: BBG.hot, fontWeight: 700, letterSpacing: 0.8 }}>ERR · COULDN&apos;T LOAD JOBS</div>
      <div style={{ color: BBG.dim, marginTop: 6 }}>
        jobs-index.json and jobs.json both failed to load{reason ? ` (${reason})` : ''}.
      </div>
      <div style={{ color: BBG.dim }}>This is usually a network hiccup or a deploy in progress.</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 16 }}>
        <button type="button" onClick={() => window.location.reload()} style={{
          background: BBG.acc, color: '#000', border: 'none', padding: '8px 14px', minHeight: 36,
          fontFamily: 'inherit', fontWeight: 700, letterSpacing: 0.5, cursor: 'pointer',
        }}>RETRY ↻</button>
        <a href={`${REPO_URL}#readme`} target="_blank" rel="noopener noreferrer" style={{
          border: `1px solid ${BBG.rule2}`, color: BBG.ink, padding: '8px 14px', textDecoration: 'none',
        }}>README ↗</a>
      </div>
    </div>
  );
}
