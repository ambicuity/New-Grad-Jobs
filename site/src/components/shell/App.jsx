// App shell — top bar with tabs, swaps between the Hiring and Contributors views.

import { useEffect, useState } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import { ErrorBoundary } from './ErrorBoundary.jsx';
import { TopBar } from './TopBar.jsx';
import { SiteFooter } from './SiteFooter.jsx';
import { HiringTab } from '../hiring/HiringTab.jsx';
import { ContributorsView } from '../contributors/ContributorsView.jsx';

const TAB_IDS = ['hiring', 'contributors'];

export function tabFromHash(hash) {
  const h = (hash || '').replace('#', '');
  return TAB_IDS.includes(h) ? h : 'hiring';
}

/**
 * @param {{
 *   jobsState: import('../../data/jobs-source.js').JobsState,
 *   contributorsPromise: Promise<import('../../data/contributors-source.js').ContributorsState>,
 * }} props
 */
export function App({ jobsState, contributorsPromise }) {
  const [tab, setTab] = useState(() => tabFromHash(window.location.hash));

  useEffect(() => {
    window.location.hash = tab;
  }, [tab]);

  return (
    <div style={{
      width: '100%', height: '100%', background: BBG.bg, color: BBG.ink,
      fontFamily: FONT_STACK,
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden',
    }}>
      <TopBar tab={tab} setTab={setTab} jobsState={jobsState} contributorsPromise={contributorsPromise} />
      <div style={{ minHeight: 0, overflow: 'hidden' }}>
        {/* Per-tab boundary: a crash in one view (e.g. contributors) leaves the
            top bar working so the user can switch back to the other tab. */}
        <ErrorBoundary key={tab} scope={tab}>
          {tab === 'hiring'
            ? <HiringTab jobsState={jobsState} />
            : <ContributorsView contributorsPromise={contributorsPromise} />}
        </ErrorBoundary>
      </div>
      <SiteFooter />
    </div>
  );
}
