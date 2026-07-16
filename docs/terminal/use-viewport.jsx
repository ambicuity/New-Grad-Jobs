// Shared responsive hook. The terminal views are styled entirely with inline JS
// style objects, which win specificity over stylesheet rules — so `@media`
// queries can't restyle them. Responsive branching is therefore driven in JS:
// components call `useIsMobile()` and swap their inline styles on the result.
//
// Single source of truth for the breakpoint. Below MOBILE_MAX the layout
// collapses to a single column; at/above it the desktop terminal is unchanged.
//
// The value is tied to the desktop terminal's own min-width (1180px): any
// viewport that can't fit the 3-column terminal reflows to a single column, so
// there is no in-between band that horizontally scrolls. This means phones AND
// tablets (portrait + landscape) get the single-column layout; only ≥1180px
// screens, where the terminal fits, keep the dense desktop view.

const MOBILE_MAX_PX = 1180;
const MOBILE_QUERY = `(max-width: ${MOBILE_MAX_PX}px)`;

function useIsMobile() {
  const mql = React.useMemo(
    () => (typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(MOBILE_QUERY)
      : null),
    [],
  );
  const [isMobile, setIsMobile] = React.useState(() => (mql ? mql.matches : false));

  React.useEffect(() => {
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

window.useIsMobile = useIsMobile;
window.MOBILE_MAX_PX = MOBILE_MAX_PX;
