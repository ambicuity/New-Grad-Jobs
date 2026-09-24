import { useCallback, useEffect, useRef, useState } from 'react';

export const TOAST_MS = 1800;

/** Transient status message; a new flash replaces (and re-times) the current one. */
export function useToast(durationMs = TOAST_MS) {
  const [toast, setToast] = useState(null);
  const timer = useRef(null);

  const flash = useCallback((msg, color) => {
    setToast({ msg, color });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), durationMs);
  }, [durationMs]);

  useEffect(() => () => clearTimeout(timer.current), []);

  return [toast, flash];
}
