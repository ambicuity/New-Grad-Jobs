// Right pane (desktop) / full-screen overlay body (mobile) for one job.

import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_LABEL, SIZE_LABEL } from '../../lib/taxonomy.js';
import { fmtComp } from '../../lib/format.js';
import { daysLeft } from '../../lib/time.js';
import { extractRequirements } from '../../lib/requirements.js';
import { useJobDescription } from '../../hooks/useJobDescription.js';
import { Metric, sectionLabel } from '../ui.jsx';

const SIMILAR_LIMIT = 3;
const section = { padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` };

const openUrl = (url) => url && window.open(url, '_blank', 'noopener');

/**
 * @param {{job: import('../../lib/jobs.js').Job|null, jobs: import('../../lib/jobs.js').Job[], saved: boolean, onSave: () => void}} props
 */
export function JobDetail({ job, jobs, saved, onSave }) {
  // Hook runs before the early return so hook order stays stable.
  const desc = useJobDescription(job);
  const requirements = useMemo(() => extractRequirements(desc), [desc]);
  const similar = useMemo(
    () => (job ? jobs.filter((x) => x.type === job.type && x.id !== job.id).slice(0, SIMILAR_LIMIT) : []),
    [jobs, job],
  );
  if (!job) return <DetailEmpty hasJobs={jobs.length > 0} />;
  const days = daysLeft(job.dl);
  return (
    <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }} data-testid="job-detail">
      <div style={section}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>
            {job.co.toUpperCase()} · {job.type} · {SIZE_LABEL[job.size]}
          </div>
          <button onClick={onSave} style={{
            background: saved ? BBG.acc : 'transparent', color: saved ? '#000' : BBG.ink,
            border: `1px solid ${saved ? BBG.acc : BBG.rule2}`, padding: '2px 8px',
            fontFamily: 'inherit', fontSize: 11, cursor: 'pointer',
          }}>{saved ? '★ SAVED' : '☆ SAVE'}</button>
        </div>
        <div style={{ fontSize: 17, fontWeight: 600, marginTop: 4, color: BBG.ink, lineHeight: 1.25 }}>{job.role}</div>
        <div style={{ color: BBG.dim, fontSize: 11.5, marginTop: 4 }}>
          {job.co} · {job.loc} · {RMT_LABEL[job.rmt]} · cohort &apos;{job.cohort}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric label="COMP" value={fmtComp(job.comp)} color={BBG.acc} sub="base + equity" />
        <Metric label="DEADLINE" value={`${days}d`} color={days < 14 ? BBG.hot : BBG.ink} sub={job.dl} />
        <Metric label="VISA" value={job.visa ? 'YES' : 'NO'} color={job.visa ? BBG.ok : BBG.warn} sub={job.visa ? 'sponsored' : 'us-auth req.'} />
      </div>

      <div style={section}>
        <div style={sectionLabel}>ABOUT THE ROLE</div>
        <div data-testid="job-description" style={{
          color: BBG.ink, lineHeight: 1.55, fontSize: 11.5,
          maxHeight: 160, overflowY: 'auto', paddingRight: 8,
        }}>{desc}</div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>STACK</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {job.stack.map((s) => (
            <span key={s} style={{ padding: '2px 7px', border: `1px solid ${BBG.rule2}`, color: BBG.ink, fontSize: 11 }}>
              {s.toLowerCase()}
            </span>
          ))}
          <span style={{ padding: '2px 7px', color: BBG.dim, fontSize: 11 }}>+ {job.level || 'entry'} level</span>
        </div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>REQUIREMENTS</div>
        <div style={{ margin: 0, paddingLeft: 0, lineHeight: 1.7, color: BBG.ink, fontSize: 11.5 }}>
          {requirements.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {requirements.map((req, i) => <li key={i}>{req}</li>)}
            </ul>
          ) : (
            <div style={{ color: BBG.dim, fontSize: 11, fontStyle: 'italic' }}>
              Requirements not available. Click APPLY to view full details.
            </div>
          )}
        </div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>SIMILAR ROLES</div>
        {similar.map((x) => (
          <div key={x.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, padding: '2px 0' }}>
            <span style={{ color: BBG.ink }}>{x.co} · <span style={{ color: BBG.dim }}>{x.role}</span></span>
            <span style={{ color: BBG.acc }}>{fmtComp(x.comp)}</span>
          </div>
        ))}
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        <button onClick={() => openUrl(job.url)} style={{
          flex: 1, background: BBG.acc, color: '#000', border: 'none',
          padding: '10px', fontFamily: 'inherit', fontWeight: 700, cursor: 'pointer',
          letterSpacing: 0.5,
        }}>APPLY ↗</button>
        <button style={{
          background: 'transparent', color: BBG.ink, border: `1px solid ${BBG.rule2}`,
          padding: '10px 14px', fontFamily: 'inherit', cursor: 'pointer',
        }}>REFER A FRIEND</button>
      </div>
    </div>
  );
}

// Right pane when nothing is selected: an empty feed, or filters that match
// nothing. Keeps the 3-column layout intact instead of collapsing the column.
export function DetailEmpty({ hasJobs }) {
  return (
    <div style={{ padding: '18px 16px', color: BBG.dim, fontSize: 11.5, lineHeight: 1.6 }}>
      <div style={{ color: BBG.acc, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>DETAIL</div>
      {hasJobs
        ? <div>No job selected. Clear filters with <span style={{ color: BBG.ink }}>Esc</span> or pick a row.</div>
        : <div>No open roles in the feed right now. The scraper runs about every 30 minutes.</div>}
    </div>
  );
}
