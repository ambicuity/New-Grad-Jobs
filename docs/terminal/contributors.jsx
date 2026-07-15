// Contributors view — same Bloomberg-terminal chrome as Hiring.

const { useState: useStateC, useMemo: useMemoC, useEffect: useEffectC, useRef: useRefC } = React;

const CBG = {
  bg:'#000', panel:'#0a0a0a', panel2:'#101010',
  ink:'#e8e8e8', dim:'#6e6e6e', rule:'#1c1c1c', rule2:'#2a2a2a',
  acc:'#ff9d3d', acc2:'#62a3ff', ok:'#5fd28a', hot:'#ff5050', warn:'#e8c443',
};

function ContributorsView() {
  const [q, setQ] = useStateC('');
  const [filters, setFilters] = useStateC({
    role: new Set(),
    area: new Set(),
    lang: new Set(),
  });
  const [sortKey, setSortKey] = useStateC('commits');
  const [sortDir, setSortDir] = useStateC(1);
  const [selectedHandle, setSelectedHandle] = useStateC(NGCONTRIB[0].handle);
  const searchRef = useRefC(null);

  const toggleSet = (key, val) => setFilters(f => {
    const n = new Set(f[key]); n.has(val) ? n.delete(val) : n.add(val);
    return { ...f, [key]: n };
  });

  const filtered = useMemoC(() => {
    let out = NGCONTRIB.filter(c => {
      if (filters.role.size && !filters.role.has(c.role)) return false;
      if (filters.area.size && !c.areas.some(a => filters.area.has(a))) return false;
      if (filters.lang.size && !c.langs.some(l => filters.lang.has(l))) return false;
      if (q) {
        const needle = q.toLowerCase();
        const hay = `${c.handle} ${c.name} ${c.region} ${c.bio} ${c.langs.join(' ')} ${c.areas.join(' ')}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
    const dir = sortDir;
    if (sortKey === 'commits')  out.sort((a,b) => dir*(b.commits - a.commits));
    if (sortKey === 'prs')      out.sort((a,b) => dir*(b.prs - a.prs));
    if (sortKey === 'add')      out.sort((a,b) => dir*(b.add - a.add));
    if (sortKey === 'handle')   out.sort((a,b) => dir*a.handle.localeCompare(b.handle));
    if (sortKey === 'last')     out.sort((a,b) => dir*lastSort(a.last, b.last));
    if (sortKey === 'since')    out.sort((a,b) => dir*a.since.localeCompare(b.since));
    return out;
  }, [filters, q, sortKey, sortDir]);

  useEffectC(() => {
    if (!filtered.find(c => c.handle === selectedHandle) && filtered[0]) setSelectedHandle(filtered[0].handle);
  }, [filtered, selectedHandle]);

  const selected = NGCONTRIB.find(c => c.handle === selectedHandle) || filtered[0];

  const sortClick = (k) => {
    if (sortKey === k) setSortDir(d => -d);
    else { setSortKey(k); setSortDir(1); }
  };

  // ── Stats ──
  const totals = useMemoC(() => {
    const t = { commits:0, prs:0, add:0, del:0 };
    NGCONTRIB.forEach(c => { t.commits+=c.commits; t.prs+=c.prs; t.add+=c.add; t.del+=c.del; });
    return t;
  }, []);

  // Active-this-week = last contains 'h' or '1d'/'2d'
  const activeWeek = NGCONTRIB.filter(c => /h$|^1d|^2d/.test(c.last)).length;

  // Top by commits in filtered set
  const top5 = useMemoC(() => [...filtered].sort((a,b)=>b.commits-a.commits).slice(0,5), [filtered]);

  // Activity sparkline data (mock — 26 weeks)
  const spark = useMemoC(() => {
    const seed = (selected?.handle || 'a').charCodeAt(0);
    return Array.from({length: 26}, (_, i) => {
      const v = (Math.sin(seed + i*0.7) + Math.sin(seed*0.3 + i*1.3) + 2) / 4;
      return Math.max(0.05, v + (i / 40));
    });
  }, [selected]);

  return (
    <div style={{
      width:'100%', minWidth: 1180, height:'100%', minHeight: 640, background: CBG.bg, color: CBG.ink,
      fontFamily:'"JetBrains Mono", ui-monospace, monospace', fontSize: 12, lineHeight: 1.45,
      display:'grid', gridTemplateRows:'1fr auto', overflow:'hidden', position:'relative',
    }}>

      {/* Body */}
      <div style={{ display:'grid', gridTemplateColumns:'220px 1fr 460px', minHeight: 0 }}>

        {/* Left rail: repo card + filters + leaderboard */}
        <div style={{ borderRight: `1px solid ${CBG.rule2}`, overflow:'auto' }}>

          {/* Repo card */}
          <div style={{ padding:'14px 14px 12px', borderBottom: `1px solid ${CBG.rule2}` }}>
            <div style={{ color: CBG.acc, fontSize: 10, letterSpacing: 0.7, marginBottom: 2 }}>REPO</div>
            <div style={{ color: CBG.ink, fontSize: 12.5, fontWeight: 600 }}>{NGREPO.name}</div>
            <div style={{ color: CBG.dim, fontSize: 10.5, marginTop: 4, lineHeight: 1.55 }}>{NGREPO.desc}</div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap: 6, marginTop: 8 }}>
              <RepoStat label="★" val={fmtK(NGREPO.stars)} />
              <RepoStat label="forks" val={fmtK(NGREPO.forks)} />
              <RepoStat label="open issues" val={NGREPO.issues} />
              <RepoStat label="open PRs" val={NGREPO.prs_open} />
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ color: CBG.dim, fontSize: 9.5, letterSpacing: 0.6, marginBottom: 4 }}>LANGUAGES</div>
              <div style={{ display:'flex', height: 5, background: CBG.panel2 }}>
                {NGREPO.langs.map(([l, pct]) => (
                  <div key={l} title={`${l} ${pct}%`} style={{ width: `${pct}%`, background: AREA_COLOR[l.toLowerCase()] || CBG.acc, opacity: 0.85 }} />
                ))}
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap: 6, marginTop: 5, fontSize: 10, color: CBG.dim }}>
                {NGREPO.langs.map(([l, pct]) => (
                  <span key={l}>
                    <span style={{ display:'inline-block', width: 6, height: 6, background: AREA_COLOR[l.toLowerCase()] || CBG.acc, marginRight: 3 }} />
                    {l} {pct}%
                  </span>
                ))}
              </div>
            </div>
            <div style={{ color: CBG.dim, fontSize: 10, marginTop: 8, display:'flex', justifyContent:'space-between' }}>
              <span>{NGREPO.license}</span>
              <span>release <span style={{ color: CBG.ink }}>{NGREPO.release}</span> · {NGREPO.released}</span>
            </div>
          </div>

          <CChipGroup title="ROLE">
            {['maintainer','core','contributor'].map(r => (
              <CChip key={r} on={filters.role.has(r)} onClick={() => toggleSet('role', r)} label={r} />
            ))}
          </CChipGroup>
          <CChipGroup title="AREA">
            {['core','api','ui','infra','scrape','cli','ml','data','db','search','ci','dedup'].map(a => (
              <CChip key={a} on={filters.area.has(a)} onClick={() => toggleSet('area', a)} label={a} dot={AREA_COLOR[a]} />
            ))}
          </CChipGroup>
          <CChipGroup title="LANGUAGE">
            {['TS','Rust','Python','Go','React','SQL','C','Bash'].map(l => (
              <CChip key={l} on={filters.lang.has(l)} onClick={() => toggleSet('lang', l)} label={l.toLowerCase()} />
            ))}
          </CChipGroup>

          {/* Leaderboard */}
          <div style={{ padding:'12px 14px', borderTop: `1px solid ${CBG.rule}` }}>
            <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>TOP BY COMMITS</div>
            {top5.map((c, i) => (
              <div key={c.handle} onClick={() => setSelectedHandle(c.handle)} style={{
                display:'grid', gridTemplateColumns:'14px 1fr auto', gap: 6, padding:'2px 0',
                cursor:'pointer', fontSize: 11,
              }}>
                <span style={{ color: i === 0 ? CBG.acc : CBG.dim }}>{i+1}</span>
                <span style={{ color: c.handle === selectedHandle ? CBG.acc : CBG.ink, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>@{c.handle}</span>
                <span style={{ color: CBG.dim }}>{c.commits}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Center: header strip + table */}
        <div style={{ display:'flex', flexDirection:'column', minHeight: 0, borderRight: `1px solid ${CBG.rule2}` }}>
          {/* Stats strip */}
          <div style={{ display:'flex', gap: 18, padding:'10px 14px', borderBottom: `1px solid ${CBG.rule2}`, alignItems:'center' }}>
            <CStat label="CONTRIBUTORS" value={NGCONTRIB.length} delta={`+3 7d`} deltaC={CBG.ok} />
            <CStat label="COMMITS"      value={fmtK(totals.commits)} delta="+412 7d" deltaC={CBG.ok} />
            <CStat label="PRS MERGED"   value={fmtK(totals.prs)}     delta="+98 7d"  deltaC={CBG.ok} />
            <CStat label="ACTIVE 7D"    value={activeWeek}            delta=""        deltaC={CBG.dim} />
            <CStat label="NET LOC"      value={`+${fmtK(totals.add)} / -${fmtK(totals.del)}`} delta="" deltaC={CBG.dim} />
            <div style={{ marginLeft:'auto', display:'flex', gap: 8, alignItems:'center' }}>
              <span style={{ color: CBG.acc, fontWeight: 700 }}>CMD&gt;</span>
              <input
                ref={searchRef}
                value={q} onChange={e => setQ(e.target.value)}
                placeholder="search @handle / name / area / region"
                style={{
                  background:'transparent', border: `1px solid ${CBG.rule2}`, outline:'none',
                  color: CBG.ink, fontFamily:'inherit', fontSize: 12, padding:'3px 8px',
                  width: 260, letterSpacing: 0.3,
                }}
              />
            </div>
          </div>

          {/* Tabular header */}
          <div style={{
            display:'grid',
            gridTemplateColumns:'32px 130px 1fr 90px 70px 60px 110px 80px 70px',
            gap: 8, padding:'4px 14px', borderBottom: `1px solid ${CBG.rule2}`,
            color: CBG.dim, fontSize: 10, letterSpacing: 0.6, background: CBG.panel2,
          }}>
            <span>#</span>
            <CSortHdr k="handle"  label="@HANDLE" cur={sortKey} dir={sortDir} on={sortClick} />
            <span>NAME / AREAS</span>
            <span>REGION</span>
            <CSortHdr k="commits" label="COMMITS" cur={sortKey} dir={sortDir} on={sortClick} />
            <CSortHdr k="prs"     label="PRS"     cur={sortKey} dir={sortDir} on={sortClick} />
            <CSortHdr k="add"     label="+/-"     cur={sortKey} dir={sortDir} on={sortClick} />
            <CSortHdr k="since"   label="SINCE"   cur={sortKey} dir={sortDir} on={sortClick} />
            <CSortHdr k="last"    label="LAST"    cur={sortKey} dir={sortDir} on={sortClick} />
          </div>

          {/* Rows */}
          <div style={{ overflow:'auto', flex: 1 }}>
            {filtered.map((c, i) => {
              const isSel = c.handle === selectedHandle;
              return (
                <div key={c.handle} onClick={() => setSelectedHandle(c.handle)} style={{
                  display:'grid',
                  gridTemplateColumns:'32px 130px 1fr 90px 70px 60px 110px 80px 70px',
                  gap: 8, padding:'7px 14px',
                  borderBottom: `1px solid ${CBG.rule}`,
                  background: isSel ? '#1a1407' : 'transparent',
                  borderLeft: isSel ? `2px solid ${CBG.acc}` : '2px solid transparent',
                  cursor:'pointer', alignItems:'center',
                }}>
                  <span style={{ color: CBG.dim, fontSize: 11 }}>{String(i+1).padStart(2,'0')}</span>
                  <div style={{ display:'flex', alignItems:'center', gap: 6, minWidth: 0 }}>
                    <Avatar handle={c.handle} size={20} />
                    <span style={{ color: isSel ? CBG.acc : CBG.ink, fontWeight: 600, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
                      @{c.handle}
                    </span>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ color: CBG.ink, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
                      {c.name}
                      <span style={{ color: roleColor(c.role), marginLeft: 8, fontSize: 10, letterSpacing: 0.5 }}>{c.role.toUpperCase()}</span>
                    </div>
                    <div style={{ display:'flex', gap: 4, flexWrap:'nowrap', overflow:'hidden' }}>
                      {c.areas.slice(0, 4).map(a => (
                        <span key={a} style={{ fontSize: 9.5, color: AREA_COLOR[a] || CBG.dim }}>
                          <span style={{ display:'inline-block', width: 5, height: 5, background: AREA_COLOR[a] || CBG.dim, marginRight: 2 }} />
                          {a}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span style={{ color: CBG.dim, fontSize: 11, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{c.region}</span>
                  <span style={{ color: CBG.acc, fontSize: 11.5 }}>{c.commits.toLocaleString()}</span>
                  <span style={{ color: CBG.ink, fontSize: 11.5 }}>{c.prs}</span>
                  <PMBar add={c.add} del={c.del} />
                  <span style={{ color: CBG.dim, fontSize: 11 }}>{c.since}</span>
                  <span style={{ color: /h$|^1d/.test(c.last) ? CBG.ok : CBG.ink, fontSize: 11 }}>{c.last}</span>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div style={{ padding: 24, color: CBG.dim }}>NO MATCHES. clear filters or refine search.</div>
            )}
          </div>
        </div>

        {/* Right: contributor detail */}
        <ContribDetail c={selected} spark={spark} />
      </div>

      {/* Footer */}
      <div style={{
        borderTop: `1px solid ${CBG.rule2}`, padding:'5px 14px', background: CBG.panel,
        display:'flex', gap: 18, fontSize: 11, color: CBG.dim,
      }}>
        <span>STATUS: <span style={{ color: CBG.ok }}>OK</span></span>
        <span>SHOWN: <span style={{ color: CBG.ink }}>{filtered.length}</span> / {NGCONTRIB.length}</span>
        <span>SEL: <span style={{ color: CBG.ink }}>@{selected?.handle || '—'}</span></span>
        <span style={{ marginLeft:'auto', display:'flex', gap: 14 }}>
          <FKeyC n="/"   l="SEARCH" />
          <FKeyC n="F2"  l="SORT" />
          <FKeyC n="ESC" l="CLEAR" />
          <FKeyC n="G"   l="GITHUB \u2197" />
        </span>
      </div>
    </div>
  );
}

// ── Sub-components ──

function ContribDetail({ c, spark }) {
  const recent = useRecentCommits(c && c.handle);
  if (!c) return null;
  const total = c.add + c.del;
  return (
    <div style={{ overflow:'auto', display:'flex', flexDirection:'column' }}>
      {/* Profile */}
      <div style={{ padding:'16px 16px 14px', borderBottom: `1px solid ${CBG.rule2}`, display:'flex', gap: 12 }}>
        <Avatar handle={c.handle} size={56} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ color: CBG.acc, fontSize: 11, letterSpacing: 0.7 }}>@{c.handle} · {c.role.toUpperCase()}</div>
          <div style={{ fontSize: 17, fontWeight: 600, marginTop: 2, color: CBG.ink }}>{c.name}</div>
          <div style={{ color: CBG.dim, fontSize: 11.5, marginTop: 2 }}>{c.region} · since {c.since} · last commit {c.last}</div>
          <div style={{ color: CBG.ink, fontSize: 11.5, marginTop: 6, lineHeight: 1.55 }}>{c.bio}</div>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', borderBottom: `1px solid ${CBG.rule2}` }}>
        <CMetric label="COMMITS"    value={c.commits.toLocaleString()} sub={`#${rankIn('commits', c)}`} color={CBG.acc} />
        <CMetric label="PRS MERGED" value={c.prs.toString()}            sub={`#${rankIn('prs', c)}`}     color={CBG.ink} />
        <CMetric label="NET LOC"    value={`+${fmtK(c.add)} / -${fmtK(c.del)}`} sub={`${((c.add/(total||1))*100).toFixed(0)}% add`} color={CBG.ok} />
      </div>

      {/* Activity sparkline */}
      <div style={{ padding:'14px 16px', borderBottom: `1px solid ${CBG.rule2}` }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom: 6 }}>
          <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7 }}>ACTIVITY · 26W</div>
          <div style={{ color: CBG.dim, fontSize: 10 }}>{Math.round(c.commits / 26)} commits/wk avg</div>
        </div>
        <Sparkline values={spark} />
        <div style={{ display:'flex', justifyContent:'space-between', color: CBG.dim, fontSize: 9.5, marginTop: 3 }}>
          <span>nov '25</span><span>feb '26</span><span>now</span>
        </div>
      </div>

      {/* Languages */}
      <div style={{ padding:'14px 16px', borderBottom: `1px solid ${CBG.rule2}` }}>
        <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>TOP LANGUAGES</div>
        <div style={{ display:'flex', flexWrap:'wrap', gap: 6 }}>
          {c.langs.map(l => (
            <span key={l} style={{ padding:'2px 7px', border:`1px solid ${CBG.rule2}`, color: CBG.ink, fontSize: 11 }}>
              {l.toLowerCase()}
            </span>
          ))}
        </div>
      </div>

      {/* Owns / areas */}
      <div style={{ padding:'14px 16px', borderBottom: `1px solid ${CBG.rule2}` }}>
        <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>CODEOWNERS</div>
        {c.areas.map(a => (
          <div key={a} style={{ display:'flex', justifyContent:'space-between', fontSize: 11.5, padding:'3px 0', borderBottom: `1px dashed ${CBG.rule}` }}>
            <span>
              <span style={{ display:'inline-block', width: 6, height: 6, background: AREA_COLOR[a] || CBG.acc, marginRight: 6 }} />
              <span style={{ color: CBG.ink }}>{a}</span>
              <span style={{ color: CBG.dim, marginLeft: 8 }}>src/{a}/**</span>
            </span>
            <span style={{ color: CBG.dim }}>owner</span>
          </div>
        ))}
      </div>

      {/* Recent commits — live from GitHub for @{c.handle} */}
      <div style={{ padding:'14px 16px', borderBottom: `1px solid ${CBG.rule2}` }}>
        <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>RECENT COMMITS</div>
        {recent.state === 'loading' && (
          <div style={{ color: CBG.dim, fontSize: 11, padding:'3px 0' }}>loading from github…</div>
        )}
        {recent.state === 'empty' && (
          <div style={{ color: CBG.dim, fontSize: 11, padding:'3px 0' }}>no commits authored by @{c.handle} in this repo</div>
        )}
        {recent.state === 'error' && (
          <div style={{ color: CBG.warn, fontSize: 11, padding:'3px 0' }}>could not load commits ({recent.error || 'network'})</div>
        )}
        {recent.state === 'ok' && recent.commits.map((rc, i) => (
          <a key={rc.sha || i} href={rc.url || `https://github.com/${RECENT_COMMITS_REPO}/commit/${rc.sha}`} target="_blank" rel="noopener noreferrer"
             style={{ display:'grid', gridTemplateColumns:'52px 1fr 60px', gap: 8, fontSize: 11, padding:'3px 0', textDecoration:'none' }}>
            <span style={{ color: CBG.acc2 }}>{rc.sha}</span>
            <span style={{ color: CBG.ink, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{rc.msg}</span>
            <span style={{ color: CBG.dim, textAlign:'right' }}>{rc.ago}</span>
          </a>
        ))}
      </div>

      {/* CTA */}
      <div style={{ padding:'14px 16px', display:'flex', gap: 8 }}>
        <button onClick={() => c.profile && window.open(c.profile, '_blank', 'noopener')} style={{
          flex: 1, background: CBG.acc, color:'#000', border:'none', padding: 10,
          fontFamily:'inherit', fontWeight: 700, cursor:'pointer', letterSpacing: 0.5,
        }}>VIEW ON GITHUB ↗</button>
        <button style={{
          background:'transparent', color: CBG.ink, border: `1px solid ${CBG.rule2}`,
          padding:'10px 14px', fontFamily:'inherit', cursor:'pointer',
        }}>SPONSOR</button>
      </div>
    </div>
  );
}

function CStat({ label, value, delta, deltaC }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', minWidth: 56 }}>
      <span style={{ fontSize: 9.5, color: CBG.dim, letterSpacing: 0.8 }}>{label}</span>
      <span style={{ fontSize: 14, color: CBG.ink, fontWeight: 600, lineHeight: 1.15 }}>{value}</span>
      {delta && <span style={{ fontSize: 9.5, color: deltaC || CBG.dim }}>{delta}</span>}
    </div>
  );
}

function CMetric({ label, value, sub, color }) {
  return (
    <div style={{ padding:'10px 14px', borderRight: `1px solid ${CBG.rule}` }}>
      <div style={{ color: CBG.dim, fontSize: 9.5, letterSpacing: 0.7 }}>{label}</div>
      <div style={{ color, fontSize: 16, fontWeight: 600, marginTop: 2 }}>{value}</div>
      <div style={{ color: CBG.dim, fontSize: 10 }}>{sub}</div>
    </div>
  );
}

function CChipGroup({ title, children }) {
  return (
    <div style={{ padding:'10px 14px', borderBottom: `1px solid ${CBG.rule}` }}>
      <div style={{ color: CBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 }}>{title}</div>
      <div style={{ display:'flex', flexWrap:'wrap', gap: 4 }}>{children}</div>
    </div>
  );
}

function CChip({ on, onClick, label, dot }) {
  return (
    <button onClick={onClick} style={{
      background: on ? CBG.acc : 'transparent',
      color: on ? '#000' : CBG.ink,
      border: `1px solid ${on ? CBG.acc : CBG.rule2}`,
      padding:'2px 7px', fontFamily:'inherit', fontSize: 11, cursor:'pointer',
      letterSpacing: 0.2, fontWeight: on ? 600 : 400,
      display:'inline-flex', alignItems:'center', gap: 4,
    }}>
      {dot && !on && <span style={{ display:'inline-block', width: 5, height: 5, background: dot }} />}
      {label}
    </button>
  );
}

function CSortHdr({ k, label, cur, dir, on }) {
  const active = cur === k;
  return (
    <button onClick={() => on(k)} style={{
      background:'transparent', border:'none', cursor:'pointer',
      color: active ? CBG.acc : CBG.dim, fontFamily:'inherit', fontSize: 10, letterSpacing: 0.6,
      padding: 0, textAlign:'left',
    }}>{label}{active ? (dir > 0 ? ' ▲' : ' ▼') : ''}</button>
  );
}

function FKeyC({ n, l }) {
  return <span><span style={{ color: CBG.acc, fontWeight: 700, marginRight: 4 }}>{n}</span>{l}</span>;
}

function RepoStat({ label, val }) {
  return (
    <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', fontSize: 10.5 }}>
      <span style={{ color: CBG.dim }}>{label}</span>
      <span style={{ color: CBG.ink, fontWeight: 600 }}>{val}</span>
    </div>
  );
}

// Pseudo-avatar: 2-letter monogram on a hashed color block
function Avatar({ handle, size = 24 }) {
  const h = Array.from(handle).reduce((a,c) => (a*31 + c.charCodeAt(0)) >>> 0, 0);
  const hue = h % 360;
  const initials = handle.replace(/[^a-z0-9]/gi,'').slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, flexShrink: 0,
      background: `hsl(${hue} 32% 22%)`,
      color: `hsl(${hue} 70% 78%)`,
      display:'flex', alignItems:'center', justifyContent:'center',
      fontSize: size * 0.42, fontWeight: 700, letterSpacing: 0.5,
      border: `1px solid hsl(${hue} 35% 32%)`,
    }}>{initials}</div>
  );
}

function PMBar({ add, del }) {
  const total = add + del || 1;
  const aPct = (add / total) * 100;
  return (
    <div style={{ display:'flex', alignItems:'center', gap: 4 }}>
      <span style={{ display:'inline-flex', height: 6, width: 36, background: CBG.panel2 }}>
        <span style={{ width: `${aPct}%`, background: CBG.ok }} />
        <span style={{ width: `${100-aPct}%`, background: CBG.hot, opacity: 0.7 }} />
      </span>
      <span style={{ fontSize: 10, color: CBG.dim }}>{fmtK(add+del)}</span>
    </div>
  );
}

function Sparkline({ values }) {
  const W = 420, H = 44;
  const max = Math.max(...values);
  const stepX = W / (values.length - 1);
  const pts = values.map((v, i) => `${i*stepX},${H - (v/max)*H}`).join(' ');
  const area = `0,${H} ${pts} ${W},${H}`;
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ display:'block' }}>
      <polygon points={area} fill={CBG.acc} opacity={0.12} />
      <polyline points={pts} fill="none" stroke={CBG.acc} strokeWidth={1.4} />
      {values.map((v, i) => (
        <circle key={i} cx={i*stepX} cy={H - (v/max)*H} r={1.4} fill={CBG.acc} />
      ))}
    </svg>
  );
}

