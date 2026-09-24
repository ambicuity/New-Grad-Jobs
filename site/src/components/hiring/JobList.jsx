// Center column: CMD> search bar, sortable table header and the job rows.

import { BBG } from '../../lib/theme.js';
import { SortHeader } from '../ui.jsx';
import { JOB_GRID_COLUMNS, JobCard, JobRow } from './JobRow.jsx';

export function JobList({
  isMobile, searchRef, q, onQuery, filtered, total, sort, onSort,
  selectedId, onSelect, onOpenMobile, saved, onToggleSave,
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}` }}>
      <div style={{ padding: '8px 14px', borderBottom: `1px solid ${BBG.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: BBG.acc, fontWeight: 700 }}>CMD&gt;</span>
        <input
          ref={searchRef}
          value={q}
          onChange={(e) => onQuery(e.target.value)}
          aria-label="Search jobs"
          placeholder="search co / role / stack / loc · / to focus, esc to clear"
          style={{
            background: 'transparent', border: 'none', outline: 'none',
            color: BBG.ink, fontFamily: 'inherit', fontSize: 12.5, flex: 1, letterSpacing: 0.3,
          }}
        />
        <span style={{ color: BBG.dim, fontSize: 11 }}>
          <span style={{ color: BBG.acc, fontWeight: 700 }}>{filtered.length}</span> / {total} results
        </span>
      </div>

      {/* Tabular header — desktop only; mobile cards carry their own labels */}
      {!isMobile && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: JOB_GRID_COLUMNS,
          gap: 8, padding: '4px 14px', borderBottom: `1px solid ${BBG.rule2}`,
          color: BBG.dim, fontSize: 10, letterSpacing: 0.6, background: BBG.panel2,
        }}>
          <span>#</span>
          <SortHeader k="co" label="CO" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <span>ROLE</span>
          <span>LOC</span>
          <SortHeader k="comp" label="COMP" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="posted" label="POSTED" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="deadline" label="DEADLINE" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <span></span>
        </div>
      )}

      <div style={{ overflow: 'auto', flex: 1 }} data-testid="job-list">
        {filtered.map((j, i) => (isMobile ? (
          <JobCard key={j.id} job={j} index={i} isSaved={saved.has(j.id)} onOpen={onOpenMobile} onToggleSave={onToggleSave} />
        ) : (
          <JobRow
            key={j.id}
            job={j}
            index={i}
            isSelected={j.id === selectedId}
            isSaved={saved.has(j.id)}
            onSelect={onSelect}
            onToggleSave={onToggleSave}
          />
        )))}
        {filtered.length === 0 && (
          <div style={{ padding: 24, color: BBG.dim }}>NO MATCHES. CMD&gt; clear filters with Esc</div>
        )}
      </div>
    </div>
  );
}
