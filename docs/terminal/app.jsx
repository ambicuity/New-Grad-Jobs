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
        <SponsoredBy />
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

// Credit for the project's sponsor, Tailr (https://www.tailr.uk). This is the
// inverse of SponsorLink below: Tailr supports the project, so we display its
// mark — the canonical white "T" on an ink rounded square, inlined as SVG so it
// renders crisply in the monochrome terminal with no network request. A faint
// stroke keeps the near-black ink square legible against the #000 top bar.
function SponsoredBy() {
  const [hover, setHover] = useStateApp(false);
  return (
    <a
      href="https://www.tailr.uk"
      target="_blank"
      rel="noopener noreferrer"
      title="Sponsored by Tailr — tailor your résumé to each job posting"
      aria-label="Sponsored by Tailr (opens in a new tab)"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        textDecoration: 'none',
        color: hover ? '#e8e8e8' : '#6e6e6e',
        letterSpacing: 0.5,
        transition: 'color 120ms ease',
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 8 }}>◆</span>
      <span style={{ fontSize: 10 }}>SPONSORED BY</span>
      <svg width="15" height="15" viewBox="0 0 64 64" aria-hidden="true" style={{ display: 'block' }}>
        <rect x="1" y="1" width="62" height="62" rx="15" fill="#1b1b1d"
              stroke="rgba(255,255,255,0.22)" strokeWidth="2" />
        <text x="32" y="47" textAnchor="middle"
              fontFamily="Georgia, 'Times New Roman', serif" fontSize="44" fill="#ffffff">T</text>
      </svg>
      <span style={{ fontWeight: 600, color: hover ? '#ff9d3d' : '#e8e8e8' }}>tailr</span>
    </a>
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