// ── Helpers ──

function fmtK(n) {
  if (n == null) return '—';
  if (n >= 1000) return (n/1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/,'') + 'k';
  return n.toString();
}

function lastSort(a, b) {
  // smaller = more recent
  const score = s => {
    const m = /^(\d+)(h|d)/.exec(s);
    if (!m) return 999;
    return parseInt(m[1]) * (m[2] === 'h' ? 1 : 24);
  };
  return score(a) - score(b);
}

function roleColor(r) {
  if (r === 'maintainer') return CBG.acc;
  if (r === 'core') return CBG.acc2;
  return CBG.dim;
}

function rankIn(key, c) {
  const sorted = [...NGCONTRIB].sort((a,b) => b[key] - a[key]);
  return sorted.findIndex(x => x.handle === c.handle) + 1;
}

// ── Recent commits ── Live GitHub API per-contributor with session-scoped cache.

const RECENT_COMMITS_CACHE = new Map(); // handle -> { state: 'loading'|'ok'|'error'|'empty', commits, error }
const RECENT_COMMITS_LISTENERS = new Map(); // handle -> Set<callback>
const RECENT_COMMITS_REPO = (typeof NGREPO !== 'undefined' && NGREPO.name) ? NGREPO.name : 'ambicuity/New-Grad-Jobs';

