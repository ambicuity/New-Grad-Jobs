// Direction 2: TERMINAL — Bloomberg-terminal aesthetic, denser tabular layout,
// amber accent, ticker/stats widgets, no ASCII chrome.

const { useState: useState2, useMemo: useMemo2, useEffect: useEffect2, useRef: useRef2 } = React;

const BBG = {
  bg:    '#000000',
  panel: '#0a0a0a',
  panel2:'#101010',
  ink:   '#e8e8e8',
  dim:   '#6e6e6e',
  rule:  '#1c1c1c',
  rule2: '#2a2a2a',
  acc:   '#ff9d3d',  // amber
  acc2:  '#62a3ff',  // cyan-blue, secondary
  ok:    '#5fd28a',
  hot:   '#ff5050',
  warn:  '#e8c443',
};

function DashboardDirection() {
  const [q, setQ] = useState2('');
  const [filters, setFilters] = useState2({
    type: new Set(), rmt: new Set(), visa: null, cohort: new Set(['26']), size: new Set(),
  });
  const [sortKey, setSortKey] = useState2('deadline');
  const [sortDir, setSortDir] = useState2(1);
  const [selectedId, setSelectedId] = useState2(NGJOBS[5].id);
  const [saved, setSaved] = useState2(new Set(['ant-mlr-26','crs-swe-26']));
  const [toast, setToast] = useState2(null);
  const [helpOpen, setHelpOpen] = useState2(false);
  const searchRef = useRef2(null);
  const listScrollRef = useRef2(null);

  const flashToast = (msg, color) => {
    setToast({ msg, color });
    clearTimeout(flashToast._t);
    flashToast._t = setTimeout(() => setToast(null), 1800);
  };

  const toggleSet = (key, val) => setFilters(f => {
    const next = new Set(f[key]);
    next.has(val) ? next.delete(val) : next.add(val);
    return { ...f, [key]: next };
  });
  const setVisa = (val) => setFilters(f => ({ ...f, visa: f.visa === val ? null : val }));

  const filtered = useMemo2(() => {
    let out = NGJOBS.filter(j => {
      if (filters.type.size && !filters.type.has(j.type)) return false;
      if (filters.rmt.size && !filters.rmt.has(j.rmt)) return false;
      if (filters.visa !== null && j.visa !== filters.visa) return false;
      if (filters.cohort.size && !filters.cohort.has(j.cohort)) return false;
      if (filters.size.size && !filters.size.has(j.size)) return false;
      if (q) {
        const needle = q.toLowerCase();
        if (!`${j.co} ${j.role} ${j.loc} ${j.stack.join(' ')}`.toLowerCase().includes(needle)) return false;
      }
      return true;
    });
    const dir = sortDir;
    if (sortKey === 'deadline') out.sort((a,b) => dir*(daysLeft(a.dl) - daysLeft(b.dl)));
    if (sortKey === 'comp')     out.sort((a,b) => dir*(b.comp[1] - a.comp[1]));
    if (sortKey === 'co')       out.sort((a,b) => dir*a.co.localeCompare(b.co));
    if (sortKey === 'posted')   out.sort((a,b) => dir*a.posted.localeCompare(b.posted));
    return out;
  }, [filters, q, sortKey, sortDir]);

  useEffect2(() => {
    if (!filtered.find(j => j.id === selectedId) && filtered[0]) setSelectedId(filtered[0].id);
  }, [filtered, selectedId]);

  const selected = NGJOBS.find(j => j.id === selectedId) || filtered[0];

  const toggleSave = (id) => setSaved(s => {
    const next = new Set(s); next.has(id) ? next.delete(id) : next.add(id); return next;
  });

  const sortClick = (k) => {
    if (sortKey === k) setSortDir(d => -d);
    else { setSortKey(k); setSortDir(1); }
  };

  // Keyboard shortcuts
  useEffect2(() => {
    const onKey = (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      const inInput = tag === 'input' || tag === 'textarea';
      if (e.key === 'Escape') {
        if (helpOpen) { setHelpOpen(false); return; }
        if (inInput) { e.target.blur(); return; }
        // clear filters + search
        setFilters({ type:new Set(), rmt:new Set(), visa:null, cohort:new Set(['26']), size:new Set() });
        setQ('');
        flashToast('filters cleared', BBG.dim);
        return;
      }
      if (inInput) return;
      if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); return; }
      if (e.key === '?') { e.preventDefault(); setHelpOpen(v => !v); return; }
      const idx = filtered.findIndex(j => j.id === selectedId);
      if ((e.key === 'ArrowDown' || e.key === 'j') && idx < filtered.length - 1) {
        e.preventDefault(); setSelectedId(filtered[idx + 1].id);
      } else if ((e.key === 'ArrowUp' || e.key === 'k') && idx > 0) {
        e.preventDefault(); setSelectedId(filtered[idx - 1].id);
      } else if (e.key === 's' || e.key === 'F3') {
        e.preventDefault();
        toggleSave(selectedId);
        flashToast(saved.has(selectedId) ? 'unsaved' : '★ saved', BBG.acc);
      } else if (e.key === 'Enter') {
        const j = NGJOBS.find(x => x.id === selectedId);
        if (j) {
          if (j.url) window.open(j.url, '_blank', 'noopener');
          flashToast(`opening ${j.co.toLowerCase()} ↗`, BBG.acc);
        }
      } else if (e.key === 'F2') {
        e.preventDefault();
        const keys = ['deadline','comp','co','posted'];
        const next = keys[(keys.indexOf(sortKey) + 1) % keys.length];
        setSortKey(next);
        flashToast(`sort: ${next}`, BBG.acc2);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [filtered, selectedId, saved, sortKey, helpOpen]);

  // company-frequency for hot-companies widget
  const coCounts = useMemo2(() => {
    const m = new Map();
    filtered.forEach(j => m.set(j.co, (m.get(j.co) || 0) + 1));
    return [...m.entries()].sort((a,b) => b[1]-a[1]);
  }, [filtered]);

  // Deadline buckets
  const buckets = useMemo2(() => {
    const b = { w1: 0, w2: 0, m1: 0, m3: 0, m3p: 0 };
    filtered.forEach(j => {
      const d = daysLeft(j.dl);
      if (d < 7) b.w1++; else if (d < 14) b.w2++; else if (d < 30) b.m1++; else if (d < 90) b.m3++; else b.m3p++;
    });
    return b;
  }, [filtered]);

  return (
    <div style={{
      width: '100%', minWidth: 1180, height: '100%', minHeight: 640, background: BBG.bg, color: BBG.ink,
      fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontSize: 12, lineHeight: 1.45,
      display: 'grid', gridTemplateRows: 'auto 1fr auto', overflow: 'hidden', position: 'relative',
    }}>
      {/* ─── Stats strip ─── */}
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`, padding: '10px 14px', gap: 18 }}>
        <Stat label="OPEN"      value={NGJOBS.length} delta="+12 24h" deltaC={BBG.ok} />
        <Stat label="NEW TODAY" value={NGJOBS.filter(j => /^\dh|^1d|^2d/.test(j.posted)).length} delta="+5"   deltaC={BBG.ok} />
        <Stat label="CLOSING <7d" value={NGJOBS.filter(j => daysLeft(j.dl) < 7).length} delta="⚠" deltaC={BBG.hot} />
        <Stat label="MED COMP" value="$170k" delta="+2.1%" deltaC={BBG.ok} />
        <Stat label="VISA✓"    value={`${Math.round(100*NGJOBS.filter(j=>j.visa).length/NGJOBS.length)}%`} delta="" deltaC={BBG.dim} />
        <div style={{ marginLeft: 'auto', color: BBG.dim, fontSize: 11 }}>HIRING · live job feed</div>
      </div>

      {/* ─── Body grid ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '210px 1fr 460px', minHeight: 0 }}>
        {/* ─ Left rail: filters as compact chip list ─ */}
        <div style={{ borderRight: `1px solid ${BBG.rule2}`, overflow: 'auto' }}>
          <ChipGroup title="ROLE">
            {['SWE','ML','DATA','FE','BE','INFRA','SEC','MOBILE','HW'].map(t => (
              <Chip key={t} on={filters.type.has(t)} onClick={() => toggleSet('type', t)} label={TYPE_LABEL[t]} />
            ))}
          </ChipGroup>
          <ChipGroup title="REMOTE">
            {['remote','hybrid','onsite'].map(r => (
              <Chip key={r} on={filters.rmt.has(r)} onClick={() => toggleSet('rmt', r)} label={r} />
            ))}
          </ChipGroup>
          <ChipGroup title="VISA">
            <Chip on={filters.visa === true}  onClick={() => setVisa(true)}  label="sponsored" />
            <Chip on={filters.visa === false} onClick={() => setVisa(false)} label="us-only" />
          </ChipGroup>
          <ChipGroup title="COHORT">
            <Chip on={filters.cohort.has('26')} onClick={() => toggleSet('cohort','26')} label="'26" />
            <Chip on={filters.cohort.has('25')} onClick={() => toggleSet('cohort','25')} label="'25" />
          </ChipGroup>
          <ChipGroup title="COMPANY SIZE">
            {['S','M','L','XL'].map(s => (
              <Chip key={s} on={filters.size.has(s)} onClick={() => toggleSet('size', s)} label={SIZE_LABEL[s]} />
            ))}
          </ChipGroup>

          {/* Deadline histogram widget */}
          <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}`, marginTop: 6 }}>
            <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>DEADLINE DIST.</div>
            {[
              ['<7d',   buckets.w1,  BBG.hot],
              ['<14d',  buckets.w2,  BBG.warn],
              ['<1mo',  buckets.m1,  BBG.acc],
              ['<3mo',  buckets.m3,  BBG.ok],
              ['>3mo',  buckets.m3p, BBG.dim],
            ].map(([lbl, n, c]) => (
              <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, marginBottom: 2 }}>
                <span style={{ width: 32, color: BBG.dim }}>{lbl}</span>
                <div style={{ flex: 1, height: 6, background: BBG.panel2, position: 'relative' }}>
                  <div style={{ position: 'absolute', inset: 0, width: `${Math.min(100, (n/(filtered.length||1))*100)}%`, background: c }} />
                </div>
                <span style={{ width: 22, textAlign: 'right' }}>{n}</span>
              </div>
            ))}
          </div>

          {/* Hot companies */}
          <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}` }}>
            <div style={{
              color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6,
              display: 'flex', justifyContent: 'space-between',
            }}>
              <span>HIRING NOW</span>
              <span style={{ color: BBG.acc }}>{coCounts.length}</span>
            </div>
            <div style={{ maxHeight: 220, overflowY: 'auto' }}>
              {coCounts.map(([co, n]) => (
                <div key={co} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, padding: '1px 0' }}>
                  <span style={{ color: BBG.ink }}>{co}</span>
                  <span style={{ color: BBG.acc }}>{n}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ─ Center: search + tabular list ─ */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, borderRight: `1px solid ${BBG.rule2}` }}>
          <div style={{ padding: '8px 14px', borderBottom: `1px solid ${BBG.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: BBG.acc, fontWeight: 700 }}>CMD&gt;</span>
            <input
              ref={searchRef}
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="search co / role / stack / loc · / to focus, esc to clear"
              style={{
                background: 'transparent', border: 'none', outline: 'none',
                color: BBG.ink, fontFamily: 'inherit', fontSize: 12.5, flex: 1, letterSpacing: 0.3,
              }}
            />
            <span style={{ color: BBG.dim, fontSize: 11 }}>
              <span style={{ color: BBG.acc, fontWeight: 700 }}>{filtered.length}</span> / {NGJOBS.length} results
            </span>
          </div>

          {/* Tabular header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '28px 110px 1fr 130px 90px 90px 90px 26px',
            gap: 8, padding: '4px 14px', borderBottom: `1px solid ${BBG.rule2}`,
            color: BBG.dim, fontSize: 10, letterSpacing: 0.6, background: BBG.panel2,
          }}>
            <span>#</span>
            <SortHeader k="co"       label="CO"        cur={sortKey} dir={sortDir} onClick={sortClick} />
            <span>ROLE</span>
            <span>LOC</span>
            <SortHeader k="comp"     label="COMP"      cur={sortKey} dir={sortDir} onClick={sortClick} />
            <SortHeader k="posted"   label="POSTED"    cur={sortKey} dir={sortDir} onClick={sortClick} />
            <SortHeader k="deadline" label="DEADLINE"  cur={sortKey} dir={sortDir} onClick={sortClick} />
            <span></span>
          </div>

          <div style={{ overflow: 'auto', flex: 1 }}>
            {filtered.map((j, i) => {
              const isSel = j.id === selectedId;
              const isSaved = saved.has(j.id);
              const days = daysLeft(j.dl);
              const urgency = Math.min(1, Math.max(0, 1 - days/120));
              return (
                <div key={j.id} onClick={() => setSelectedId(j.id)} style={{
                  display: 'grid',
                  gridTemplateColumns: '28px 110px 1fr 130px 90px 90px 90px 26px',
                  gap: 8, padding: '6px 14px',
                  borderBottom: `1px solid ${BBG.rule}`,
                  background: isSel ? '#1a1407' : 'transparent',
                  borderLeft: isSel ? `2px solid ${BBG.acc}` : '2px solid transparent',
                  cursor: 'pointer', alignItems: 'center',
                }}>
                  <span style={{ color: BBG.dim, fontSize: 11 }}>{String(i+1).padStart(2,'0')}</span>
                  <span style={{ color: isSel ? BBG.acc : BBG.ink, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {j.co}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ color: BBG.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {j.role}
                    </div>
                    <div style={{ color: BBG.dim, fontSize: 10.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {j.stack.slice(0,3).join('/').toLowerCase()}
                      <span style={{ color: BBG.rule2, margin: '0 6px' }}>·</span>
                      <span style={{ color: j.visa ? BBG.ok : BBG.warn }}>{j.visa ? 'visa✓' : 'us'}</span>
                      <span style={{ color: BBG.rule2, margin: '0 6px' }}>·</span>
                      {RMT_LABEL[j.rmt]}
                      <span style={{ color: BBG.rule2, margin: '0 6px' }}>·</span>
                      {SIZE_LABEL[j.size]}
                    </div>
                  </div>
                  <span style={{ color: BBG.ink, fontSize: 11.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{j.loc}</span>
                  <span style={{ color: BBG.acc, fontSize: 11.5 }}>{fmtComp(j.comp)}</span>
                  <span style={{ color: BBG.dim, fontSize: 11 }}>{j.posted}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <UrgencyBar value={urgency} />
                    <span style={{ color: days < 14 ? BBG.hot : BBG.ink, fontSize: 11 }}>
                      {days < 0 ? 'X' : `${days}d`}
                    </span>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); toggleSave(j.id); }} style={{
                    background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                    color: isSaved ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: 14,
                  }}>{isSaved ? '★' : '☆'}</button>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div style={{ padding: 24, color: BBG.dim }}>NO MATCHES. CMD&gt; clear filters with Esc</div>
            )}
          </div>
        </div>

        {/* ─ Right: detail card ─ */}
        <DashboardDetail job={selected} saved={saved.has(selected?.id)} onSave={() => toggleSave(selected.id)} />
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'absolute', bottom: 38, right: 16, zIndex: 30,
          background: BBG.panel, border: `1px solid ${toast.color || BBG.rule2}`,
          color: toast.color || BBG.ink, padding: '4px 10px', fontSize: 11, letterSpacing: 0.3,
          fontFamily: '"JetBrains Mono", monospace',
        }}>{toast.msg}</div>
      )}

      {/* Help overlay */}
      {helpOpen && (
        <div onClick={() => setHelpOpen(false)} style={{
          position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 40,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: BBG.bg, border: `1px solid ${BBG.acc}`, padding: 24, minWidth: 420,
            fontFamily: '"JetBrains Mono", monospace', color: BBG.ink,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`, paddingBottom: 8, marginBottom: 12 }}>
              <div style={{ color: BBG.acc, letterSpacing: 0.8, fontWeight: 600 }}>KEYBOARD SHORTCUTS</div>
              <div style={{ color: BBG.dim, fontSize: 10 }}>esc to close</div>
            </div>
            {[
              ['/',     'focus search'],
              ['esc',   'clear filters / unfocus'],
              ['↑ ↓ (or j k)', 'navigate jobs'],
              ['⏎',     'open application'],
              ['s / F3', 'save toggle'],
              ['F2',    'cycle sort: deadline → comp → co → posted'],
              ['?',     'show this help'],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'grid', gridTemplateColumns: '160px 1fr', padding: '4px 0', fontSize: 12 }}>
                <span style={{ color: BBG.acc }}>{k}</span>
                <span style={{ color: BBG.ink }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Footer status ─── */}
      <div style={{
        borderTop: `1px solid ${BBG.rule2}`, padding: '5px 14px', background: BBG.panel,
        display: 'flex', gap: 18, fontSize: 11, color: BBG.dim,
      }}>
        <span>STATUS: <span style={{ color: BBG.ok }}>OK</span></span>
        <span>QUERY: <span style={{ color: BBG.ink }}>{filtered.length}</span></span>
        <span>SAVED: <span style={{ color: BBG.acc }}>{saved.size}</span></span>
        <span>SEL: <span style={{ color: BBG.ink }}>{selected ? selected.id : '—'}</span></span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }}>
          <FKey n="/"   l="SEARCH" />
          <FKey n="↑↓"  l="NAV" />
          <FKey n="⏎"   l="APPLY" />
          <FKey n="S"   l="SAVE" />
          <FKey n="F2"  l="SORT" />
          <FKey n="ESC" l="CLEAR" />
          <FKey n="?"   l="HELP" />
        </span>
      </div>
    </div>
  );
}

function Stat({ label, value, delta, deltaC }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 56 }}>
      <span style={{ fontSize: 9.5, color: BBG.dim, letterSpacing: 0.8 }}>{label}</span>
      <span style={{ fontSize: 14, color: BBG.ink, fontWeight: 600, lineHeight: 1.15 }}>{value}</span>
      {delta && <span style={{ fontSize: 9.5, color: deltaC || BBG.dim }}>{delta}</span>}
    </div>
  );
}

function ChipGroup({ title, children }) {
  return (
    <div style={{ padding: '10px 14px', borderBottom: `1px solid ${BBG.rule}` }}>
      <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>{title}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{children}</div>
    </div>
  );
}

function Chip({ on, onClick, label }) {
  return (
    <button onClick={onClick} style={{
      background: on ? BBG.acc : 'transparent',
      color: on ? '#000' : BBG.ink,
      border: `1px solid ${on ? BBG.acc : BBG.rule2}`,
      padding: '2px 7px', fontFamily: 'inherit', fontSize: 11, cursor: 'pointer',
      letterSpacing: 0.2, fontWeight: on ? 600 : 400,
    }}>{label}</button>
  );
}

function SortHeader({ k, label, cur, dir, onClick }) {
  const active = cur === k;
  return (
    <button onClick={() => onClick(k)} style={{
      background: 'transparent', border: 'none', cursor: 'pointer',
      color: active ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: 10, letterSpacing: 0.6,
      padding: 0, textAlign: 'left',
    }}>
      {label}{active ? (dir > 0 ? ' ▲' : ' ▼') : ''}
    </button>
  );
}

function FKey({ n, l }) {
  return (
    <span><span style={{ color: BBG.acc, fontWeight: 700, marginRight: 4 }}>{n}</span>{l}</span>
  );
}

function UrgencyBar({ value }) {
  // 5 blocks
  const filled = Math.round(value * 5);
  return (
    <span style={{ display: 'inline-flex', gap: 1 }}>
      {[0,1,2,3,4].map(i => (
        <span key={i} style={{
          width: 4, height: 8, background: i < filled ? (value > 0.7 ? BBG.hot : value > 0.4 ? BBG.warn : BBG.acc) : BBG.rule2,
        }} />
      ))}
    </span>
  );
}

function DashboardDetail({ job, saved, onSave }) {
  if (!job) return null;
  const days = daysLeft(job.dl);
  return (
    <div style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
      {/* Top card */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>
            {job.co.toUpperCase()} · {job.type} · {SIZE_LABEL[job.size]}
          </div>
          <button onClick={onSave} style={{
            background: saved ? BBG.acc : 'transparent', color: saved ? '#000' : BBG.ink,
            border: `1px solid ${saved ? BBG.acc : BBG.rule2}`, padding: '2px 8px',
            fontFamily: 'inherit', fontSize: 11, cursor: 'pointer',
          }}>{saved ? '★ SAVED' : '☆ SAVE'}</button>
        </div>
        <div style={{ fontSize: 17, fontWeight: 600, marginTop: 4, color: BBG.ink, lineHeight: 1.25 }}>{job.role}</div>
        <div style={{ color: BBG.dim, fontSize: 11.5, marginTop: 4 }}>
          {job.co} · {job.loc} · {RMT_LABEL[job.rmt]} · cohort '{job.cohort}
        </div>
      </div>

      {/* Quick metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric label="COMP" value={fmtComp(job.comp)} color={BBG.acc} sub="base + equity" />
        <Metric label="DEADLINE" value={`${days}d`} color={days < 14 ? BBG.hot : BBG.ink} sub={job.dl} />
        <Metric label="VISA" value={job.visa ? 'YES' : 'NO'} color={job.visa ? BBG.ok : BBG.warn} sub={job.visa ? 'sponsored' : 'us-auth req.'} />
      </div>

      {/* Description */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` }}>
        <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>ABOUT THE ROLE</div>
        <div style={{
          color: BBG.ink, lineHeight: 1.55, fontSize: 11.5,
          maxHeight: 160, overflowY: 'auto', paddingRight: 8,
        }}>{job.desc}</div>
      </div>

      {/* Stack */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` }}>
        <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>STACK</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {job.stack.map(s => (
            <span key={s} style={{
              padding: '2px 7px', border: `1px solid ${BBG.rule2}`, color: BBG.ink, fontSize: 11,
            }}>{s.toLowerCase()}</span>
          ))}
          <span style={{ padding: '2px 7px', color: BBG.dim, fontSize: 11 }}>+ {job.level || 'entry'} level</span>
        </div>
      </div>

      {/* Requirements */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` }}>
        <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>REQUIREMENTS</div>
        <ul style={{ margin: 0, paddingLeft: 16, lineHeight: 1.7, color: BBG.ink }}>
          <li>BS / MS in CS or equivalent, graduating by Jun 2027</li>
          <li>Proficiency in <span style={{ color: BBG.acc }}>{job.stack[0].toLowerCase()}</span>; bonus: {job.stack.slice(1).join(', ').toLowerCase() || 'related stacks'}</li>
          <li>Portfolio or open-source — internships not required</li>
          {!job.visa && <li style={{ color: BBG.warn }}>US work authorization (no sponsorship)</li>}
        </ul>
      </div>

      {/* Similar */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` }}>
        <div style={{ color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>SIMILAR ROLES</div>
        {NGJOBS.filter(x => x.type === job.type && x.id !== job.id).slice(0, 3).map(x => (
          <div key={x.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, padding: '2px 0' }}>
            <span style={{ color: BBG.ink }}>{x.co} · <span style={{ color: BBG.dim }}>{x.role}</span></span>
            <span style={{ color: BBG.acc }}>{fmtComp(x.comp)}</span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        <button onClick={() => job.url && window.open(job.url, '_blank', 'noopener')} style={{
          flex: 1, background: BBG.acc, color: '#000', border: 'none',
          padding: '10px', fontFamily: 'inherit', fontWeight: 700, cursor: 'pointer',
          letterSpacing: 0.5,
        }}>APPLY ↗</button>
        <button style={{
          background: 'transparent', color: BBG.ink, border: `1px solid ${BBG.rule2}`,
          padding: '10px 14px', fontFamily: 'inherit', cursor: 'pointer',
        }}>REFER A FRIEND</button>
      </div>
    </div>
  );
}

function Metric({ label, value, sub, color }) {
  return (
    <div style={{ padding: '10px 14px', borderRight: `1px solid ${BBG.rule}` }}>
      <div style={{ color: BBG.dim, fontSize: 9.5, letterSpacing: 0.7 }}>{label}</div>
      <div style={{ color, fontSize: 18, fontWeight: 600, marginTop: 2 }}>{value}</div>
      <div style={{ color: BBG.dim, fontSize: 10 }}>{sub}</div>
    </div>
  );
}

window.DashboardDirection = DashboardDirection;
