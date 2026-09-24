// One job in the list: a fixed-height listbox option on desktop, a stacked
// card on mobile. Both are memoised so j/k navigation and virtual scrolling
// re-render only the rows whose props change.

import { memo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_LABEL, TIER_LABEL, TYPE_LABEL } from '../../lib/taxonomy.js';
import { fmtComp, rowNumber } from '../../lib/format.js';
import { MIN_TARGET, ellipsis } from '../ui.jsx';

export const JOB_GRID_COLUMNS = '32px 120px 1fr 150px 100px 64px 28px';
/** Desktop rows are fixed-height so the virtualizer never has to measure them. */
export const ROW_HEIGHT = 46;
/** First guess for a mobile card before it is measured. */
export const CARD_ESTIMATE = 96;

const VISA_SHORT = { citizenship: 'us citizens only', 'no-sponsorship': 'no sponsorship' };
const sep = <span style={{ color: BBG.rule2, margin: '0 6px' }} aria-hidden="true">·</span>;

/** Spoken summary of a job for its option / card button. */
export function jobLabel(j, isSaved) {
  return [
    j.co, j.role, j.loc,
    j.comp[0] != null ? fmtComp(j.comp) : null,
    j.posted !== '—' ? `posted ${j.posted} ago` : null,
    j.visaNote ? VISA_SHORT[j.visaNote] : null,
    j.closed ? 'closed' : null,
    isSaved ? 'saved' : null,
  ].filter(Boolean).join(', ');
}

export function ClosedBadge() {
  return (
    <span style={{
      border: `1px solid ${BBG.hot}`, color: BBG.hot, padding: '0 4px', fontSize: 11,
      fontWeight: 700, letterSpacing: 0.5, marginRight: 6, lineHeight: 1.3,
    }}>CLOSED</span>
  );
}

function MetaLine({ j }) {
  return (
    <>
      {TYPE_LABEL[j.type]}{sep}{RMT_LABEL[j.rmt]}{sep}{TIER_LABEL[j.tier]}
      {j.visaNote && <>{sep}<span style={{ color: BBG.warn }}>{VISA_SHORT[j.visaNote]}</span></>}
    </>
  );
}

function StarButton({ isSaved, onToggle, big, focusable, co }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      // Keep focus on the listbox when the (unfocusable) row star is clicked.
      onMouseDown={focusable ? undefined : (e) => e.preventDefault()}
      // Inside a listbox option the star is a mouse shortcut only (options
      // can't contain interactive children); keyboard users press S or use
      // the SAVE button in the detail pane.
      tabIndex={focusable ? 0 : -1}
      aria-hidden={focusable ? undefined : 'true'}
      aria-label={focusable ? `${isSaved ? 'Remove' : 'Save'} ${co} job` : undefined}
      aria-pressed={focusable ? isSaved : undefined}
      style={{
        background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
        minWidth: big ? 44 : MIN_TARGET, minHeight: big ? 44 : MIN_TARGET,
        color: isSaved ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: big ? 18 : 14, lineHeight: 1,
      }}
    >{isSaved ? '★' : '☆'}</button>
  );
}

export const JobRow = memo(function JobRow({
  job: j, index, count, optionId, isSelected, isSaved, onSelect, onToggleSave, style,
}) {
  return (
    <div
      role="option"
      id={optionId}
      aria-selected={isSelected}
      aria-setsize={count}
      aria-posinset={index + 1}
      aria-label={jobLabel(j, isSaved)}
      data-job-id={j.id}
      onClick={() => onSelect(j.id)}
      style={{
        ...style,
        display: 'grid',
        gridTemplateColumns: JOB_GRID_COLUMNS,
        gap: 8, padding: '0 14px', height: ROW_HEIGHT, boxSizing: 'border-box',
        borderBottom: `1px solid ${BBG.rule}`,
        background: isSelected ? BBG.selBg : 'transparent',
        borderLeft: isSelected ? `2px solid ${BBG.acc}` : '2px solid transparent',
        cursor: 'pointer', alignItems: 'center', overflow: 'hidden',
      }}
    >
      <span style={{ color: BBG.dim, fontSize: 11 }}>{rowNumber(index)}</span>
      <span style={{ color: isSelected ? BBG.acc : BBG.ink, fontWeight: 600, ...ellipsis }}>{j.co}</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ color: j.closed ? BBG.dim : BBG.ink, ...ellipsis }}>
          {j.closed && <ClosedBadge />}{j.role}
        </div>
        <div style={{ color: BBG.dim, fontSize: 11, ...ellipsis }}><MetaLine j={j} /></div>
      </div>
      <span style={{ color: BBG.ink, fontSize: 11.5, ...ellipsis }}>{j.loc}</span>
      <span style={{ color: j.comp[0] != null ? BBG.acc : BBG.dim, fontSize: 11.5 }}>{fmtComp(j.comp)}</span>
      <span style={{ color: BBG.dim, fontSize: 11 }}>{j.posted}</span>
      <StarButton isSaved={isSaved} onToggle={() => onToggleSave(j.id)} co={j.co} />
    </div>
  );
});

// Single-column card: the desktop columns can't fit a phone. The card itself
// is not interactive; it holds two sibling controls (open details, save) so
// no button is nested inside another.
export const JobCard = memo(function JobCard({ job: j, index, isSaved, onOpen, onToggleSave }) {
  return (
    <div style={{
      position: 'relative', borderBottom: `1px solid ${BBG.rule}`,
    }}>
      <button
        type="button"
        onClick={() => onOpen(j.id)}
        aria-label={`${jobLabel(j, isSaved)}. Open details`}
        data-job-id={j.id}
        style={{
          display: 'flex', flexDirection: 'column', gap: 4, width: '100%', textAlign: 'left',
          background: 'transparent', border: 'none', color: 'inherit', fontFamily: 'inherit',
          padding: '11px 56px 11px 14px', cursor: 'pointer', minHeight: 44,
        }}
      >
        <span style={{ color: BBG.acc, fontWeight: 600, fontSize: 12.5 }}>
          <span style={{ color: BBG.dim, marginRight: 6 }}>{rowNumber(index)}</span>{j.co}
        </span>
        <span style={{ color: j.closed ? BBG.dim : BBG.ink, fontSize: 13, lineHeight: 1.3 }}>
          {j.closed && <ClosedBadge />}{j.role}
        </span>
        <span style={{ color: BBG.dim, fontSize: 11, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '2px 0' }}>
          <span>{j.loc}</span>{sep}
          <span style={{ color: j.comp[0] != null ? BBG.acc : BBG.dim }}>{fmtComp(j.comp)}</span>{sep}
          <span>{j.posted}</span>
          {j.visaNote && <>{sep}<span style={{ color: BBG.warn }}>{VISA_SHORT[j.visaNote]}</span></>}
        </span>
      </button>
      <div style={{ position: 'absolute', top: 4, right: 6 }}>
        <StarButton isSaved={isSaved} onToggle={() => onToggleSave(j.id)} big focusable co={j.co} />
      </div>
    </div>
  );
});
