// Center column of the contributors view: stats strip + search, table header, rows.

import { useMemo } from 'react';
import { AREA_COLOR, BBG } from '../../lib/theme.js';
import { fmtK, rowNumber } from '../../lib/format.js';
import { activeThisWeek, contributorTotals, roleColor } from '../../lib/contributors.js';
import { SortHeader, Stat, ellipsis, onActivateKey } from '../ui.jsx';
import { Avatar, PMBar } from './ContribBits.jsx';

const GRID = '32px 130px 1fr 90px 70px 60px 110px 80px 70px';
const recentColor = (last) => (/h$|^1d/.test(last) ? BBG.ok : BBG.ink);
const dot = <span style={{ color: BBG.rule2 }}>·</span>;

export function ContribTable({
  isMobile, contributors, filtered, searchRef, q, onQuery, sort, onSort, selectedHandle, onSelect,
}) {
  const totals = useMemo(() => contributorTotals(contributors), [contributors]);
  const activeWeek = useMemo(() => activeThisWeek(contributors), [contributors]);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}` }}>
      <div style={{
        display: 'flex', gap: isMobile ? 12 : 18, padding: '10px 14px',
        borderBottom: `1px solid ${BBG.rule2}`, alignItems: 'center',
        flexWrap: isMobile ? 'wrap' : 'nowrap',
      }}>
        <Stat label="CONTRIBUTORS" value={contributors.length} delta="+3 7d" deltaC={BBG.ok} />
        <Stat label="COMMITS" value={fmtK(totals.commits)} delta="+412 7d" deltaC={BBG.ok} />
        <Stat label="PRS MERGED" value={fmtK(totals.prs)} delta="+98 7d" deltaC={BBG.ok} />
        <Stat label="ACTIVE 7D" value={activeWeek} delta="" deltaC={BBG.dim} />
        <Stat label="NET LOC" value={`+${fmtK(totals.add)} / -${fmtK(totals.del)}`} delta="" deltaC={BBG.dim} />
        <div style={{
          marginLeft: isMobile ? 0 : 'auto', width: isMobile ? '100%' : 'auto',
          display: 'flex', gap: 8, alignItems: 'center',
        }}>
          <span style={{ color: BBG.acc, fontWeight: 700 }}>CMD&gt;</span>
          <input
            ref={searchRef}
            value={q}
            onChange={(e) => onQuery(e.target.value)}
            aria-label="Search contributors"
            placeholder="search @handle / name / area / region"
            style={{
              background: 'transparent', border: `1px solid ${BBG.rule2}`, outline: 'none',
              color: BBG.ink, fontFamily: 'inherit', fontSize: 12, padding: '3px 8px',
              width: isMobile ? 'auto' : 260, flex: isMobile ? 1 : 'none', letterSpacing: 0.3,
            }}
          />
        </div>
      </div>

      {!isMobile && (
        <div style={{
          display: 'grid', gridTemplateColumns: GRID,
          gap: 8, padding: '4px 14px', borderBottom: `1px solid ${BBG.rule2}`,
          color: BBG.dim, fontSize: 10, letterSpacing: 0.6, background: BBG.panel2,
        }}>
          <span>#</span>
          <SortHeader k="handle" label="@HANDLE" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <span>NAME / AREAS</span>
          <span>REGION</span>
          <SortHeader k="commits" label="COMMITS" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="prs" label="PRS" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="add" label="+/-" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="since" label="SINCE" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="last" label="LAST" cur={sort.key} dir={sort.dir} onClick={onSort} />
        </div>
      )}

      <div style={{ overflow: 'auto', flex: 1 }}>
        {filtered.map((c, i) => (isMobile
          ? <ContribCard key={c.handle} c={c} index={i} onOpen={() => onSelect(c.handle, true)} />
          : <ContribRow key={c.handle} c={c} index={i} isSel={c.handle === selectedHandle} onSelect={() => onSelect(c.handle, false)} />
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: 24, color: BBG.dim }}>NO MATCHES. clear filters or refine search.</div>
        )}
      </div>
    </div>
  );
}

function ContribRow({ c, index, isSel, onSelect }) {
  return (
    <div onClick={onSelect} style={{
      display: 'grid', gridTemplateColumns: GRID,
      gap: 8, padding: '7px 14px',
      borderBottom: `1px solid ${BBG.rule}`,
      background: isSel ? BBG.selBg : 'transparent',
      borderLeft: isSel ? `2px solid ${BBG.acc}` : '2px solid transparent',
      cursor: 'pointer', alignItems: 'center',
    }}>
      <span style={{ color: BBG.dim, fontSize: 11 }}>{rowNumber(index)}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
        <Avatar handle={c.handle} size={20} />
        <span style={{ color: isSel ? BBG.acc : BBG.ink, fontWeight: 600, ...ellipsis }}>@{c.handle}</span>
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ color: BBG.ink, ...ellipsis }}>
          {c.name}
          <span style={{ color: roleColor(c.role), marginLeft: 8, fontSize: 10, letterSpacing: 0.5 }}>{c.role.toUpperCase()}</span>
        </div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'nowrap', overflow: 'hidden' }}>
          {c.areas.slice(0, 4).map((a) => (
            <span key={a} style={{ fontSize: 9.5, color: AREA_COLOR[a] || BBG.dim }}>
              <span style={{ display: 'inline-block', width: 5, height: 5, background: AREA_COLOR[a] || BBG.dim, marginRight: 2 }} />
              {a}
            </span>
          ))}
        </div>
      </div>
      <span style={{ color: BBG.dim, fontSize: 11, ...ellipsis }}>{c.region}</span>
      <span style={{ color: BBG.acc, fontSize: 11.5 }}>{c.commits.toLocaleString()}</span>
      <span style={{ color: BBG.ink, fontSize: 11.5 }}>{c.prs}</span>
      <PMBar add={c.add} del={c.del} />
      <span style={{ color: BBG.dim, fontSize: 11 }}>{c.since}</span>
      <span style={{ color: recentColor(c.last), fontSize: 11 }}>{c.last}</span>
    </div>
  );
}

// Single-column card; tap opens the full-screen contributor detail.
function ContribCard({ c, index, onOpen }) {
  return (
    <div onClick={onOpen}
      role="button" tabIndex={0}
      aria-label={`@${c.handle} — ${c.name}, open details`}
      onKeyDown={onActivateKey(onOpen)}
      style={{
        padding: '11px 14px', borderBottom: `1px solid ${BBG.rule}`,
        cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 5,
      }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color: BBG.dim, fontSize: 11 }}>{rowNumber(index)}</span>
        <Avatar handle={c.handle} size={22} />
        <span style={{ color: BBG.acc, fontWeight: 600, fontSize: 12.5 }}>@{c.handle}</span>
        <span style={{ color: roleColor(c.role), fontSize: 10, letterSpacing: 0.5, marginLeft: 'auto' }}>{c.role.toUpperCase()}</span>
      </div>
      <div style={{ color: BBG.ink, fontSize: 12.5 }}>{c.name}</div>
      <div style={{ color: BBG.dim, fontSize: 11, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '2px 6px' }}>
        <span>{c.region}</span>
        {dot}
        <span style={{ color: BBG.acc }}>{c.commits.toLocaleString()} commits</span>
        {dot}
        <span>{c.prs} prs</span>
        {dot}
        <span style={{ color: BBG.ok }}>+{fmtK(c.add)}</span>
        <span style={{ color: BBG.hot }}>-{fmtK(c.del)}</span>
        {dot}
        <span style={{ color: recentColor(c.last) }}>{c.last}</span>
      </div>
    </div>
  );
}