function _notifyRecentCommits(handle) {
  const listeners = RECENT_COMMITS_LISTENERS.get(handle);
  if (listeners) listeners.forEach(cb => cb());
}

function _formatAgo(iso) {
  const t = new Date(iso).getTime();
  if (!t) return '—';
  const diffSec = Math.max(0, (Date.now() - t) / 1000);
  if (diffSec < 60) return `${Math.round(diffSec)}s`;
  if (diffSec < 3600) return `${Math.round(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)}h`;
  if (diffSec < 86400 * 7) return `${Math.round(diffSec / 86400)}d`;
  if (diffSec < 86400 * 30) return `${Math.round(diffSec / (86400 * 7))}w`;
  if (diffSec < 86400 * 365) return `${Math.round(diffSec / (86400 * 30))}mo`;
  return `${Math.round(diffSec / (86400 * 365))}y`;
}

async function _fetchRecentCommits(handle) {
  const url = `https://api.github.com/repos/${RECENT_COMMITS_REPO}/commits?author=${encodeURIComponent(handle)}&per_page=4`;
  const resp = await fetch(url, { headers: { 'Accept': 'application/vnd.github+json' } });
  if (!resp.ok) {
    throw new Error(`gh api ${resp.status}`);
  }
  const data = await resp.json();
  return data.map(d => ({
    sha: (d.sha || '').slice(0, 7),
    msg: (d.commit && d.commit.message || '').split('\n')[0].slice(0, 80),
    ago: _formatAgo(d.commit && d.commit.author && d.commit.author.date),
    url: d.html_url || '',
  }));
}

