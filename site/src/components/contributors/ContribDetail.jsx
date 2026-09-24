// Right pane (desktop) / overlay body (mobile) for one contributor.

import { AREA_COLOR, BBG } from '../../lib/theme.js';
import { fmtK } from '../../lib/format.js';
import { REPO_SLUG, rankIn } from '../../lib/contributors.js';
import { useRecentCommits } from '../../hooks/useRecentCommits.js';
import { Metric, ellipsis, sectionLabel } from '../ui.jsx';
import { Avatar, Sparkline } from './ContribBits.jsx';

const WEEKS = 26;
const section = { padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` };
const note = { fontSize: 11, padding: '3px 0' };

export function ContribDetail({ c, contributors, spark }) {
  const recent = useRecentCommits(c && c.handle);
  if (!c) return null;
  const total = c.add + c.del;
  return (
    <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 16px 14px', borderBottom: `1px solid ${BBG.rule2}`, display: 'flex', gap: 12 }}>
        <Avatar handle={c.handle} size={56} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>@{c.handle} · {c.role.toUpperCase()}</div>
          <div style={{ fontSize: 17, fontWeight: 600, marginTop: 2, color: BBG.ink }}>{c.name}</div>
          <div style={{ color: BBG.dim, fontSize: 11.5, marginTop: 2 }}>{c.region} · since {c.since} · last commit {c.last}</div>
          <div style={{ color: BBG.ink, fontSize: 11.5, marginTop: 6, lineHeight: 1.55 }}>{c.bio}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric size={16} label="COMMITS" value={c.commits.toLocaleString()} sub={`#${rankIn(contributors, 'commits', c)}`} color={BBG.acc} />
        <Metric size={16} label="PRS MERGED" value={c.prs.toString()} sub={`#${rankIn(contributors, 'prs', c)}`} color={BBG.ink} />
        <Metric size={16} label="NET LOC" value={`+${fmtK(c.add)} / -${fmtK(c.del)}`} sub={`${((c.add / (total || 1)) * 100).toFixed(0)}% add`} color={BBG.ok} />
      </div>

      <div style={section}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7 }}>ACTIVITY · 26W</div>
          <div style={{ color: BBG.dim, fontSize: 10 }}>{Math.round(c.commits / WEEKS)} commits/wk avg</div>
        </div>
        <Sparkline values={spark} />
        <div style={{ display: 'flex', justifyContent: 'space-between', color: BBG.dim, fontSize: 9.5, marginTop: 3 }}>
          <span>nov &apos;25</span><span>feb &apos;26</span><span>now</span>
        </div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>TOP LANGUAGES</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {c.langs.map((l) => (
            <span key={l} style={{ padding: '2px 7px', border: `1px solid ${BBG.rule2}`, color: BBG.ink, fontSize: 11 }}>
              {l.toLowerCase()}
            </span>
          ))}
        </div>
      </div>

      <div style={section}>
        <div style={sectionLabel}>CODEOWNERS</div>
        {c.areas.map((a) => (
          <div key={a} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, padding: '3px 0', borderBottom: `1px dashed ${BBG.rule}` }}>
            <span>
              <span style={{ display: 'inline-block', width: 6, height: 6, background: AREA_COLOR[a] || BBG.acc, marginRight: 6 }} />
              <span style={{ color: BBG.ink }}>{a}</span>
              <span style={{ color: BBG.dim, marginLeft: 8 }}>src/{a}/**</span>
            </span>
            <span style={{ color: BBG.dim }}>owner</span>
          </div>
        ))}
      </div>

      <div style={section}>
        <div style={sectionLabel}>RECENT COMMITS</div>
        {recent.state === 'loading' && <div style={{ color: BBG.dim, ...note }}>loading from github…</div>}
        {recent.state === 'empty' && <div style={{ color: BBG.dim, ...note }}>no commits authored by @{c.handle} in this repo</div>}
        {recent.state === 'error' && (
          <div style={{ color: BBG.warn, ...note }}>could not load commits ({recent.error || 'network'})</div>
        )}
        {recent.state === 'ok' && recent.commits.map((rc, i) => (
          <a key={rc.sha || i} href={rc.url || `https://github.com/${REPO_SLUG}/commit/${rc.sha}`} target="_blank" rel="noopener noreferrer"
            style={{ display: 'grid', gridTemplateColumns: '52px 1fr 60px', gap: 8, fontSize: 11, padding: '3px 0', textDecoration: 'none' }}>
            <span style={{ color: BBG.acc2 }}>{rc.sha}</span>
            <span style={{ color: BBG.ink, ...ellipsis }}>{rc.msg}</span>
            <span style={{ color: BBG.dim, textAlign: 'right' }}>{rc.ago}</span>
          </a>
        ))}
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        <button onClick={() => c.profile && window.open(c.profile, '_blank', 'noopener')} style={{
          flex: 1, background: BBG.acc, color: '#000', border: 'none', padding: 10,
          fontFamily: 'inherit', fontWeight: 700, cursor: 'pointer', letterSpacing: 0.5,
        }}>VIEW ON GITHUB ↗</button>
        <button style={{
          background: 'transparent', color: BBG.ink, border: `1px solid ${BBG.rule2}`,
          padding: '10px 14px', fontFamily: 'inherit', cursor: 'pointer',
        }}>SPONSOR</button>
      </div>
    </div>
  );
}
