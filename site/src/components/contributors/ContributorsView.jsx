// Contributors view — same Bloomberg-terminal chrome as Hiring.

import { useCallback, useMemo, useRef, useState } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import { toggleFacet } from '../../lib/filters.js';
import { clickSort } from '../../lib/sort.js';
import {
  DEFAULT_REPO, EMPTY_CONTRIB_FILTERS, facetOptions, filterContributors, sortContributors,
} from '../../lib/contributors.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { usePromiseSettled } from '../../hooks/usePromiseSettled.js';
import { FKey, MobileOverlay } from '../ui.jsx';
import { ContribRail } from './ContribRail.jsx';
import { ContribTable } from './ContribTable.jsx';
import { ContribDetail } from './ContribDetail.jsx';
import { useContribKeys } from './useContribKeys.js';

/**
 * Contributors tab entry point. The app mounts as soon as jobs load, so
 * contributors.json + the GitHub API enrichment may still be in flight; show a
 * loading line until the promise settles, then mount the real view.
 */
export function ContributorsView({ contributorsPromise }) {
  const { settled, value } = usePromiseSettled(contributorsPromise);
  if (!settled) {
    return (
      <div role="status" style={{
        height: '100%', background: BBG.bg, padding: '24px',
        fontFamily: FONT_STACK, fontSize: 12, letterSpacing: 0.6,
      }}>
        <span style={{ color: BBG.acc }}>CONTRIBUTORS</span>{' '}
        <span style={{ color: BBG.dim }}>loading contributors.json + github stats …</span>
      </div>
    );
  }
  return (
    <ContributorsBody
      contributors={(value && value.contributors) || []}
      repo={(value && value.repo) || DEFAULT_REPO}
    />
  );
}

function ContributorsBody({ contributors, repo }) {
  const [q, setQ] = useState('');
  const [filters, setFilters] = useState(EMPTY_CONTRIB_FILTERS);
  const [sort, setSort] = useState({ key: 'commits', dir: 1 });
  const [selectedHandle, setSelectedHandle] = useState(() => contributors[0]?.handle ?? null);
  // Mobile reflow: repo card + filters + leaderboard collapse into a drawer,
  // and tapping a contributor opens a full-screen detail (no 460px side panel).
  const isMobile = useIsMobile();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);
  const searchRef = useRef(null);

  const options = useMemo(() => facetOptions(contributors), [contributors]);
  const filtered = useMemo(
    () => sortContributors(filterContributors(contributors, filters, q), sort.key, sort.dir),
    [contributors, filters, q, sort],
  );

  // Keep the selection on a visible row (state adjustment during render).
  if (!filtered.some((c) => c.handle === selectedHandle) && filtered[0]) {
    setSelectedHandle(filtered[0].handle);
  }
  const selected = contributors.find((c) => c.handle === selectedHandle) || filtered[0];

  const toggleSet = (key, val) => setFilters((f) => toggleFacet(f, key, val));
  const sortClick = (k) => setSort((s) => clickSort(s, k));
  const clearAll = useCallback(() => {
    setQ('');
    setFilters(EMPTY_CONTRIB_FILTERS());
  }, []);
  const toggleSort = useCallback(
    () => setSort((s) => ({ key: s.key === 'commits' ? 'handle' : 'commits', dir: 1 })),
    [],
  );
  useContribKeys({
    enabled: !isMobile, filtered, selected, setSelectedHandle, searchRef, clearAll, toggleSort,
  });
  const select = (handle, openOnMobile) => {
    setSelectedHandle(handle);
    if (openOnMobile && isMobile) setMobileDetailOpen(true);
  };

  return (
    <div style={{
      width: '100%', minWidth: isMobile ? 0 : 1180,
      height: '100%', minHeight: isMobile ? 0 : 640, background: BBG.bg, color: BBG.ink,
      fontFamily: FONT_STACK, fontSize: 12, lineHeight: 1.45,
      display: 'grid', gridTemplateRows: '1fr auto', overflow: 'hidden', position: 'relative',
    }}>
      <div style={{
        display: isMobile ? 'block' : 'grid',
        gridTemplateColumns: isMobile ? undefined : '220px 1fr 460px',
        minHeight: 0,
        overflowY: isMobile ? 'auto' : 'hidden',
      }}>
        <ContribRail
          isMobile={isMobile}
          open={drawerOpen}
          onToggleOpen={() => setDrawerOpen((o) => !o)}
          repo={repo}
          options={options}
          filters={filters}
          onToggle={toggleSet}
          filtered={filtered}
          selectedHandle={selectedHandle}
          onSelect={(h) => select(h, true)}
        />
        <ContribTable
          isMobile={isMobile}
          contributors={contributors}
          repo={repo}
          filtered={filtered}
          searchRef={searchRef}
          q={q}
          onQuery={setQ}
          sort={sort}
          onSort={sortClick}
          selectedHandle={selectedHandle}
          onSelect={select}
        />
        {!isMobile && <ContribDetail c={selected} contributors={contributors} />}
      </div>

      {isMobile && mobileDetailOpen && selected && (
        <MobileOverlay
          title={`@${selected.handle} · ${selected.name}`}
          backLabel="Back to contributor list"
          onBack={() => setMobileDetailOpen(false)}
        >
          <ContribDetail c={selected} contributors={contributors} />
        </MobileOverlay>
      )}

      <div style={{
        borderTop: `1px solid ${BBG.rule2}`, padding: '5px 14px', background: BBG.panel,
        display: 'flex', gap: 18, fontSize: 11, color: BBG.dim,
      }}>
        <span>STATUS: <span style={{ color: BBG.ok }}>OK</span></span>
        <span>SHOWN: <span style={{ color: BBG.ink }}>{filtered.length}</span> / {contributors.length}</span>
        <span>SEL: <span style={{ color: BBG.ink }}>@{selected?.handle || '—'}</span></span>
        {!isMobile && (
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }}>
            <FKey n="/" l="SEARCH" />
            <FKey n="F2" l="SORT" />
            <FKey n="ESC" l="CLEAR" />
            <FKey n="G" l="GITHUB ↗" />
          </span>
        )}
      </div>
    </div>
  );
}
