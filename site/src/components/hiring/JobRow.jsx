// One job in the list: a dense 8-column table row on desktop, a stacked card
// on mobile. Memoised so j/k navigation re-renders only the rows that change.

import { memo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_LABEL, SIZE_LABEL } from '../../lib/taxonomy.js';
import { fmtComp, rowNumber } from '../../lib/format.js';
import { daysLeft } from '../../lib/time.js';
import { ellipsis, onActivateKey } from '../ui.jsx';

export const JOB_GRID_COLUMNS = '28px 110px 1fr 130px 90px 90px 90px 26px';
const URGENCY_WINDOW_DAYS = 120;
const HOT_DAYS = 14;

const sep = <span style={{ color: BBG.rule2, margin: '0 6px' }}>·</span>;
const dot = <span style={{ color: BBG.rule2 }}>·</span>;

function urgencyOf(days) {
  return Math.min(1, Math.max(0, 1 - days / URGENCY_WINDOW_DAYS));
}

export const JobRow = memo(function JobRow({ job: j, index, isSelected, isSaved, onSelect, onToggleSave }) {
  const days = daysLeft(j.dl);
  return (
    <div onClick={() => onSelect(j.id)} aria-selected={isSelected} data-job-id={j.id} style={{
      display: 'grid',
      gridTemplateColumns: JOB_GRID_COLUMNS,
      gap: 8, padding: '6px 14px',
      borderBottom: `1px solid ${BBG.rule}`,
      background: isSelected ? BBG.selBg : 'transparent',
      borderLeft: isSelected ? `2px solid ${BBG.acc}` : '2px solid transparent',
      cursor: 'pointer', alignItems: 'center',
    }}>
      <span style={{ color: BBG.dim, fontSize: 11 }}>{rowNumber(index)}</span>
      <span style={{ color: isSelected ? BBG.acc : BBG.ink, fontWeight: 600, ...ellipsis }}>{j.co}</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ color: BBG.ink, ...ellipsis }}>{j.role}</div>
        <div style={{ color: BBG.dim, fontSize: 10.5, ...ellipsis }}>
          {j.stack.slice(0, 3).join('/').toLowerCase()}
          {sep}
          <span style={{ color: j.visa ? BBG.ok : BBG.warn }}>{j.visa ? 'visa✓' : 'us'}</span>
          {sep}
          {RMT_LABEL[j.rmt]}
          {sep}
          {SIZE_LABEL[j.size]}
        </div>
      </div>
      <span style={{ color: BBG.ink, fontSize: 11.5, ...ellipsis }}>{j.loc}</span>
      <span style={{ color: BBG.acc, fontSize: 11.5 }}>{fmtComp(j.comp)}</span>
      <span style={{ color: BBG.dim, fontSize: 11 }}>{j.posted}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <UrgencyBar value={urgencyOf(days)} />
        <span style={{ color: days < HOT_DAYS ? BBG.hot : BBG.ink, fontSize: 11 }}>
          {days < 0 ? 'X' : `${days}d`}
        </span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onToggleSave(j.id); }}
        aria-label={isSaved ? 'unsave job' : 'save job'}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
          color: isSaved ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: 14,
        }}
      >{isSaved ? '★' : '☆'}</button>
    </div>
  );
});

// Single-column card: the 8 desktop columns can't fit a phone, so stack them
// and open the full-screen detail on tap.
export const JobCard = memo(function JobCard({ job: j, index, isSaved, onOpen, onToggleSave }) {
  const days = daysLeft(j.dl);
  const open = () => onOpen(j.id);
  return (
    <div
      onClick={open}
      role="button"
      tabIndex={0}
      aria-label={`${j.co} — ${j.role}, open details`}
      onKeyDown={onActivateKey(open)}
      data-job-id={j.id}
      style={{
        padding: '11px 14px', borderBottom: `1px solid ${BBG.rule}`,
        cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span style={{ color: BBG.acc, fontWeight: 600, fontSize: 12.5 }}>
          <span style={{ color: BBG.dim, marginRight: 6 }}>{rowNumber(index)}</span>{j.co}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onToggleSave(j.id); }}
          aria-label={isSaved ? 'unsave job' : 'save job'}
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px 4px',
            color: isSaved ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: 18, lineHeight: 1,
          }}
        >{isSaved ? '★' : '☆'}</button>
      </div>
      <div style={{ color: BBG.ink, fontSize: 13, lineHeight: 1.3 }}>{j.role}</div>
      <div style={{ color: BBG.dim, fontSize: 11, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '2px 6px' }}>
        <span>{j.loc}</span>
        {dot}
        <span style={{ color: BBG.acc }}>{fmtComp(j.comp)}</span>
        {dot}
        <span>{j.posted}</span>
        {dot}
        <span style={{ color: days < HOT_DAYS ? BBG.hot : BBG.ink }}>{days < 0 ? 'closed' : `${days}d left`}</span>
        {dot}
        <span style={{ color: j.visa ? BBG.ok : BBG.warn }}>{j.visa ? 'visa✓' : 'us'}</span>
      </div>
    </div>
  );
});

/** Five-block deadline urgency meter. */
export function UrgencyBar({ value }) {
  const filled = Math.round(value * 5);
  const fill = value > 0.7 ? BBG.hot : value > 0.4 ? BBG.warn : BBG.acc;
  return (
    <span style={{ display: 'inline-flex', gap: 1 }}>
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} style={{ width: 4, height: 8, background: i < filled ? fill : BBG.rule2 }} />
      ))}
    </span>
  );
}
