// EXPLORE tab: every posting the scraper saw this run, before any new-grad
// rule, laid out like the HIRING view — a facet rail, a dense list and a
// detail pane — but filtered by the viewer's own include / exclude words
// (same matcher as config.yml), tier, role, source, country and posting age.
// Loaded on demand, all client-side, shareable through the URL, exportable.

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { BBG } from '../../lib/theme.js';
import {
  EMPTY_EXPLORE, EXCLUDE_CHIPS, INCLUDE_CHIPS, POSTED_WINDOWS, PRESETS, TIERS, categoryLabel, chipIsOn, cleanWords, facetCounts,
  filterCorpus, matchedWords, sortNewest, tierInfo, toCsv, toggleChipWords,
} from '../../lib/explore.js';
import { COUNTRY_FACET } from '../../lib/location.js';
import { useCorpus } from '../../hooks/useCorpus.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { Chip, ChipGroup, DrawerToggle, MIN_TARGET, Metric, ellipsis, sectionLabel } from '../ui.jsx';

const ROW_HEIGHT = 46;
const OVERSCAN = 10;
export const EXPLORE_LIST_ID = 'explore-list';
const GRID = '32px 130px 1fr 150px 90px 74px 56px';
const TIER_COLOR = { curated: BBG.acc, near_miss: BBG.acc2, out: BBG.dim };
const MAX_ROLE_CHIPS = 30;
const COUNTRY_LABEL = new Map(COUNTRY_FACET);
const inputStyle = {
  background: BBG.panel2, color: BBG.ink, border: `1px solid ${BBG.rule2}`, fontFamily: 'inherit', fontSize: 12,
  padding: '4px 8px', minHeight: MIN_TARGET, width: '100%', boxSizing: 'border-box',
};
const btnStyle = (primary) => ({
  background: primary ? BBG.acc : 'transparent', color: primary ? '#000' : BBG.ink,
  border: `1px solid ${primary ? BBG.acc : BBG.rule2}`, padding: '2px 8px', minHeight: MIN_TARGET,
  fontFamily: 'inherit', fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap', letterSpacing: 0.4,
});

const activeCount = (x) => x.include.length + x.exclude.length + x.tiers.size + x.roles.size + x.sources.size + x.countries.size + (x.posted ? 1 : 0);

/** Word list editor: chips with a remove button and an input that adds on Enter. */
function WordList({ id, label, words, onChange, placeholder }) {
  const [draft, setDraft] = useState('');
  const add = () => {
    const next = cleanWords([...words, draft]);
    if (next.length !== words.length) onChange(next);
    setDraft('');
  };
  return (
    <div style={{ padding: '10px 14px', borderBottom: `1px solid ${BBG.rule}` }}>
      <label htmlFor={id} style={{ ...sectionLabel, display: 'block' }}>{label}</label>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: words.length ? 6 : 0 }} role="list" aria-label={`${label} words`}>
        {words.map((w) => (
          <span key={w} role="listitem" style={{ display: 'inline-flex', alignItems: 'center', border: `1px solid ${BBG.rule2}`, color: BBG.ink, fontSize: 11 }}>
            <span style={{ padding: '2px 6px' }}>{w}</span>
            <button
              type="button"
              aria-label={`remove ${w}`}
              onClick={() => onChange(words.filter((x) => x !== w))}
              style={{ background: 'transparent', border: 'none', borderLeft: `1px solid ${BBG.rule2}`, color: BBG.dim, cursor: 'pointer', fontFamily: 'inherit', minWidth: MIN_TARGET, minHeight: MIN_TARGET }}
            >×</button>
          </span>
        ))}
      </div>
      <input
        id={id}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
        onBlur={() => { if (draft.trim()) add(); }}
        style={inputStyle}
      />
    </div>
  );
}

