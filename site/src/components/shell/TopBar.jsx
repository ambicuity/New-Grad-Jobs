import { BBG } from '../../lib/theme.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { usePromiseSettled } from '../../hooks/usePromiseSettled.js';
import { LiveStamp } from './LiveStamp.jsx';
import { SponsoredBy, SponsorLink } from './Sponsor.jsx';

export function TopBar({ tab, setTab, jobsState, contributorsPromise }) {
  const isMobile = useIsMobile();
  // Contributors data may still be loading when the app first paints.
  const contrib = usePromiseSettled(contributorsPromise);
  const devCount = contrib.value ? contrib.value.contributors.length : 0;
  const tabs = [
    { id: 'hiring', label: 'HIRING', sub: jobsState.error ? 'offline' : `${jobsState.jobs.length} open` },
    { id: 'contributors', label: 'CONTRIBUTORS', sub: contrib.settled ? `${devCount} devs` : '… devs' },
  ];
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 14px', borderRight: `1px solid ${BBG.rule2}` }}>
        <span style={{
          background: BBG.acc, color: '#000', padding: '2px 6px',
          fontWeight: 700, fontSize: 11, letterSpacing: 1,
        }}>NGJ</span>
      </div>

      <div style={{ display: 'flex' }} role="tablist">
        {tabs.map((t) => {
          const active = t.id === tab;
          return (
            <button key={t.id} role="tab" aria-selected={active} onClick={() => setTab(t.id)} style={{
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
            }}>
              <span>{t.label}</span>
              <span style={{ color: BBG.dim, fontWeight: 400, fontSize: 10 }}>{t.sub}</span>
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
        {/* The F1 HELP hint is keyboard-only, so it's noise on touch. */}
        {!isMobile && (
          <span style={{ border: `1px solid ${BBG.rule2}`, padding: '2px 6px', color: BBG.ink }}>F1 HELP</span>
        )}
      </div>
    </div>
  );
}
