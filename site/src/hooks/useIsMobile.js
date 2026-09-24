import { useEffect, useMemo, useState } from 'react';

// Shared responsive hook. The terminal views are styled with inline style
// objects, which win specificity over stylesheet rules — so `@media` queries
// can't restyle them. Responsive branching is therefore driven in JS:
// components call `useIsMobile()` and swap their inline styles on the result.
//
// Single source of truth for the breakpoint, tied to the desktop terminal's
// own min-width (1180px): any viewport that can't fit the 3-column terminal
// reflows to a single column, so there is no in-between band that scrolls
// horizontally. Phones AND tablets get the single-column layout. The
// `@media (max-width: 1180px)` rule in index.html mirrors this value.
export const MOBILE_MAX_PX = 1180;
export const MOBILE_QUERY = `(max-width: ${MOBILE_MAX_PX}px)`;

export function useIsMobile() {
  const mql = useMemo(
    () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(MOBILE_QUERY) : null),
    [],
  );
  const [isMobile, setIsMobile] = useState(() => (mql ? mql.matches : false));

  useEffect(() => {
    if (!mql) return undefined;
    const onChange = (e) => setIsMobile(e.matches);
    // Safari < 14 lacks addEventListener on MediaQueryList; fall back to the
    // deprecated addListener so older iOS still gets live breakpoint updates.
    if (mql.addEventListener) {
      mql.addEventListener('change', onChange);
      return () => mql.removeEventListener('change', onChange);
    }
    mql.addListener(onChange);
    return () => mql.removeListener(onChange);
  }, [mql]);

  return isMobile;
}
