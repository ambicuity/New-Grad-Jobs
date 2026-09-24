import { BBG, FONT_STACK } from '../../lib/theme.js';

/**
 * Transient status message. The live region is always mounted (screen
 * readers only announce changes to a region that already exists).
 */
export function Toast({ toast }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={toast ? undefined : 'ngj-sr-only'}
      style={toast ? {
        position: 'absolute', bottom: 38, right: 16, zIndex: 30,
        background: BBG.panel, border: `1px solid ${toast.color || BBG.rule2}`,
        color: toast.color || BBG.ink, padding: '4px 10px', fontSize: 11, letterSpacing: 0.3,
        fontFamily: FONT_STACK,
      } : undefined}
    >{toast ? toast.msg : ''}</div>
  );
}
