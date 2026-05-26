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
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden',
    }}>
      <TopBar tab={tab} setTab={setTab} />
      <div style={{ minHeight: 0, overflow: 'hidden' }}>
        {tab === 'hiring' ? <DashboardDirection /> : <ContributorsView />}
      </div>
      <SiteFooter />
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

function SiteFooter() {
  // Bottom-right footer block — adapted from a foorilla-style three-section
  // layout (nav links / socials / version+copyright) to our terminal palette.
  // Right-aligned within a thin row beneath the tab-level status bar so it
  // doesn't overlap the dense main content above.
  const REPO = 'https://github.com/ambicuity/New-Grad-Jobs';
  const links = [
    { href: REPO,                                    label: 'Repo',   ext: true },
    { href: `${REPO}/blob/main/README.md`,           label: 'README', ext: true },
    { href: `${REPO}/issues`,                        label: 'Issues', ext: true },
    { href: 'jobs.json',                             label: 'API',    ext: false, title: 'Public JSON feed of all jobs' },
    { href: 'feed.xml',                              label: 'RSS',    ext: false },
    { href: `${REPO}/actions/workflows/update-jobs.yml`, label: 'Status', ext: true, title: 'Scraper workflow runs' },
  ];
  const socials = [
    { href: 'https://github.com/ambicuity',          label: 'GH', title: 'Ritesh Rana on GitHub' },
    { href: 'https://buymeacoffee.com/ritesh.rana',  label: 'BMC', title: 'Buy Me a Coffee' },
  ];
  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-end',
      borderTop: '1px solid #2a2a2a', background: '#0a0a0a',
      padding: '4px 14px', gap: 14,
      fontSize: 10, color: '#6e6e6e', letterSpacing: 0.3, flexWrap: 'wrap',
    }}>
      <FooterRow items={links} />
      <FooterRow items={socials} />
      <span>
        <span title="Continuously deployed from main">rolling · main</span>
        {' · '}Made with <span aria-hidden="true">♥️</span>
        {' · '}© 2026{' '}
        <a href="https://github.com/ambicuity" target="_blank" rel="noopener noreferrer"
           style={{ color: '#6e6e6e', textDecoration: 'none', borderBottom: '1px dotted #2a2a2a' }}>
          ambicuity
        </a>
      </span>
    </div>
  );
}

function FooterRow({ items }) {
  return (
    <span>
      {items.map((it, i) => (
        <span key={it.label}>
          <a
            href={it.href}
            target={it.ext === false ? undefined : '_blank'}
            rel={it.ext === false ? undefined : 'noopener noreferrer'}
            title={it.title || it.label}
            style={{ color: '#6e6e6e', textDecoration: 'none', borderBottom: '1px dotted #2a2a2a' }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#ff9d3d'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#6e6e6e'; }}
          >
            {it.label}
          </a>
          {i < items.length - 1 ? ' · ' : ''}
        </span>
      ))}
    </span>
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
