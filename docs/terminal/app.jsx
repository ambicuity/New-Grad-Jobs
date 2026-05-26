// App shell — top bar with tabs, swaps between Hiring and Contributors views.

const { useState: useStateApp, useEffect: useEffectApp } = React;

function NGApp() {
  const [tab, setTab] = useStateApp(() => {
    const h = (window.location.hash || '').replace('#', '');
    return h === 'contributors' ? 'contributors' : 'hiring';
  });

  useEffectApp(() => {
    window.location.hash = tab;
  }, [tab]);

  return (
    <div style={{
      width: '100%', height: '100%', background: '#000', color: '#e8e8e8',
      fontFamily: '"JetBrains Mono", ui-monospace, monospace',
      display: 'grid', gridTemplateRows: 'auto 1fr', overflow: 'hidden',
    }}>
      <TopBar tab={tab} setTab={setTab} />
      <div style={{ minHeight: 0, overflow: 'hidden' }}>
        {tab === 'hiring' ? <DashboardDirection /> : <ContributorsView />}
      </div>
    </div>
  );
}

function TopBar({ tab, setTab }) {
  const TABS = [
    { id: 'hiring',       label: 'HIRING',       sub: `${NGJOBS.length} open` },
    { id: 'contributors', label: 'CONTRIBUTORS', sub: `${NGCONTRIB.length} devs` },
  ];
  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      borderBottom: '1px solid #2a2a2a', background: '#000',
      fontSize: 12, height: 38,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 14px', borderRight: '1px solid #2a2a2a' }}>
        <span style={{
          background: '#ff9d3d', color: '#000', padding: '2px 6px',
          fontWeight: 700, fontSize: 11, letterSpacing: 1,
        }}>NGJ</span>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex' }}>
        {TABS.map(t => {
          const active = t.id === tab;
          return (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              background: active ? '#1a1407' : 'transparent',
              border: 'none',
              borderRight: '1px solid #2a2a2a',
              borderBottom: active ? '2px solid #ff9d3d' : '2px solid transparent',
              color: active ? '#ff9d3d' : '#e8e8e8',
              padding: '0 18px',
              fontFamily: 'inherit', fontSize: 12, fontWeight: active ? 700 : 500,
              cursor: 'pointer', letterSpacing: 0.5,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span>{t.label}</span>
              <span style={{ color: '#6e6e6e', fontWeight: 400, fontSize: 10 }}>{t.sub}</span>
            </button>
          );
        })}
      </div>

      {/* Right meta */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14, padding: '0 14px', fontSize: 11, color: '#6e6e6e' }}>
        <LiveStamp />
        <SponsorLink />
        <span style={{ border: '1px solid #2a2a2a', padding: '2px 6px', color: '#e8e8e8' }}>F1 HELP</span>
      </div>
    </div>
  );
}

function SponsorLink() {
  const [hover, setHover] = useStateApp(false);
  return (
    <a
      href="https://buymeacoffee.com/ritesh.rana"
      target="_blank"
      rel="noopener noreferrer"
      title="Support the maintainer on Buy Me a Coffee"
      aria-label="Sponsor on Buy Me a Coffee (opens in a new tab)"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        border: '1px solid #ff9d3d',
        background: hover ? '#1a1407' : 'transparent',
        padding: '2px 8px',
        color: '#ff9d3d',
        textDecoration: 'none',
        fontWeight: 600, letterSpacing: 0.5,
        transition: 'background 120ms ease',
      }}
    >
      <span aria-hidden="true">☕</span>
      <span>SPONSOR</span>
    </a>
  );
}

window.NGApp = NGApp;