/** Trigger a client-side download of the current result set. */
function downloadCsv(rows, stamp) {
  const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ngj-explore-${stamp}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function DetailPane({ row, include, isMobile }) {
  if (!row) {
    return (
      <div style={{ padding: '18px 16px', color: BBG.dim, fontSize: 11.5, lineHeight: 1.6 }}>
        <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7, marginBottom: 6 }}>DETAIL</div>
        No posting selected. Pick a row, or loosen the words and facets.
      </div>
    );
  }
  const tier = tierInfo(row.tier);
  const hits = matchedWords(row.title, include);
  const section = { padding: '14px 16px', borderBottom: `1px solid ${BBG.rule2}` };
  return (
    <section aria-labelledby="explore-detail-title" style={{ overflow: 'auto', minHeight: 0, borderLeft: isMobile ? 'none' : `1px solid ${BBG.rule2}` }} data-testid="explore-detail">
      <div style={section}>
        <div style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>{row.co.toUpperCase()} · {categoryLabel(row.cat)} · <span style={{ color: TIER_COLOR[row.tier] }}>{tier.tag}</span></div>
        <h2 id="explore-detail-title" style={{ fontSize: 17, fontWeight: 600, margin: '4px 0 0', color: BBG.ink, lineHeight: 1.25 }}>{row.title}</h2>
        <div style={{ color: BBG.dim, fontSize: 11.5, marginTop: 4 }}>{row.co} · {row.loc || 'location not stated'} · {row.src}</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', borderBottom: `1px solid ${BBG.rule2}` }}>
        <Metric label="TIER" value={tier.tag.toUpperCase()} size={14} color={TIER_COLOR[row.tier]} sub={tier.label} />
        <Metric label="POSTED" value={row.posted || '—'} size={14} color={BBG.ink} sub={row.posted ? 'employer date' : 'not stated'} />
        <Metric label="COUNTRY" value={row.country || '—'} size={14} color={BBG.ink} sub={row.country ? COUNTRY_LABEL.get(row.country) : 'not recognised'} />
      </div>
      <div style={section}>
        <h3 style={{ ...sectionLabel, margin: '0 0 6px', fontWeight: 400 }}>WHY IT IS HERE</h3>
        <div style={{ color: BBG.ink, fontSize: 11.5, lineHeight: 1.6 }}>{tier.why}.</div>
        {include.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 11.5, color: BBG.ink }}>
            Matched include words:{' '}
            {hits.length ? hits.map((w) => <span key={w} style={{ border: `1px solid ${BBG.acc}`, color: BBG.acc, padding: '0 5px', marginRight: 4 }}>{w}</span>) : <span style={{ color: BBG.dim }}>none (shown because the include list is empty or it matched the query)</span>}
          </div>
        )}
      </div>
      <div style={{ padding: '14px 16px', display: 'flex', gap: 8 }}>
        {row.url
          ? <a href={row.url} target="_blank" rel="noopener noreferrer" style={{ flex: 1, background: BBG.acc, color: '#000', textAlign: 'center', textDecoration: 'none', padding: '10px', fontWeight: 700, letterSpacing: 0.5 }}>OPEN ON EMPLOYER SITE ↗</a>
          : <span style={{ color: BBG.dim, fontSize: 11.5, fontStyle: 'italic', padding: '10px 0' }}>No safe application link in the corpus.</span>}
      </div>
    </section>
  );
}

/**
 * @param {{view: import('../../lib/url-state.js').ViewState, updateView: Function}} props
 */
