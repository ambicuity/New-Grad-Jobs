// Right pane (desktop) / full-screen overlay body (mobile) for one job.
// Shows only what the feed publishes; anything unknown is labelled as such.

import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_LABEL, TIER_LABEL, TYPE_LABEL } from '../../lib/taxonomy.js';
import { fmtComp } from '../../lib/format.js';
import { safeHttpUrl } from '../../lib/safe-url.js';
import { extractRequirements } from '../../lib/requirements.js';
import { similarJobs } from '../../lib/similar.js';
import { useJobDescription } from '../../hooks/useJobDescription.js';
import { MIN_TARGET, Metric, ellipsis, sectionLabel } from '../ui.jsx';
import { ClosedBadge } from './JobRow.jsx';

const section = { padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` };
const muted = { color: BBG.dim, fontSize: 11.5, fontStyle: 'italic' };

const VISA_DETAIL = {
  citizenship: 'posting requires US citizenship',
  'no-sponsorship': 'posting says no visa sponsorship',
};

const postedDate = (ts) => (ts > 0 ? new Date(ts).toISOString().slice(0, 10) : 'date unknown');

/**
 * @param {{
 *   job: import('../../lib/jobs.js').Job|null,
 *   jobs: import('../../lib/jobs.js').Job[],
 *   saved: boolean,
 *   onSave: () => void,
 *   onSelectJob: (id: string) => void,
 * }} props
 */
export function JobDetail({ job, jobs, saved, onSave, onSelectJob }) {
  // Hooks run before the early return so hook order stays stable.
  const desc = useJobDescription(job);
  const requirements = useMemo(
    () => (desc.status === 'ready' ? extractRequirements(desc.text) : []),
    [desc.status, desc.text],
  );
  const similar = useMemo(() => similarJobs(job, jobs), [job, jobs]);
  if (!job) return <DetailEmpty hasJobs={jobs.length > 0} />;
  const href = safeHttpUrl(job.url);
  const hasComp = job.comp[0] != null;
  return (
    <section
      aria-labelledby="job-detail-title"
      style={{ overflow: 'auto', display: 'flex', flexDirection: 'column', minHeight: 0 }}
      data-testid="job-detail"
    >
      <div style={section}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>
            {job.co.toUpperCase()} · {TYPE_LABEL[job.type]} · {TIER_LABEL[job.tier]}
          </div>
          <button type="button" onClick={onSave} aria-pressed={saved} aria-label={saved ? 'Saved — remove from saved jobs' : 'Save job'} style={{
            background: saved ? BBG.acc : 'transparent', color: saved ? '#000' : BBG.ink,
            border: `1px solid ${saved ? BBG.acc : BBG.rule2}`, padding: '2px 8px', minHeight: MIN_TARGET,
            fontFamily: 'inherit', fontSize: 11, cursor: 'pointer',
          }}>{saved ? '★ SAVED' : '☆ SAVE'}</button>
        </div>
        <h2 id="job-detail-title" style={{ fontSize: 17, fontWeight: 600, margin: '4px 0 0', color: BBG.ink, lineHeight: 1.25 }}>
          {job.closed && <ClosedBadge />}{job.role}
        </h2>
        <div style={{ color: BBG.dim, fontSize: 11.5, marginTop: 4 }}>
          {job.co} · {job.loc} · {RMT_LABEL[job.rmt]}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric
          label="COMP"
          value={hasComp ? fmtComp(job.comp) : '—'}
          color={hasComp ? BBG.acc : BBG.dim}
          size={hasComp ? 18 : 14}
          sub={hasComp ? 'range in posting' : 'not posted'}
        />
        <Metric label="POSTED" value={job.posted} color={BBG.ink} sub={postedDate(job.postedTs)} />
        <Metric
          label="VISA"
          value={job.visa ? 'NONE STATED' : 'RESTRICTED'}
          size={14}
          color={job.visa ? BBG.ink : BBG.warn}
          sub={job.visa ? 'no restriction stated' : VISA_DETAIL[job.visaNote]}
        />
      </div>

      <div style={section}>
        <h3 style={{ ...sectionLabel, margin: '0 0 6px', fontWeight: 400 }}>ABOUT THE ROLE</h3>
        <Description desc={desc} />
      </div>

      {desc.status === 'ready' && (
        <div style={section}>
          <h3 style={{ ...sectionLabel, margin: '0 0 6px', fontWeight: 400 }}>REQUIREMENTS</h3>
          {requirements.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 16, lineHeight: 1.7, color: BBG.ink, fontSize: 11.5 }}>
              {requirements.map((req, i) => <li key={i}>{req}</li>)}
            </ul>
          ) : (
            <div style={muted}>None extracted from the description — see the full listing.</div>
          )}
        </div>
      )}

      <div style={section}>
        <h3 style={{ ...sectionLabel, margin: '0 0 6px', fontWeight: 400 }}>SIMILAR ROLES</h3>
        {similar.length === 0 && <div style={muted}>No other open {TYPE_LABEL[job.type]} roles right now.</div>}
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {similar.map((x) => (
            <li key={x.id}>
              <button type="button" onClick={() => onSelectJob(x.id)} style={{
                display: 'flex', justifyContent: 'space-between', gap: 8, width: '100%', minHeight: MIN_TARGET,
                background: 'transparent', border: 'none', padding: '2px 0', cursor: 'pointer',
                fontFamily: 'inherit', fontSize: 11.5, textAlign: 'left',
              }}>
                <span style={{ color: BBG.ink, minWidth: 0, ...ellipsis }}>
                  {x.co} · <span style={{ color: BBG.dim }}>{x.role} · {x.loc}</span>
                </span>
                <span style={{ color: x.comp[0] != null ? BBG.acc : BBG.dim, flexShrink: 0 }}>{fmtComp(x.comp)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" style={{
            flex: 1, background: job.closed ? 'transparent' : BBG.acc, color: job.closed ? BBG.ink : '#000',
            border: job.closed ? `1px solid ${BBG.rule2}` : 'none', textAlign: 'center', textDecoration: 'none',
            padding: '10px', fontWeight: 700, letterSpacing: 0.5,
          }}>
            {job.closed ? 'VIEW CLOSED LISTING ↗' : 'APPLY ↗'}
            <span className="ngj-sr-only"> (opens {job.co} listing in a new tab)</span>
          </a>
        ) : (
          <span style={{ ...muted, padding: '10px 0' }}>No valid application link in the feed.</span>
        )}
      </div>
    </section>
  );
}

function Description({ desc }) {
  const box = {
    color: BBG.ink, lineHeight: 1.55, fontSize: 11.5,
    maxHeight: 160, overflowY: 'auto', paddingRight: 8, whiteSpace: 'pre-line',
  };
  if (desc.status === 'loading') {
    return <div data-testid="job-description" aria-busy="true" style={{ ...box, color: BBG.dim }}>loading…</div>;
  }
  if (desc.status === 'error') {
    return (
      <div data-testid="job-description" role="alert" style={{ ...box, color: BBG.warn }}>
        description unavailable —{' '}
        <button type="button" onClick={desc.retry} style={{
          background: 'transparent', border: `1px solid ${BBG.rule2}`, color: BBG.ink, cursor: 'pointer',
          fontFamily: 'inherit', fontSize: 11, padding: '0 8px', minHeight: MIN_TARGET,
        }}>RETRY ↻</button>
      </div>
    );
  }
  if (desc.status !== 'ready') {
    return <div data-testid="job-description" style={muted}>No description published for this posting — see the full listing.</div>;
  }
  // Focusable so keyboard users can scroll the clipped text (WCAG 2.1.1).
  return <div data-testid="job-description" tabIndex={0} role="region" aria-label="Job description" style={box}>{desc.text}</div>;
}

// Right pane when nothing is selected: an empty feed, or filters that match
// nothing. Keeps the 3-column layout intact instead of collapsing the column.
export function DetailEmpty({ hasJobs }) {
  return (
    <div style={{ padding: '18px 16px', color: BBG.dim, fontSize: 11.5, lineHeight: 1.6 }}>
      <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7, marginBottom: 6 }}>DETAIL</div>
      {hasJobs
        ? <div>No job selected. Clear filters with <span style={{ color: BBG.ink }}>Esc</span> or pick a row.</div>
        : <div>No open roles in the feed right now. The scraper runs about every 30 minutes.</div>}
    </div>
  );
}
