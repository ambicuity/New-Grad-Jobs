import { BBG } from '../../lib/theme.js';
import { FKey, onActivateKey } from '../ui.jsx';

/** Bottom status line of the hiring view, incl. the SAVED-only toggle. */
export function StatusBar({ isMobile, count, savedCount, savedOnly, onToggleSavedOnly }) {
  const title = savedOnly
    ? 'showing only saved jobs — click to clear'
    : (savedCount ? `show only your ${savedCount} saved job${savedCount === 1 ? '' : 's'}` : 'no saved jobs yet');
  return (
    <div style={{
      borderTop: `1px solid ${BBG.rule2}`, padding: '5px 14px', background: BBG.panel,
      display: 'flex', gap: 18, fontSize: 11, color: BBG.dim,
    }}>
      <span>STATUS: <span style={{ color: BBG.ok }}>OK</span></span>
      <span>QUERY: <span style={{ color: BBG.ink }}>{count}</span></span>
      <span
        role="button"
        tabIndex={0}
        aria-pressed={savedOnly}
        title={title}
        onClick={onToggleSavedOnly}
        onKeyDown={onActivateKey(onToggleSavedOnly)}
        style={{
          cursor: 'pointer',
          padding: '0 4px',
          background: savedOnly ? BBG.acc : 'transparent',
          color: savedOnly ? '#000' : BBG.dim,
          fontWeight: savedOnly ? 700 : 400,
          transition: 'background 120ms ease',
        }}
      >
        SAVED: <span style={{ color: savedOnly ? '#000' : BBG.acc, fontWeight: 700 }}>{savedCount}</span>
      </span>
      {!isMobile && (
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }}>
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
