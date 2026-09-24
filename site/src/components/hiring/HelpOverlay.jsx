import { BBG, FONT_STACK } from '../../lib/theme.js';

const SHORTCUTS = [
  ['/', 'focus search'],
  ['esc', 'clear filters / unfocus'],
  ['↑ ↓ (or j k)', 'navigate jobs'],
  ['⏎', 'open application'],
  ['s / F3', 'save toggle'],
  ['F2', 'cycle sort: posted → deadline → comp → co'],
  ['?', 'show this help'],
];

/** Keyboard-shortcut sheet (toggled with `?`, closed by Esc or a backdrop click). */
export function HelpOverlay({ onClose }) {
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 40,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div role="dialog" aria-label="Keyboard shortcuts" onClick={(e) => e.stopPropagation()} style={{
        background: BBG.bg, border: `1px solid ${BBG.acc}`, padding: 24, minWidth: 420,
        fontFamily: FONT_STACK, color: BBG.ink,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`, paddingBottom: 8, marginBottom: 12 }}>
          <div style={{ color: BBG.acc, letterSpacing: 0.8, fontWeight: 600 }}>KEYBOARD SHORTCUTS</div>
          <div style={{ color: BBG.dim, fontSize: 10 }}>esc to close</div>
        </div>
        {SHORTCUTS.map(([k, v]) => (
          <div key={k} style={{ display: 'grid', gridTemplateColumns: '160px 1fr', padding: '4px 0', fontSize: 12 }}>
            <span style={{ color: BBG.acc }}>{k}</span>
            <span style={{ color: BBG.ink }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
