import { BBG, FONT_STACK } from '../../lib/theme.js';

export function Toast({ toast }) {
  if (!toast) return null;
  return (
    <div role="status" style={{
      position: 'absolute', bottom: 38, right: 16, zIndex: 30,
      background: BBG.panel, border: `1px solid ${toast.color || BBG.rule2}`,
      color: toast.color || BBG.ink, padding: '4px 10px', fontSize: 11, letterSpacing: 0.3,
      fontFamily: FONT_STACK,
    }}>{toast.msg}</div>
  );
}
