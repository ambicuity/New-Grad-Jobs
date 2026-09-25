import { BBG } from '../../lib/theme.js';
import { FKey, MIN_TARGET } from '../ui.jsx';

/**
 * Bottom status line of the hiring view: shown count, SAVED-only toggle, and an
 * RSS link only when the current view maps to its own feed slice (the top bar
 * carries LIVE/STALE and the footer the generic feed, so neither repeats here).
 */
export function StatusBar({ isMobile, count, savedCount, savedOnly, onToggleSavedOnly, feedPath = 'feed.xml' }) {
  const sliced = feedPath !== 'feed.xml';
  const title = savedOnly
    ? 'showing only saved jobs — click to show all'
    : (savedCount ? `show only your ${savedCount} saved job${savedCount === 1 ? '' : 's'}` : 'no saved jobs yet');
  return (
    <div style={{
      borderTop: `1px solid ${BBG.rule2}`, padding: '3px 14px', background: BBG.panel,
      display: 'flex', alignItems: 'center', gap: 18, fontSize: 11, color: BBG.dim,
    }}>
      <span>SHOWN: <span style={{ color: BBG.ink }}>{count}</span></span>
      <button
        type="button"
        aria-pressed={savedOnly}
        title={title}
        onClick={onToggleSavedOnly}
        style={{
          cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontSize: 11,
          padding: '0 6px', minHeight: MIN_TARGET,
          background: savedOnly ? BBG.acc : 'transparent',
          color: savedOnly ? '#000' : BBG.dim,
          fontWeight: savedOnly ? 700 : 400,
          transition: 'background 120ms ease',
        }}
      >
        SAVED: <span style={{ color: savedOnly ? '#000' : BBG.acc, fontWeight: 700 }}>{savedCount}</span>
        <span className="ngj-sr-only">{savedOnly ? ' (showing saved only)' : ' (show saved only)'}</span>
      </button>
      {sliced && (
        <a
          href={`./${feedPath}`}
          title={`RSS feed for this filter (${feedPath})`}
          data-testid="status-feed-link"
          style={{ color: BBG.acc, textDecoration: 'underline', minHeight: MIN_TARGET, display: 'inline-flex', alignItems: 'center' }}
        >
          RSS · this filter
        </a>
      )}
      {!isMobile && (
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }} aria-hidden="true">
          <FKey n="/" l="SEARCH" />
          <FKey n="↑↓" l="NAV" />
          <FKey n="⏎" l="APPLY" />
          <FKey n="S" l="SAVE" />
          <FKey n="F2" l="SORT" />
          <FKey n="ESC" l="CLEAR" />
          <FKey n="?" l="HELP" />
        </span>
      )}
    </div>
  );
}
