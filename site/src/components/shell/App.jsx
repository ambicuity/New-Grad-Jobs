// App shell — skip links, top bar with tabs, and the Hiring / Contributors /
// Explore views. The view state (tab, search, filters, sort, selected job) lives in
// the URL via useUrlViewState, so switching tabs, reloading or sharing a link
// keeps it.

import './a11y.css';
import { useCallback } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import { useUrlViewState } from '../../hooks/useUrlViewState.js';
import { ErrorBoundary } from './ErrorBoundary.jsx';
import { TopBar } from './TopBar.jsx';
import { SiteFooter } from './SiteFooter.jsx';
import { HiringTab } from '../hiring/HiringTab.jsx';
import { JOB_LIST_ID, JOB_SEARCH_ID } from '../hiring/JobList.jsx';
import { ContributorsView } from '../contributors/ContributorsView.jsx';
import { ExploreView } from '../explore/ExploreView.jsx';

export const MAIN_ID = 'main';
export const TABPANEL_ID = 'tabpanel';

/** Skip-link target: focus the element without touching location.hash (the URL holds view state). */
function focusById(id) {
  return (e) => {
    const el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    if (!el.hasAttribute('tabindex') && !/^(INPUT|BUTTON|A|SELECT|TEXTAREA)$/.test(el.tagName)) {
      el.setAttribute('tabindex', '-1');
    }
    el.focus();
  };
}

function SkipLinks({ tab }) {
  const links = tab === 'hiring'
    ? [[JOB_LIST_ID, 'Skip to job list'], [JOB_SEARCH_ID, 'Skip to job search']]
    : [[MAIN_ID, 'Skip to main content']];
  return links.map(([id, label]) => (
    <a key={id} className="ngj-skip" href={`#${id}`} onClick={focusById(id)}>{label}</a>
  ));
}

/**
 * @param {{
 *   jobsState: import('../../data/jobs-source.js').JobsState,
 *   contributorsPromise: Promise<import('../../data/contributors-source.js').ContributorsState>,
 * }} props
 */
export function App({ jobsState, contributorsPromise }) {
  const [view, updateView] = useUrlViewState();
  const { tab } = view;
  // A tab switch is navigation: push, so Back returns to the previous tab.
  const setTab = useCallback((next) => updateView((v) => ({ ...v, tab: next }), { push: true }), [updateView]);

  return (
    <div style={{
      width: '100%', height: '100%', background: BBG.bg, color: BBG.ink,
      fontFamily: FONT_STACK, position: 'relative',
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden',
    }}>
      <SkipLinks tab={tab} />
      <h1 className="ngj-sr-only">New Grad Jobs — live board of new-grad and entry-level roles in every field</h1>
      <TopBar tab={tab} setTab={setTab} jobsState={jobsState} contributorsPromise={contributorsPromise} />
      <main id={MAIN_ID} tabIndex={-1} style={{ minHeight: 0, overflow: 'hidden', outline: 'none' }}>
        <div id={TABPANEL_ID} role="tabpanel" aria-labelledby={`tab-${tab}`} style={{ height: '100%' }}>
          {/* Per-tab boundary: a crash in one view (e.g. contributors) leaves the
              top bar working so the user can switch back to the other tab. */}
          <ErrorBoundary key={tab} scope={tab}>
            {tab === 'hiring' && <HiringTab jobsState={jobsState} view={view} updateView={updateView} />}
            {tab === 'contributors' && <ContributorsView contributorsPromise={contributorsPromise} />}
            {tab === 'explore' && <ExploreView view={view} updateView={updateView} />}
          </ErrorBoundary>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
