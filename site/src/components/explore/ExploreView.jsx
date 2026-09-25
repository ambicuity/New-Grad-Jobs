// EXPLORE tab: every posting the scraper saw this run, before any new-grad
// rule, filtered by the viewer's own include / exclude words (same matcher
// as config.yml), tier toggles and a free-text query. Loaded on demand, all
// client-side, shareable through the URL.

import { useCallback, useDeferredValue, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { BBG } from '../../lib/theme.js';
import { PRESETS, TIERS, cleanWords, filterCorpus, sortNewest, tierCounts } from '../../lib/explore.js';
import { useCorpus } from '../../hooks/useCorpus.js';
import { useIsMobile } from '../../hooks/useIsMobile.js';
import { Chip, ChipGroup, MIN_TARGET, ellipsis, sectionLabel } from '../ui.jsx';

const ROW_HEIGHT = 46;
const OVERSCAN = 10;
export const EXPLORE_LIST_ID = 'explore-list';
const GRID = '130px 1fr 160px 90px 84px 64px';
const TIER_COLOR = { curated: BBG.acc, near_miss: BBG.acc2, out: BBG.dim };

const inputStyle = {
  background: BBG.panel2, color: BBG.ink, border: `1px solid ${BBG.rule2}`, fontFamily: 'inherit', fontSize: 12,
  padding: '4px 8px', minHeight: MIN_TARGET, width: '100%', boxSizing: 'border-box',
};

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

/**
 * @param {{view: import('../../lib/url-state.js').ViewState, updateView: Function}} props
 */
export function ExploreView({ view, updateView }) {
  const isMobile = useIsMobile();
  const corpus = useCorpus(true);
  const { explore } = view;
  const patch = useCallback((fn) => updateView((v) => ({ ...v, explore: { ...v.explore, ...fn(v.explore) } })), [updateView]);
  const setInclude = useCallback((include) => patch(() => ({ include })), [patch]);
  const setExclude = useCallback((exclude) => patch(() => ({ exclude })), [patch]);
  const toggleTier = useCallback((key) => patch((x) => {
    const tiers = new Set(x.tiers);
    if (tiers.has(key)) tiers.delete(key); else tiers.add(key);
    return { tiers };
  }), [patch]);
  const applyPreset = useCallback((p) => patch(() => ({ include: [...p.include], exclude: [...p.exclude] })), [patch]);
  const clear = useCallback(() => patch(() => ({ include: [], exclude: [], tiers: new Set(), q: '' })), [patch]);
  const setQuery = useCallback((q) => patch(() => ({ q })), [patch]);

  const deferred = useDeferredValue(explore);
  const sorted = useMemo(() => sortNewest(corpus.rows), [corpus.rows]);
  const filtered = useMemo(() => filterCorpus(sorted, deferred), [sorted, deferred]);
  const counts = useMemo(() => new Map(tierCounts(corpus.rows)), [corpus.rows]);
  const stale = deferred !== explore;

  const scrollRef = useRef(null);
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    getItemKey: (i) => filtered[i].id,
    overscan: OVERSCAN,
  });

  const activePreset = PRESETS.find((p) => p.include.join() === explore.include.join() && p.exclude.join() === explore.exclude.join());

  const rail = (
    <div role="region" aria-label="Explore signals" style={{ borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}`, borderBottom: isMobile ? `1px solid ${BBG.rule2}` : 'none', overflow: 'auto', flexShrink: 0 }}>
      <div style={{ padding: '10px 14px', borderBottom: `1px solid ${BBG.rule}`, color: BBG.dim, fontSize: 11, lineHeight: 1.6 }}>
        Every posting the scraper saw this run, before the new-grad rules. Your words use the same matcher as config.yml
        (whole words, level tokens, years), so a result is explainable. Tier tags show where each row landed on the board.
      </div>
      <WordList id="explore-include" label="INCLUDE · any of" words={explore.include} onChange={setInclude} placeholder="rust, engineer ii, 0-2 years… ⏎" />
      <WordList id="explore-exclude" label="EXCLUDE · none of" words={explore.exclude} onChange={setExclude} placeholder="senior, intern… ⏎" />
      <ChipGroup title="PRESETS">
        {PRESETS.map((p) => <Chip key={p.id} on={activePreset && activePreset.id === p.id} onClick={() => applyPreset(p)} label={p.label} />)}
        <Chip on={false} onClick={clear} label="clear" />
      </ChipGroup>
      <ChipGroup title="TIER">
        {TIERS.map((t) => (
          <Chip key={t.key} on={explore.tiers.has(t.key)} onClick={() => toggleTier(t.key)} label={corpus.status === 'ready' ? `${t.label} (${counts.get(t.key)})` : t.label} />
        ))}
      </ChipGroup>
    </div>
  );

  return (
    <div style={{ height: '100%', display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '260px 1fr', gridTemplateRows: isMobile ? 'auto 1fr' : '1fr', minHeight: 0 }}>
      {rail}
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '6px 14px', borderBottom: `1px solid ${BBG.rule2}`, background: BBG.panel }}>
          <label htmlFor="explore-q" style={{ color: BBG.acc, fontSize: 11, letterSpacing: 0.7 }}>CMD&gt;</label>
          <input id="explore-q" value={explore.q} onChange={(e) => setQuery(e.target.value)} placeholder="search company / title / location" aria-label="Search all postings" style={{ ...inputStyle, flex: 1 }} />
          <span id="explore-result-count" aria-live="polite" style={{ color: BBG.dim, fontSize: 11, whiteSpace: 'nowrap' }}>
            {corpus.status === 'ready' ? `${filtered.length} / ${corpus.rows.length} postings` : corpus.status === 'error' ? 'corpus unavailable' : 'loading corpus…'}
            {corpus.encoding ? ` · ${corpus.encoding}` : ''}
          </span>
        </div>
        {!isMobile && (
          <div aria-hidden="true" style={{ display: 'grid', gridTemplateColumns: GRID, gap: 8, padding: '4px 14px', color: BBG.dim, fontSize: 11, letterSpacing: 0.6, background: BBG.panel2 }}>
            <span>CO</span><span>TITLE</span><span>LOC</span><span>SOURCE</span><span>POSTED</span><span>TIER</span>
          </div>
        )}
        <div ref={scrollRef} id={EXPLORE_LIST_ID} role="list" aria-label={`All postings, ${filtered.length} results`} aria-busy={stale || corpus.status === 'loading' || undefined} style={{ overflow: 'auto', flex: 1, minHeight: 0, opacity: stale ? 0.7 : 1 }}>
          <div style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
            {virtualizer.getVirtualItems().map((vi) => {
              const r = filtered[vi.index];
              const tier = TIERS.find((t) => t.key === r.tier);
              return (
                <div
                  key={vi.key}
                  role="listitem"
                  data-tier={r.tier}
                  style={{
                    position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)`, height: ROW_HEIGHT,
                    display: 'grid', gridTemplateColumns: isMobile ? '1fr' : GRID, gap: 8, padding: '0 14px', alignItems: 'center',
                    borderBottom: `1px solid ${BBG.rule}`, fontSize: 12, boxSizing: 'border-box', overflow: 'hidden',
                  }}
                >
                  {!isMobile && <span style={{ color: BBG.ink, fontWeight: 600, ...ellipsis }}>{r.co}</span>}
                  <span style={{ ...ellipsis, minWidth: 0 }}>
                    {isMobile && <span style={{ color: BBG.ink, fontWeight: 600 }}>{r.co} · </span>}
                    {r.url
                      ? <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ color: BBG.ink }}>{r.title}</a>
                      : <span style={{ color: BBG.ink }}>{r.title}</span>}
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
          {corpus.status === 'ready' && filtered.length === 0 && (
            <div style={{ padding: 24, color: BBG.dim }}>NO MATCHES. Loosen the include words or turn a tier back on.</div>
          )}
          {corpus.status === 'error' && (
            <div role="alert" style={{ padding: 24, color: BBG.warn }}>The corpus could not be loaded{corpus.error ? ` (${corpus.error})` : ''}. It is published by the scraper after each run.</div>
          )}
        </div>
      </div>
    </div>
  );
}
