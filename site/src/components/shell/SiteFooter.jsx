import { BBG, REPO_URL } from '../../lib/theme.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';

const LINKS = [
  { href: REPO_URL, label: 'Repo', ext: true },
  { href: `${REPO_URL}/blob/main/README.md`, label: 'README', ext: true },
  { href: `${REPO_URL}/issues`, label: 'Issues', ext: true },
  { href: './jobs.json', label: 'API', ext: false, title: 'Public JSON feed of all jobs' },
  { href: './feed.xml', label: 'RSS', ext: false },
  { href: `${REPO_URL}/actions/workflows/update-jobs.yml`, label: 'Status', ext: true, title: 'Scraper workflow runs' },
];
const SOCIALS = [
  { href: 'https://github.com/ambicuity', label: 'GH', title: 'Ritesh Rana on GitHub' },
  { href: 'https://buymeacoffee.com/ritesh.rana', label: 'BMC', title: 'Buy Me a Coffee' },
];
// 24px line box: WCAG 2.2 minimum target size (2.5.8) for the footer links.
const linkStyle = { color: BBG.dim, textDecoration: 'none', borderBottom: `1px dotted ${BBG.rule2}`, display: 'inline-block', lineHeight: '22px', minHeight: 24, minWidth: 24, textAlign: 'center' };

// Bottom-right footer: nav links / socials / version+copyright, right-aligned
// in a thin row beneath the tab-level status bar.
export function SiteFooter() {
  const isMobile = useIsMobile();
  return (
    <div style={{
      display: 'flex', justifyContent: isMobile ? 'center' : 'flex-end',
      borderTop: `1px solid ${BBG.rule2}`, background: BBG.panel,
      padding: isMobile ? '2px 10px' : '0 14px', gap: isMobile ? 10 : 14,
      fontSize: 11, color: BBG.dim, letterSpacing: 0.3, flexWrap: 'wrap', alignItems: 'center',
    }}>
      <FooterRow items={LINKS} />
      <FooterRow items={SOCIALS} />
      <span>
        <span title="Continuously deployed from main">rolling · main</span>
        {' · '}Made with <span aria-hidden="true">♥️</span>
        {' · '}© 2026{' '}
        <a href="https://github.com/ambicuity" target="_blank" rel="noopener noreferrer" style={linkStyle}>
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
            style={linkStyle}
            onMouseEnter={(e) => { e.currentTarget.style.color = BBG.acc; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = BBG.dim; }}
          >
            {it.label}
          </a>
          {i < items.length - 1 ? ' · ' : ''}
        </span>
      ))}
    </span>
  );
}
