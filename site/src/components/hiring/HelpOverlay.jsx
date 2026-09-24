import { useRef } from 'react';
import { BBG, FONT_STACK } from '../../lib/theme.js';
import { useDialog } from '../../hooks/useDialog.js';

const SHORTCUTS = [
  ['/', 'focus search'],
  ['esc', 'leave search / clear filters / close dialogs'],
  ['↑ ↓ (or j k)', 'move through jobs'],
  ['home / end', 'first / last job'],
  ['⏎', 'open application (desktop) · details (mobile)'],
  ['s / F3', 'save / unsave job'],
  ['F2', 'cycle sort: posted → comp → company'],
  ['? / F1', 'show this help'],
];

/** Keyboard-shortcut sheet: a modal dialog (focus trapped, Esc / backdrop / CLOSE dismiss). */
export function HelpOverlay({ onClose }) {
  const ref = useRef(null);
  useDialog(ref, onClose);
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 40,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        style={{
          background: BBG.bg, border: `1px solid ${BBG.acc}`, padding: 24, width: 'min(520px, 100%)',
          fontFamily: FONT_STACK, color: BBG.ink,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`, paddingBottom: 8, marginBottom: 12 }}>
          <h2 id="help-title" style={{ color: BBG.acc, letterSpacing: 0.8, fontWeight: 600, fontSize: 12, margin: 0 }}>KEYBOARD SHORTCUTS</h2>
          <button type="button" onClick={onClose} style={{
            background: 'transparent', border: `1px solid ${BBG.rule2}`, color: BBG.ink,
            fontFamily: 'inherit', fontSize: 11, padding: '2px 8px', minHeight: 24, cursor: 'pointer',
          }}>CLOSE (esc)</button>
        </div>
        <dl style={{ margin: 0 }}>
          {SHORTCUTS.map(([k, v]) => (
            <div key={k} style={{ display: 'grid', gridTemplateColumns: '140px 1fr', padding: '4px 0', fontSize: 12 }}>
              <dt style={{ color: BBG.acc }}>{k}</dt>
              <dd style={{ color: BBG.ink, margin: 0 }}>{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
