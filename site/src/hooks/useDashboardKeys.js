import { useEffect } from 'react';
import { BBG } from '../lib/theme.js';
import { nextSortKey, stepSelection } from '../lib/sort.js';

/**
 * Global keyboard shortcuts for the hiring view:
 *   /  focus search · ? help · Esc close help / blur input / clear filters
 *   j k ↑ ↓ move selection · s F3 save · ⏎ open application · F2 cycle sort
 */
export function useDashboardKeys({
  filtered, selected, selectedId, setSelectedId, saved, toggleSave,
  sortKey, setSortKey, helpOpen, setHelpOpen, clearAll, searchRef, flash,
}) {
  useEffect(() => {
    const onKey = (e) => {
      const tag = ((e.target && e.target.tagName) || '').toLowerCase();
      const inInput = tag === 'input' || tag === 'textarea';
      if (e.key === 'Escape') {
        if (helpOpen) { setHelpOpen(false); return; }
        if (inInput) { e.target.blur(); return; }
        clearAll();
        flash('filters cleared', BBG.dim);
        return;
      }
      if (inInput) return;
      if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); return; }
      if (e.key === '?') { e.preventDefault(); setHelpOpen((v) => !v); return; }
      if (e.key === 'ArrowDown' || e.key === 'j' || e.key === 'ArrowUp' || e.key === 'k') {
        const delta = e.key === 'ArrowDown' || e.key === 'j' ? 1 : -1;
        const next = stepSelection(filtered, selectedId, delta);
        if (next !== selectedId) { e.preventDefault(); setSelectedId(next); }
        return;
      }
      if ((e.key === 's' || e.key === 'F3') && selectedId != null) {
        e.preventDefault();
        toggleSave(selectedId);
        flash(saved.has(selectedId) ? 'unsaved' : '★ saved', BBG.acc);
        return;
      }
      if (e.key === 'Enter' && selected) {
        if (selected.url) window.open(selected.url, '_blank', 'noopener');
        flash(`opening ${selected.co.toLowerCase()} ↗`, BBG.acc);
        return;
      }
      if (e.key === 'F2') {
        e.preventDefault();
        const next = nextSortKey(sortKey);
        setSortKey(next);
        flash(`sort: ${next}`, BBG.acc2);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [filtered, selected, selectedId, setSelectedId, saved, toggleSave, sortKey, setSortKey,
    helpOpen, setHelpOpen, clearAll, searchRef, flash]);
}
