// LIVE / STALE / OFFLINE chip for the terminal top bar.
//
// Reads `window.NGJOBS_META.generated_at` (set by data.jsx after fetching
// docs/jobs.json) and re-renders every 30s so the badge transitions from
// LIVE → STALE if the scraper stops updating.
//
// formatLiveStamp comes from live-stamp-format.js (plain JS, also testable
// in Node).

const { useState: useStateLs, useEffect: useEffectLs } = React;

function LiveStamp() {
  // Tick on a 30s timer so age-based state (live → stale) refreshes
  // without depending on user interaction.
  const [, setTick] = useStateLs(0);
  useEffectLs(() => {
    const onJobsReady = () => setTick((t) => t + 1);
    if (window.NGJOBS_READY && typeof window.NGJOBS_READY.then === 'function') {
      window.NGJOBS_READY.then(onJobsReady).catch(onJobsReady);
    }
    const id = setInterval(() => setTick((t) => t + 1), 30 * 1000);
    return () => clearInterval(id);
  }, []);

  const meta = (window.NGJOBS_META || {});
  const stamp = window.formatLiveStamp(meta.generated_at, new Date());

  return (
    <>
      <span><span style={{ color: stamp.dot }}>●</span> {stamp.label}</span>
      <span>{stamp.text}</span>
    </>
  );
}

window.LiveStamp = LiveStamp;