export function ExploreView({ view, updateView }) {
  const isMobile = useIsMobile();
  const corpus = useCorpus(true);
  const explore = view.explore || EMPTY_EXPLORE();
  const [railOpen, setRailOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const patch = useCallback((fn) => updateView((v) => ({ ...v, explore: { ...EMPTY_EXPLORE(), ...v.explore, ...fn({ ...EMPTY_EXPLORE(), ...v.explore }) } })), [updateView]);
  const setInclude = useCallback((include) => patch(() => ({ include })), [patch]);
  const setExclude = useCallback((exclude) => patch(() => ({ exclude })), [patch]);
  const toggleIn = useCallback((facet, key) => patch((x) => {
    const next = new Set(x[facet]);
    if (next.has(key)) next.delete(key); else next.add(key);
    return { [facet]: next };
  }), [patch]);
  const setPosted = useCallback((days) => patch((x) => ({ posted: x.posted === days ? null : days })), [patch]);
  const applyPreset = useCallback((p) => patch(() => ({ include: [...p.include], exclude: [...p.exclude] })), [patch]);
  const clear = useCallback(() => patch(() => EMPTY_EXPLORE()), [patch]);
  const setQuery = useCallback((q) => patch(() => ({ q })), [patch]);

  const now = useMemo(() => Date.parse(corpus.meta.generated_at || '') || Date.now(), [corpus.meta.generated_at]);
  const deferred = useDeferredValue(explore);
  const sorted = useMemo(() => sortNewest(corpus.rows), [corpus.rows]);
  const filtered = useMemo(() => filterCorpus(sorted, deferred, { now }), [sorted, deferred, now]);
  const stale = deferred !== explore;
  const ready = corpus.status === 'ready';

  // Facet counts computed without that facet, so every chip stays switchable.
  const counts = useMemo(() => ({
    tiers: new Map(facetCounts(sorted, deferred, 'tiers', (r) => r.tier, { now })),
    roles: facetCounts(sorted, deferred, 'roles', (r) => r.cat, { now }).slice(0, MAX_ROLE_CHIPS),
    sources: facetCounts(sorted, deferred, 'sources', (r) => r.src, { now }),
    countries: new Map(facetCounts(sorted, deferred, 'countries', (r) => r.country, { now })),
  }), [sorted, deferred, now]);

  const selected = useMemo(() => filtered.find((r) => r.id === selectedId) || filtered[0] || null, [filtered, selectedId]);
  const scrollRef = useRef(null);
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    getItemKey: (i) => filtered[i].id,
    overscan: OVERSCAN,
  });
  const selectedIndex = selected ? filtered.indexOf(selected) : -1;
  useEffect(() => {
    if (selectedIndex >= 0) virtualizer.scrollToIndex(selectedIndex, { align: 'auto' });
  }, [selectedIndex, virtualizer]);

  const onListKey = (e) => {
    const step = { ArrowDown: 1, j: 1, ArrowUp: -1, k: -1 }[e.key];
    if (step && filtered.length) {
      e.preventDefault();
      const next = Math.min(filtered.length - 1, Math.max(0, (selectedIndex < 0 ? 0 : selectedIndex) + step));
      setSelectedId(filtered[next].id);
    } else if (e.key === 'Enter' && selected && selected.url) {
      e.preventDefault();
      window.open(selected.url, '_blank', 'noopener,noreferrer');
    } else if (e.key === 'Escape') {
      e.preventDefault();
      clear();
    }
  };

  const activePreset = PRESETS.find((p) => p.include.join() === explore.include.join() && p.exclude.join() === explore.exclude.join());
  const countLabel = corpus.status === 'ready'
    ? `${filtered.length} / ${corpus.rows.length} postings`
    : corpus.status === 'error' ? 'corpus unavailable' : 'loading corpus…';

  const rail = (
    <div role="region" aria-label="Explore filters" style={{ borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}`, borderBottom: isMobile ? `1px solid ${BBG.rule2}` : 'none', overflow: 'auto', maxHeight: isMobile && railOpen ? '55vh' : undefined, flexShrink: 0 }}>
      {isMobile && <DrawerToggle open={railOpen} onToggle={() => setRailOpen((o) => !o)} label="SIGNALS & FILTERS" activeCount={activeCount(explore)} />}
      {(!isMobile || railOpen) && (
        <>
          <div style={{ padding: '10px 14px', borderBottom: `1px solid ${BBG.rule}`, color: BBG.dim, fontSize: 11, lineHeight: 1.6 }}>
            Every posting the scraper saw this run, before the new-grad rules. Words use the same matcher as config.yml, so a result is explainable.
          </div>
          <ChipGroup title="SIGNALS · include">
            {INCLUDE_CHIPS.map((c) => <Chip key={c.id} on={chipIsOn(explore.include, c)} onClick={() => setInclude(toggleChipWords(explore.include, c))} label={c.label} />)}
          </ChipGroup>
          <ChipGroup title="SIGNALS · exclude">
            {EXCLUDE_CHIPS.map((c) => <Chip key={c.id} on={chipIsOn(explore.exclude, c)} onClick={() => setExclude(toggleChipWords(explore.exclude, c))} label={c.label} />)}
          </ChipGroup>
          <WordList id="explore-include" label="INCLUDE · any of" words={explore.include} onChange={setInclude} placeholder="rust, engineer ii, 0-2 years… ⏎" />
          <WordList id="explore-exclude" label="EXCLUDE · none of" words={explore.exclude} onChange={setExclude} placeholder="senior, intern… ⏎" />
          <ChipGroup title="PRESETS">
            {PRESETS.map((p) => <Chip key={p.id} on={activePreset && activePreset.id === p.id} onClick={() => applyPreset(p)} label={p.label} />)}
            <Chip on={false} onClick={clear} label="clear all" />
          </ChipGroup>
          <ChipGroup title="TIER">
            {TIERS.map((t) => (
              <Chip key={t.key} on={explore.tiers.has(t.key)} onClick={() => toggleIn('tiers', t.key)} label={ready ? `${t.label} (${counts.tiers.get(t.key) || 0})` : t.label} />
            ))}
          </ChipGroup>
          <ChipGroup title="POSTED">
            {POSTED_WINDOWS.map((w) => <Chip key={w.days} on={explore.posted === w.days} onClick={() => setPosted(w.days)} label={`last ${w.label}`} />)}
          </ChipGroup>
          <ChipGroup title="COUNTRY">
            {COUNTRY_FACET.map(([code, label]) => (
              <Chip key={code} on={explore.countries.has(code)} onClick={() => toggleIn('countries', code)} label={ready ? `${label} (${counts.countries.get(code) || 0})` : label} />
            ))}
          </ChipGroup>
          <ChipGroup title="SOURCE">
            {counts.sources.map(([src, n]) => <Chip key={src} on={explore.sources.has(src)} onClick={() => toggleIn('sources', src)} label={`${src} (${n})`} />)}
          </ChipGroup>
          <ChipGroup title="ROLE">
            {counts.roles.map(([cat, n]) => <Chip key={cat} on={explore.roles.has(cat)} onClick={() => toggleIn('roles', cat)} label={`${categoryLabel(cat)} (${n})`} />)}
          </ChipGroup>
        </>
      )}
    </div>
  );

  const header = (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '6px 14px', borderBottom: `1px solid ${BBG.rule2}`, background: BBG.panel, flexWrap: isMobile ? 'wrap' : 'nowrap' }}>
      <label htmlFor="explore-q" style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>CMD&gt;</label>
      <input id="explore-q" value={explore.q} onChange={(e) => setQuery(e.target.value)} placeholder="search company / title / location" aria-label="Search all postings" style={{ ...inputStyle, flex: 1, minWidth: 160 }} />
      <span id="explore-result-count" aria-live="polite" style={{ color: BBG.dim, fontSize: 11, whiteSpace: 'nowrap' }}>
        {countLabel}{corpus.encoding ? ` · ${corpus.encoding}` : ''}
      </span>
      <button type="button" onClick={() => downloadCsv(filtered, (corpus.meta.generated_at || new Date().toISOString()).slice(0, 10))} disabled={!ready || !filtered.length} aria-label={`Export ${filtered.length} postings as CSV`} style={{ ...btnStyle(false), opacity: ready && filtered.length ? 1 : 0.5 }}>
        ⤓ EXPORT CSV
      </button>
    </div>
  );

  const list = (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {header}
      {!isMobile && (
        <div aria-hidden="true" style={{ display: 'grid', gridTemplateColumns: GRID, gap: 8, padding: '4px 14px', color: BBG.dim, fontSize: 11, letterSpacing: 0.6, background: BBG.panel2 }}>
          <span>#</span><span>CO</span><span>TITLE</span><span>LOC</span><span>SOURCE</span><span>POSTED</span><span>TIER</span>
        </div>
      )}
      <div
        ref={scrollRef}
        id={EXPLORE_LIST_ID}
        role="listbox"
        tabIndex={0}
        aria-label={`All postings, ${filtered.length} results`}
        aria-activedescendant={selected ? `explore-opt-${selected.id}` : undefined}
        aria-busy={stale || corpus.status === 'loading' || undefined}
        onKeyDown={onListKey}
        style={{ overflow: 'auto', flex: 1, minHeight: 0, opacity: stale ? 0.7 : 1, outline: 'none' }}
      >
        <div style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const r = filtered[vi.index];
            const tier = tierInfo(r.tier);
            const isSel = selected && r.id === selected.id;
            return (
              <div
                key={vi.key}
                id={`explore-opt-${r.id}`}
                role="option"
                aria-selected={isSel}
                aria-label={`${r.co}, ${r.title}, ${r.loc || 'location not stated'}, ${r.src}, ${tier.label}`}
                data-tier={r.tier}
                onClick={() => setSelectedId(r.id)}
                style={{
                  position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)`, height: ROW_HEIGHT,
                  display: 'grid', gridTemplateColumns: isMobile ? '1fr' : GRID, gap: 8, padding: '0 14px', alignItems: 'center',
                  borderBottom: `1px solid ${BBG.rule}`, borderLeft: isSel ? `2px solid ${BBG.acc}` : '2px solid transparent',
                  background: isSel ? BBG.selBg : 'transparent', fontSize: 12, boxSizing: 'border-box', overflow: 'hidden', cursor: 'pointer',
                }}
              >
                {!isMobile && <span style={{ color: BBG.dim, fontSize: 11 }}>{String(vi.index + 1).padStart(2, '0')}</span>}
                {!isMobile && <span style={{ color: isSel ? BBG.acc : BBG.ink, fontWeight: 600, ...ellipsis }}>{r.co}</span>}
                <span style={{ ...ellipsis, minWidth: 0, color: BBG.ink }}>
                  {isMobile && <span style={{ fontWeight: 600 }}>{r.co} · </span>}
                  {r.title}
                  {isMobile && <span style={{ color: BBG.dim }}> · {r.loc} · <span style={{ color: TIER_COLOR[r.tier] }}>{tier.tag}</span></span>}
                </span>
                {!isMobile && <span style={{ color: BBG.ink, fontSize: 11.5, ...ellipsis }}>{r.loc}</span>}
                {!isMobile && <span style={{ color: BBG.dim, fontSize: 11, ...ellipsis }}>{r.src}</span>}
                {!isMobile && <span style={{ color: BBG.dim, fontSize: 11 }}>{r.posted || '—'}</span>}
                {!isMobile && <span style={{ color: TIER_COLOR[r.tier], fontSize: 11 }} title={tier.why}>{tier.tag}</span>}
              </div>
            );
          })}
        </div>
        {ready && filtered.length === 0 && (
          <div role="option" aria-selected={false} aria-disabled style={{ padding: 24, color: BBG.dim }}>NO MATCHES. Loosen the words or turn a facet back on.</div>
        )}
        {corpus.status === 'error' && (
          <div role="alert" style={{ padding: 24, color: BBG.warn }}>The corpus could not be loaded{corpus.error ? ` (${corpus.error})` : ''}. It is published by the scraper after each run.</div>
        )}
      </div>
      <div style={{ borderTop: `1px solid ${BBG.rule2}`, padding: '3px 14px', background: BBG.panel, display: 'flex', gap: 18, fontSize: 11, color: BBG.dim, alignItems: 'center' }}>
        <span>SHOWN: <span style={{ color: BBG.ink }}>{filtered.length}</span></span>
        {ready && <span>TIERS: {TIERS.map((t) => `${t.tag} ${counts.tiers.get(t.key) || 0}`).join(' · ')}</span>}
        {!isMobile && <span style={{ marginLeft: 'auto' }} aria-hidden="true">↑↓ NAV · ⏎ OPEN · ESC CLEAR</span>}
      </div>
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '260px 1fr 420px', gridTemplateRows: isMobile ? 'auto 1fr auto' : '1fr', minHeight: 0 }}>
      {rail}
      {list}
      <DetailPane row={selected} include={explore.include} isMobile={isMobile} />
    </div>
  );
}
