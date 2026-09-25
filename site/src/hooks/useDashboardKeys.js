import { useEffect, useRef } from 'react';
import { BBG } from '../lib/theme.js';
import { nextSortKey, stepSelection } from '../lib/sort.js';
import { isEditableTarget, shouldIgnoreShortcut } from '../lib/keys.js';

const STEP = { ArrowDown: 1, j: 1, ArrowUp: -1, k: -1 };

/**
 * Global keyboard shortcuts for the hiring view:
 *   / focus search · ? or F1 help · Esc blur input / clear filters
 *   j k ↑ ↓ move selection · Home End first/last · s F3 save · a applied
 *   ⏎ open (application on desktop, detail on mobile) · F2 cycle sort
 * Shortcuts stand aside while typing, while a button/link has focus, when a
 * modifier is held, and while `enabled` is false (a dialog is open).
 */
export function useDashboardKeys(opts) {
  // Read the latest props through a ref so the window listener is attached once.
  const ref = useRef(opts);
  useEffect(() => { ref.current = opts; });

  useEffect(() => {
    const onKey = (e) => {
      const o = ref.current;
      if (!o.enabled) return;
      if (e.key === 'Escape') {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (isEditableTarget(e.target)) { e.target.blur(); return; }
        o.clearAll();
        o.flash('filters cleared', BBG.dim);
        return;
      }
      if (shouldIgnoreShortcut(e)) return;
      handleShortcut(e, o);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}

function moveTo(e, o, id) {
  e.preventDefault();
  if (id != null && id !== o.selectedId) o.select(id);
}

function handleShortcut(e, o) {
  const { filtered, selectedId } = o;
  if (e.key === 'F1' || e.key === '?') { e.preventDefault(); o.setHelpOpen(true); return; }
  if (e.key === '/') { e.preventDefault(); o.searchRef.current?.focus(); return; }
  if (STEP[e.key] && filtered.length) {
    const inList = filtered.some((j) => j.id === selectedId);
    moveTo(e, o, inList ? stepSelection(filtered, selectedId, STEP[e.key]) : filtered[0].id);
    return;
  }
  if ((e.key === 'Home' || e.key === 'End') && filtered.length) {
    moveTo(e, o, (e.key === 'Home' ? filtered[0] : filtered[filtered.length - 1]).id);
    return;
  }
  if ((e.key === 's' || e.key === 'F3') && selectedId != null) {
    e.preventDefault();
    o.toggleSave(selectedId);
    o.flash(o.saved.has(selectedId) ? 'removed from saved' : '★ saved', BBG.acc);
    return;
  }
  if (e.key === 'a' && selectedId != null && o.toggleApplied) {
    e.preventDefault();
    o.toggleApplied(selectedId);
    o.flash(o.applied && o.applied.has(selectedId) ? 'unmarked applied' : '✓ marked applied', BBG.acc);
    return;
  }
  if (e.key === 'Enter' && selectedId != null) {
    e.preventDefault();
    o.openSelected();
    return;
  }
  if (e.key === 'F2') {
    e.preventDefault();
    const next = nextSortKey(o.sortKey);
    o.setSortKey(next);
    o.flash(`sort: ${next}`, BBG.acc2);
  }
}
