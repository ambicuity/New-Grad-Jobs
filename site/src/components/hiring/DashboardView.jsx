// Hiring view — Bloomberg-terminal aesthetic: stats strip, filter rail, dense
// job table and a detail pane. This component owns the view state; the pieces
// it renders are presentational.

import { useCallback, useMemo, useRef, useState } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import {
  EMPTY_FILTERS, filterByCompany, filterJobsExceptCompany, toggleFacet, toggleInSet, toggleVisa,
} from '../../lib/filters.js';
import { clickSort, reconcileSelection, sortJobs } from '../../lib/sort.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { useToast } from '../../hooks/useToast.js';
import { useDashboardKeys } from '../../hooks/useDashboardKeys.js';
import { MobileOverlay } from '../ui.jsx';
import { StatsStrip } from './StatsStrip.jsx';
import { FilterRail } from './FilterRail.jsx';
import { JobList } from './JobList.jsx';
import { JobDetail } from './JobDetail.jsx';
import { HelpOverlay } from './HelpOverlay.jsx';
import { StatusBar } from './StatusBar.jsx';
import { Toast } from './Toast.jsx';

/** @param {{jobs: import('../../lib/jobs.js').Job[]}} props */
export function DashboardView({ jobs }) {
  const [q, setQ] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sort, setSort] = useState({ key: 'posted', dir: 1 });
  const [selectedId, setSelectedId] = useState(() => jobs[0]?.id ?? null);
  // Saved-job ids are user-driven (press S, or click the ☆ in a row); start empty.
  const [saved, setSaved] = useState(() => new Set());
  const [savedOnly, setSavedOnly] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  // Mobile reflow: filters collapse into a drawer, and tapping a job opens a
  // full-screen detail view (there's no room for the 460px side panel).
  const isMobile = useIsMobile();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);
  const [toast, flash] = useToast();
  const searchRef = useRef(null);

  // Every facet except company — also feeds HIRING NOW so picking a company
  // doesn't collapse the company list.
  const preCompanyFiltered = useMemo(
    () => filterJobsExceptCompany(jobs, { filters, q, saved, savedOnly }),
    [jobs, filters, q, saved, savedOnly],
  );
  const filtered = useMemo(
    () => sortJobs(filterByCompany(preCompanyFiltered, filters.company), sort.key, sort.dir),
    [preCompanyFiltered, filters.company, sort],
  );

  // Keep the selection on a visible row (adjusting state during render is the
  // React-recommended alternative to a sync effect).
  const reconciledId = reconcileSelection(filtered, selectedId);
  if (reconciledId !== selectedId) setSelectedId(reconciledId);

  // null when there are no jobs at all (or none match) — consumers cope with that.
  const selected = useMemo(
    () => jobs.find((j) => j.id === reconciledId) || filtered[0] || null,
    [jobs, filtered, reconciledId],
  );

  const toggleSet = useCallback((key, val) => setFilters((f) => toggleFacet(f, key, val)), []);
  const setVisa = useCallback((val) => setFilters((f) => toggleVisa(f, val)), []);
  const toggleSave = useCallback((id) => setSaved((s) => toggleInSet(s, id)), []);
  const sortClick = useCallback((k) => setSort((s) => clickSort(s, k)), []);
  const setSortKey = useCallback((key) => setSort((s) => ({ ...s, key })), []);
  const clearAll = useCallback(() => {
    setFilters(EMPTY_FILTERS());
    setQ('');
    setSavedOnly(false);
  }, []);
  const toggleSavedOnly = useCallback(() => {
    if (saved.size === 0) { flash('no saved jobs', BBG.warn); return; }
    setSavedOnly((v) => !v);
  }, [saved, flash]);
  const openMobileDetail = useCallback((id) => { setSelectedId(id); setMobileDetailOpen(true); }, []);

  useDashboardKeys({
    filtered, selected, selectedId: reconciledId, setSelectedId, saved, toggleSave,
    sortKey: sort.key, setSortKey, helpOpen, setHelpOpen, clearAll, searchRef, flash,
  });

  const detail = (
    <JobDetail
      job={selected}
      jobs={jobs}
      saved={saved.has(selected?.id)}
      onSave={() => selected && toggleSave(selected.id)}
    />
  );

  return (
    <div style={{
      width: '100%', minWidth: isMobile ? 0 : 1180,
      height: '100%', minHeight: isMobile ? 0 : 640, background: BBG.bg, color: BBG.ink,
      fontFamily: FONT_STACK, fontSize: 12, lineHeight: 1.45,
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden', position: 'relative',
    }}>
      <StatsStrip jobs={jobs} isMobile={isMobile} />

      <div style={{
        display: isMobile ? 'block' : 'grid',
        gridTemplateColumns: isMobile ? undefined : '210px 1fr 460px',
        minHeight: 0,
        overflowY: isMobile ? 'auto' : 'hidden',
      }}>
        <FilterRail
          isMobile={isMobile}
          open={filtersOpen}
          onToggleOpen={() => setFiltersOpen((o) => !o)}
          filters={filters}
          onToggle={toggleSet}
          onVisa={setVisa}
          filtered={filtered}
          preCompanyFiltered={preCompanyFiltered}
        />
        <JobList
          isMobile={isMobile}
          searchRef={searchRef}
          q={q}
          onQuery={setQ}
          filtered={filtered}
          total={jobs.length}
          sort={sort}
          onSort={sortClick}
          selectedId={reconciledId}
          onSelect={setSelectedId}
          onOpenMobile={openMobileDetail}
          saved={saved}
          onToggleSave={toggleSave}
        />
        {!isMobile && detail}
      </div>

      {isMobile && mobileDetailOpen && selected && (
        <MobileOverlay
          title={`${selected.co} · ${selected.role}`}
          backLabel="Back to job list"
          onBack={() => setMobileDetailOpen(false)}
        >
          {detail}
        </MobileOverlay>
      )}

      <Toast toast={toast} />
      {helpOpen && <HelpOverlay onClose={() => setHelpOpen(false)} />}

      <StatusBar
        isMobile={isMobile}
        count={filtered.length}
        savedCount={saved.size}
        savedOnly={savedOnly}
        onToggleSavedOnly={toggleSavedOnly}
      />
    </div>
  );
}
