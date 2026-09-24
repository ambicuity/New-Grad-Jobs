// Hiring view — Bloomberg-terminal aesthetic: stats strip, filter rail, dense
// job list and a detail pane. The shareable view state (query, filters, sort,
// selected job) lives in the URL and is owned by the App (see
// useUrlViewState); this component derives everything else from it.

import { useCallback, useDeferredValue, useMemo, useRef, useState } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import {
  EMPTY_FILTERS, filterByCompany, filterJobsExceptCompany, toggleFacet, toggleVisa,
} from '../../lib/filters.js';
import { clickJobSort, sortJobs } from '../../lib/sort.js';
import { computeStats } from '../../lib/stats.js';
import { safeHttpUrl } from '../../lib/safe-url.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { useToast } from '../../hooks/useToast.js';
import { useSavedJobs } from '../../hooks/useSavedJobs.js';
import { useDashboardKeys } from '../../hooks/useDashboardKeys.js';
import { MobileOverlay } from '../ui.jsx';
import { StatsStrip } from './StatsStrip.jsx';
import { FilterRail } from './FilterRail.jsx';
import { JobList } from './JobList.jsx';
import { JobDetail } from './JobDetail.jsx';
import { HelpOverlay } from './HelpOverlay.jsx';
import { StatusBar } from './StatusBar.jsx';
import { Toast } from './Toast.jsx';

// history.state marker on the entry pushed when a mobile detail opens, so
// BACK can pop it (instead of stacking another entry).
const DETAIL_STATE = { ngjDetail: true };

/**
 * @param {{
 *   jobs: import('../../lib/jobs.js').Job[],
 *   meta: import('../../lib/jobs.js').JobsMeta,
 *   view: import('../../lib/url-state.js').ViewState,
 *   updateView: (fn: Function, opts?: object) => void,
 * }} props
 */
