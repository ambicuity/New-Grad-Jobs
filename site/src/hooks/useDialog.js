import { useEffect, useRef } from 'react';

const FOCUSABLE = [
  'a[href]', 'button:not([disabled])', 'input:not([disabled])', 'select:not([disabled])',
  'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',');

const focusablesIn = (node) => [...node.querySelectorAll(FOCUSABLE)]
  .filter((el) => el.getAttribute('aria-hidden') !== 'true');

/**
 * Modal dialog behaviour for the element in `ref`: moves focus inside on
 * open, traps Tab / Shift+Tab, closes on Esc, and returns focus to whatever
 * had it before the dialog opened.
 * @param {{current: HTMLElement|null}} ref
 * @param {() => void} onClose
 */
export function useDialog(ref, onClose) {
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const opener = document.activeElement;
    (focusablesIn(node)[0] || node).focus();

    const onKey = (e) => {
      if (e.key === 'Escape') {
        // Stop here so the page-level Esc (clear filters) doesn't also fire.
        e.preventDefault();
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab') return;
      const list = focusablesIn(node);
      if (!list.length) { e.preventDefault(); node.focus(); return; }
      const first = list[0];
      const last = list[list.length - 1];
      const active = document.activeElement;
      const outside = !node.contains(active);
      if (e.shiftKey && (active === first || active === node || outside)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || outside)) {
        e.preventDefault();
        first.focus();
      }
    };
    node.addEventListener('keydown', onKey);
    return () => {
      node.removeEventListener('keydown', onKey);
      if (opener && typeof opener.focus === 'function' && document.contains(opener)) {
        opener.focus({ preventScroll: true });
      }
    };
  }, [ref]);
}
