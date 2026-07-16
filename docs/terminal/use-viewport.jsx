// Shared responsive hook. The terminal views are styled entirely with inline JS
// style objects, which win specificity over stylesheet rules — so `@media`
// queries can't restyle them. Responsive branching is therefore driven in JS:
// components call `useIsMobile()` and swap their inline styles on the result.
//
// Single source of truth for the breakpoint. Below MOBILE_MAX the layout
// collapses to a single column; at/above it the desktop terminal is unchanged.

const MOBILE_MAX_PX = 760;
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
