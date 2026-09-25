import { BBG } from '../../lib/theme.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { usePromiseSettled } from '../../hooks/usePromiseSettled.js';
import { LiveStamp } from './LiveStamp.jsx';
import { SponsoredBy, SponsorLink } from './Sponsor.jsx';

const TAB_ORDER = ['hiring', 'contributors', 'explore'];

/** The NGJ monogram from public/favicon.svg, drawn inline so it never flashes. */
function Monogram() {
  return (
    <svg aria-hidden="true" viewBox="0 0 64 64" width="22" height="22" style={{ display: 'block', flexShrink: 0 }}>
      <rect width="64" height="64" rx="10" fill={BBG.acc} />
      <g fill="none" stroke="#000" strokeWidth="6" strokeLinecap="square" strokeLinejoin="miter">
        <polyline points="10,46 10,22 22,46 22,22" />
        <polyline points="42,22 30,22 30,46 42,46 42,34 36,34" />
        <polyline points="56,22 56,42 52,46 47,46 44,42" />
      </g>
    </svg>
  );
}

export function TopBar({ tab, setTab, jobsState, contributorsPromise }) {
  const isMobile = useIsMobile();
  // Contributors data may still be loading when the app first paints.
  const contrib = usePromiseSettled(contributorsPromise);
  const devCount = contrib.value ? contrib.value.contributors.length : 0;
  const openCount = jobsState.jobs.filter((j) => !j.closed).length;
  const tabs = [
    { id: 'hiring', label: 'HIRING', sub: jobsState.error ? 'offline' : `${openCount} open` },
    { id: 'contributors', label: 'CONTRIBUTORS', sub: contrib.settled ? `${devCount} devs` : '… devs' },
    // Every posting the run saw, your own signals; the corpus loads only when opened.
    { id: 'explore', label: 'EXPLORE', sub: 'all postings' },
  ];

  // WAI-ARIA tabs: arrow keys move between tabs (roving tabindex).
  const onTabKey = (e) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = TAB_ORDER[(TAB_ORDER.indexOf(tab) + step + TAB_ORDER.length) % TAB_ORDER.length];
    setTab(next);
    document.getElementById(`tab-${next}`)?.focus();
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      borderBottom: `1px solid ${BBG.rule2}`, background: BBG.bg,
      fontSize: 12,
      // Mobile: let the bar wrap so the meta cluster drops to its own row
      // instead of forcing horizontal scroll on a phone.
      height: isMobile ? 'auto' : 38,
      minHeight: 38,
      flexWrap: isMobile ? 'wrap' : 'nowrap',
    }}>
      <a href="./" aria-label="NGJ, New Grad Jobs, home" style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '0 14px', borderRight: `1px solid ${BBG.rule2}`,
        textDecoration: 'none', color: BBG.ink,
        minHeight: isMobile ? 44 : 24, // WCAG 2.2 target size, comfortable on touch
      }}>
        <Monogram />
        {!isMobile && (
          <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.05 }}>
            <span style={{ color: BBG.acc, fontWeight: 700, fontSize: 12, letterSpacing: 1.2 }}>NGJ</span>
            <span style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.6 }}>new grad jobs</span>
          </span>
        )}
      </a>

      <div style={{ display: 'flex' }} role="tablist" aria-label="Views" onKeyDown={onTabKey}>
        {tabs.map((t) => {
          const active = t.id === tab;
          return (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls="tabpanel"
              tabIndex={active ? 0 : -1}
              onClick={() => { if (!active) setTab(t.id); }}
              style={{
                background: active ? BBG.selBg : 'transparent',
                border: 'none',
                borderRight: `1px solid ${BBG.rule2}`,
                borderBottom: active ? `2px solid ${BBG.acc}` : '2px solid transparent',
                color: active ? BBG.acc : BBG.ink,
                padding: '0 18px',
                minHeight: isMobile ? 44 : 'auto', // comfortable touch target on phones
                fontFamily: 'inherit', fontSize: 12, fontWeight: active ? 700 : 500,
                cursor: 'pointer', letterSpacing: 0.5,
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              <span>{t.label}</span>
              <span style={{ color: BBG.dim, fontWeight: 400, fontSize: 11 }}>{t.sub}</span>
            </button>
          );
        })}
      </div>

      <div style={{
        marginLeft: 'auto', display: 'flex', alignItems: 'center',
        gap: isMobile ? 10 : 14, padding: isMobile ? '4px 12px' : '0 14px',
        fontSize: 11, color: BBG.dim,
        flexWrap: isMobile ? 'wrap' : 'nowrap',
      }}>
        <LiveStamp generatedAt={jobsState.meta.generated_at} />
        <SponsoredBy />
        <SponsorLink />
        {/* Keyboard-only hint (F1 and ? both open the hiring shortcut sheet), so hidden on touch. */}
        {!isMobile && tab === 'hiring' && (
          <span style={{ border: `1px solid ${BBG.rule2}`, padding: '2px 6px', color: BBG.ink }}>F1 / ? HELP</span>
        )}
      </div>
    </div>
  );
}