export function DashboardView({ jobs, meta, view, updateView }) {
  const { q, filters, sort, savedOnly } = view;
  const isMobile = useIsMobile();
  const [saved, toggleSave] = useSavedJobs();
  const [helpOpen, setHelpOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [toast, flash] = useToast();
  const [loadedAt] = useState(() => Date.now());
  const searchRef = useRef(null);
  const listRef = useRef(null);

  // Typing stays responsive: the input updates immediately, filtering the
  // ~1.9k rows runs at lower priority on the deferred query.
  const deferredQ = useDeferredValue(q);
  const jobsById = useMemo(() => new Map(jobs.map((j) => [j.id, j])), [jobs]);
  const stats = useMemo(() => computeStats(jobs, loadedAt), [jobs, loadedAt]);

  // Every facet except company — also feeds HIRING NOW so picking a company
  // doesn't collapse the company list.
  const preCompanyFiltered = useMemo(
    () => filterJobsExceptCompany(jobs, { filters, q: deferredQ, saved, savedOnly }),
    [jobs, filters, deferredQ, saved, savedOnly],
  );
  const filtered = useMemo(
    () => sortJobs(filterByCompany(preCompanyFiltered, filters.company), sort.key, sort.dir),
    [preCompanyFiltered, filters.company, sort],
  );
  const savedCount = useMemo(() => jobs.reduce((n, j) => n + (saved.has(j.id) ? 1 : 0), 0), [jobs, saved]);

  // Desktop: the URL's job (even if the current filters hide it — e.g. picked
  // from SIMILAR ROLES), else the first visible row. Mobile: the URL's job is
  // the open detail, nothing is selected otherwise.
  const urlJob = view.job ? jobsById.get(view.job) || null : null;
  const selected = isMobile ? urlJob : (urlJob || filtered[0] || null);
  const selectedId = selected ? selected.id : null;
  const detailOpen = isMobile && !!urlJob;

  const patch = useCallback((fn, opts) => updateView((v) => ({ ...v, ...fn(v) }), opts), [updateView]);
  const select = useCallback((id) => patch(() => ({ job: id })), [patch]);
  const openMobileDetail = useCallback((id) => patch(() => ({ job: id }), { push: true, state: DETAIL_STATE }), [patch]);
  const closeMobileDetail = useCallback(() => {
    if (window.history.state && window.history.state.ngjDetail) window.history.back();
    else patch(() => ({ job: null }));
  }, [patch]);
  const toggleSet = useCallback((key, val) => patch((v) => ({ filters: toggleFacet(v.filters, key, val) })), [patch]);
  const setVisa = useCallback((val) => patch((v) => ({ filters: toggleVisa(v.filters, val) })), [patch]);
  const setQuery = useCallback((value) => patch(() => ({ q: value })), [patch]);
  const sortClick = useCallback((k) => patch((v) => ({ sort: clickJobSort(v.sort, k) })), [patch]);
  // F2 cycles keys, each in its natural direction (newest / highest / A→Z).
  const setSortKey = useCallback((key) => patch(() => ({ sort: clickJobSort({ key: null, dir: 1 }, key) })), [patch]);
  const clearAll = useCallback(() => patch(() => ({ filters: EMPTY_FILTERS(), q: '', savedOnly: false })), [patch]);
  const toggleSavedOnly = useCallback(() => {
    if (savedCount === 0 && !savedOnly) { flash('no saved jobs yet', BBG.warn); return; }
    patch((v) => ({ savedOnly: !v.savedOnly }));
  }, [savedCount, savedOnly, flash, patch]);
  const openSelected = useCallback(() => {
    if (!selected) return;
    if (isMobile) { openMobileDetail(selected.id); return; }
    const href = safeHttpUrl(selected.url);
    if (!href) { flash('no application link for this job', BBG.warn); return; }
    window.open(href, '_blank', 'noopener,noreferrer');
    flash(`opening ${selected.co.toLowerCase()} ↗`, BBG.acc);
  }, [selected, isMobile, openMobileDetail, flash]);

  useDashboardKeys({
    enabled: !helpOpen && !detailOpen,
    filtered: isMobile ? [] : filtered,
    selectedId,
    select,
    saved,
    toggleSave,
    sortKey: sort.key,
    setSortKey,
    setHelpOpen,
    clearAll,
    searchRef,
    flash,
    openSelected,
  });

  const detail = (
    <JobDetail
      job={selected}
      jobs={jobs}
      saved={!!selected && saved.has(selected.id)}
      onSave={() => selected && toggleSave(selected.id)}
      onSelectJob={isMobile ? (id) => patch(() => ({ job: id })) : select}
    />
  );

  return (
    <div style={{
      width: '100%', minWidth: isMobile ? 0 : 1180,
      height: '100%', minHeight: isMobile ? 0 : 640, background: BBG.bg, color: BBG.ink,
      fontFamily: FONT_STACK, fontSize: 12, lineHeight: 1.45,
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden', position: 'relative',
    }}>
      <StatsStrip stats={stats} isMobile={isMobile} />

      <div style={{
        display: isMobile ? 'flex' : 'grid',
        flexDirection: isMobile ? 'column' : undefined,
        gridTemplateColumns: isMobile ? undefined : '210px 1fr 460px',
        minHeight: 0,
        overflow: 'hidden',
      }}>
        <FilterRail
          isMobile={isMobile}
          open={filtersOpen}
          onToggleOpen={() => setFiltersOpen((o) => !o)}
          filters={filters}
          onToggle={toggleSet}
          onVisa={setVisa}
          jobs={jobs}
          preCompanyFiltered={preCompanyFiltered}
        />
        <JobList
          isMobile={isMobile}
          searchRef={searchRef}
          listRef={listRef}
          q={q}
          onQuery={setQuery}
          isStale={q !== deferredQ}
          filtered={filtered}
          total={jobs.length}
          sort={sort}
          onSort={sortClick}
          selectedId={selectedId}
          onSelect={select}
          onOpenMobile={openMobileDetail}
          saved={saved}
          onToggleSave={toggleSave}
        />
        {!isMobile && detail}
      </div>

      {detailOpen && (
        <MobileOverlay
          title={`${selected.co} · ${selected.role}`}
          backLabel="Back to job list"
          onBack={closeMobileDetail}
        >
          {detail}
        </MobileOverlay>
      )}

      <Toast toast={toast} />
      {helpOpen && <HelpOverlay onClose={() => setHelpOpen(false)} />}

      <StatusBar
        isMobile={isMobile}
        generatedAt={meta && meta.generated_at}
        count={filtered.length}
        savedCount={savedCount}
        savedOnly={savedOnly}
        onToggleSavedOnly={toggleSavedOnly}
      />
    </div>
  );
}
