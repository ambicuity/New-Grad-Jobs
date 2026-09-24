// Right pane (desktop) / overlay body (mobile) for one contributor.

import { BBG } from '../../lib/theme.js';
import { commitRank } from '../../lib/contributors.js';
import { formatAgo } from '../../lib/time.js';
import { Metric, ellipsis, sectionLabel } from '../ui.jsx';
import { Avatar, fmtCommits } from './ContribBits.jsx';
import { useRecentCommits } from './useRecentCommits.js';

const section = { padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` };
const note = { fontSize: 11, padding: '3px 0' };
const linkBtn = { textDecoration: 'none', textAlign: 'center', fontFamily: 'inherit', letterSpacing: 0.5, padding: 10 };

function retryLabel(retryAt) {
  if (!retryAt) return '';
  const d = new Date(retryAt);
  return ` · retry after ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function ContribDetail({ c, contributors }) {
  const recent = useRecentCommits(c && c.handle);
  if (!c) return null;
  const rank = commitRank(contributors, c);
  return (
    <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 16px 14px', borderBottom: `1px solid ${BBG.rule2}`, display: 'flex', gap: 12 }}>
        <Avatar handle={c.handle} size={56} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>@{c.handle} · {c.role.toUpperCase()}</div>
          <div style={{ fontSize: 17, fontWeight: 600, marginTop: 2, color: BBG.ink }}>{c.name}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric size={16} label="COMMITS" value={fmtCommits(c.commits)} sub={rank ? `#${rank} by commits` : 'not in github stats'} color={BBG.acc} />
        <Metric size={16} label="CONTRIBUTION TYPES" value={String(c.types.length)} sub="all-contributors" color={BBG.ink} />
      </div>

      <div style={section}>
        <div style={sectionLabel}>CONTRIBUTIONS</div>
        {c.types.length === 0 && <div style={{ color: BBG.dim, ...note }}>—</div>}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {c.types.map((t) => (
            <span key={t} style={{ padding: '2px 7px', border: `1px solid ${BBG.rule2}`, color: BBG.ink, fontSize: 11 }}>{t}</span>
          ))}
        </div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>RECENT COMMITS</div>
        {recent.state === 'loading' && <div role="status" style={{ color: BBG.dim, ...note }}>loading from github…</div>}
        {recent.state === 'empty' && <div style={{ color: BBG.dim, ...note }}>no commits authored by @{c.handle} in this repo</div>}
        {recent.state === 'error' && (
          <div style={{ color: BBG.warn, ...note }}>
            could not load commits ({recent.error || 'network'}{retryLabel(recent.retryAt)})
          </div>
        )}
        {recent.state === 'ok' && recent.commits.map((rc) => (
          <a key={rc.sha} href={rc.url} target="_blank" rel="noopener noreferrer"
            style={{ display: 'grid', gridTemplateColumns: '52px 1fr 60px', gap: 8, fontSize: 11, padding: '3px 0', textDecoration: 'none' }}>
            <span style={{ color: BBG.acc2 }}>{rc.sha}</span>
            <span style={{ color: BBG.ink, ...ellipsis }}>{rc.msg}</span>
            <span style={{ color: BBG.dim, textAlign: 'right' }}>{formatAgo(rc.date)}</span>
          </a>
        ))}
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        {c.profile && (
          <a href={c.profile} target="_blank" rel="noopener noreferrer" style={{
            ...linkBtn, flex: 1, background: BBG.acc, color: '#000', fontWeight: 700,
          }}>VIEW ON GITHUB ↗</a>
        )}
        {c.sponsorUrl && (
          <a href={c.sponsorUrl} target="_blank" rel="noopener noreferrer" style={{
            ...linkBtn, color: BBG.ink, border: `1px solid ${BBG.rule2}`, padding: '10px 14px',
          }}>SPONSOR ↗</a>
        )}
      </div>
    </div>
  );
}