function useRecentCommits(handle) {
  const [, force] = useStateC(0);
  useEffectC(() => {
    if (!handle) return;
    const set = RECENT_COMMITS_LISTENERS.get(handle) || new Set();
    const cb = () => force(n => n + 1);
    set.add(cb);
    RECENT_COMMITS_LISTENERS.set(handle, set);

    if (!RECENT_COMMITS_CACHE.has(handle)) {
      RECENT_COMMITS_CACHE.set(handle, { state: 'loading', commits: [] });
      _fetchRecentCommits(handle).then(commits => {
        RECENT_COMMITS_CACHE.set(handle, {
          state: commits.length ? 'ok' : 'empty',
          commits,
        });
        _notifyRecentCommits(handle);
      }).catch(err => {
        RECENT_COMMITS_CACHE.set(handle, { state: 'error', commits: [], error: String(err.message || err) });
        _notifyRecentCommits(handle);
      });
    }

    return () => {
      const cur = RECENT_COMMITS_LISTENERS.get(handle);
      if (cur) { cur.delete(cb); if (!cur.size) RECENT_COMMITS_LISTENERS.delete(handle); }
    };
  }, [handle]);

  return RECENT_COMMITS_CACHE.get(handle) || { state: 'loading', commits: [] };
}

window.ContributorsView = ContributorsView;
