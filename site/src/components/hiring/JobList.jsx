// Center column: CMD> search bar, sortable header and the (virtualized) job
// list. Only the rows in view (+ overscan) are in the DOM, so ~1.9k jobs cost
// a few dozen rows instead of tens of thousands of nodes.
//
// Desktop: the scroll container is a single-select listbox. It keeps focus
// and points at the selected row with aria-activedescendant; the global j/k
// shortcuts move the selection and the selected row is scrolled into view
// (nearest edge), which also guarantees it is rendered.
// Mobile: a plain list of cards, each with its own buttons.

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { BBG } from '../../lib/theme.js';
import { SortHeader } from '../ui.jsx';
import { CARD_ESTIMATE, JOB_GRID_COLUMNS, JobCard, JobRow, ROW_HEIGHT } from './JobRow.jsx';

const OVERSCAN = 8;
export const JOB_LIST_ID = 'job-list';
export const JOB_SEARCH_ID = 'job-search';
const optionId = (i) => `job-opt-${i}`;

export function JobList({
  isMobile, searchRef, listRef, q, onQuery, isStale, filtered, total, sort, onSort,
  selectedId, onSelect, onOpenMobile, saved, onToggleSave,
}) {
  const scrollRef = useRef(null);
  const setScrollRef = useCallback((node) => {
    scrollRef.current = node;
    if (listRef) listRef.current = node;
  }, [listRef]);

  // The project doesn't run the React Compiler; the virtualizer instance is
  // stable and read fresh each render, which is what this warning is about.
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => (isMobile ? CARD_ESTIMATE : ROW_HEIGHT),
    getItemKey: (i) => filtered[i].id,
    overscan: OVERSCAN,
  });

  const selectedIndex = useMemo(
    () => (isMobile ? -1 : filtered.findIndex((j) => j.id === selectedId)),
    [isMobile, filtered, selectedId],
  );

  // Keep the keyboard selection visible (and therefore rendered, so
  // aria-activedescendant always points at a real element).
  useEffect(() => {
    if (selectedIndex >= 0) virtualizer.scrollToIndex(selectedIndex, { align: 'auto' });
  }, [selectedIndex, virtualizer]);

  const selectRow = useCallback((id) => {
    onSelect(id);
    scrollRef.current?.focus({ preventScroll: true });
  }, [onSelect]);

  const items = virtualizer.getVirtualItems();
  const count = filtered.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, flex: 1, borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}` }}>
      <div style={{ padding: '8px 14px', borderBottom: `1px solid ${BBG.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
        <label htmlFor={JOB_SEARCH_ID} style={{ color: BBG.acc, fontWeight: 700 }}>
          <span aria-hidden="true">CMD&gt;</span>
        </label>
        <input
          id={JOB_SEARCH_ID}
          ref={searchRef}
          type="text"
          aria-label="Search jobs"
          enterKeyHint="search"
          value={q}
          onChange={(e) => onQuery(e.target.value)}
          aria-controls={JOB_LIST_ID}
          aria-describedby="job-result-count"
          placeholder="search company / role / location · / to focus"
          autoComplete="off"
          spellCheck={false}
          style={{
            background: 'transparent', border: 'none',
            color: BBG.ink, fontFamily: 'inherit', fontSize: 12.5, flex: 1, minWidth: 0, letterSpacing: 0.3,
            minHeight: 24,
          }}
        />
        <span id="job-result-count" style={{ color: BBG.dim, fontSize: 11, whiteSpace: 'nowrap' }} aria-live="polite">
          <span style={{ color: BBG.acc, fontWeight: 700 }}>{count}</span> / {total} results
        </span>
      </div>

      {/* Header sits outside the scroller so it stays put (desktop only). */}
      {!isMobile && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: JOB_GRID_COLUMNS,
          gap: 8, padding: '4px 14px', borderBottom: `1px solid ${BBG.rule2}`,
          color: BBG.dim, fontSize: 11, letterSpacing: 0.6, background: BBG.panel2,
          borderLeft: '2px solid transparent',
        }}>
          <span aria-hidden="true">#</span>
          <SortHeader k="co" label="CO" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <span aria-hidden="true">ROLE</span>
          <span aria-hidden="true">LOC</span>
          <SortHeader k="comp" label="COMP" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <SortHeader k="posted" label="POSTED" cur={sort.key} dir={sort.dir} onClick={onSort} />
          <span />
        </div>
      )}

      <div
        ref={setScrollRef}
        id={JOB_LIST_ID}
        data-testid="job-list"
        {...(isMobile
          ? { tabIndex: -1, 'aria-label': 'Jobs' }
          : {
            role: 'listbox',
            tabIndex: 0,
            'aria-label': `Jobs, ${count} results`,
            'aria-activedescendant': selectedIndex >= 0 ? optionId(selectedIndex) : undefined,
          })}
        aria-busy={isStale || undefined}
        style={{ overflow: 'auto', flex: 1, minHeight: 0, opacity: isStale ? 0.7 : 1 }}
      >
        <div
          role={isMobile ? 'list' : 'presentation'}
          style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}
        >
          {items.map((vi) => {
            const j = filtered[vi.index];
            const place = { position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)` };
            if (isMobile) {
              return (
                <div
                  key={vi.key}
                  role="listitem"
                  aria-setsize={count}
                  aria-posinset={vi.index + 1}
                  data-index={vi.index}
                  ref={virtualizer.measureElement}
                  style={place}
                >
                  <JobCard job={j} index={vi.index} isSaved={saved.has(j.id)} onOpen={onOpenMobile} onToggleSave={onToggleSave} />
                </div>
              );
            }
            return (
              <JobRow
                key={vi.key}
                job={j}
                index={vi.index}
                count={count}
                optionId={optionId(vi.index)}
                isSelected={j.id === selectedId}
                isSaved={saved.has(j.id)}
                onSelect={selectRow}
                onToggleSave={onToggleSave}
                style={place}
              />
            );
          })}
        </div>
        {count === 0 && (
          <div role={isMobile ? undefined : 'option'} aria-selected={isMobile ? undefined : false} aria-disabled={isMobile ? undefined : true} style={{ padding: 24, color: BBG.dim }}>
            NO MATCHES. CMD&gt; clear filters with Esc
          </div>
        )}
      </div>
    </div>
  );
}
