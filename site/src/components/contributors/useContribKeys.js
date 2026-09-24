import { useEffect } from 'react';

/** Handle `delta` rows away from `handle` in `list`, clamped to the ends. */
export function stepHandle(list, handle, delta) {
  const idx = list.findIndex((c) => c.handle === handle);
  if (idx === -1) return list[0] ? list[0].handle : handle;
  const next = Math.min(list.length - 1, Math.max(0, idx + delta));
  return list[next].handle;
}

/**
 * Keyboard shortcuts for the contributors view (the ones its footer lists):
 *   /  focus search · Esc blur search / clear filters · j k ↑ ↓ move selection
 *   F2 toggle sort (commits ↔ handle) · g open the selected profile on GitHub
 */
export function useContribKeys({ enabled, filtered, selected, setSelectedHandle, searchRef, clearAll, toggleSort }) {
  useEffect(() => {
    if (!enabled) return undefined;
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = ((e.target && e.target.tagName) || '').toLowerCase();
      const inInput = tag === 'input' || tag === 'textarea';
      if (e.key === 'Escape') {
        if (inInput) e.target.blur();
        else clearAll();
        return;
      }
      if (inInput) return;
      if (e.key === '/') {
        e.preventDefault();
        if (searchRef.current) searchRef.current.focus();
      } else if (e.key === 'j' || e.key === 'ArrowDown' || e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        const delta = e.key === 'j' || e.key === 'ArrowDown' ? 1 : -1;
        setSelectedHandle(stepHandle(filtered, selected && selected.handle, delta));
      } else if (e.key === 'F2') {
        e.preventDefault();
        toggleSort();
      } else if ((e.key === 'g' || e.key === 'G') && selected && selected.profile) {
        window.open(selected.profile, '_blank', 'noopener');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, filtered, selected, setSelectedHandle, searchRef, clearAll, toggleSort]);
}
