// Left rail of the contributors view: repo card, facet chips, leaderboard.

import { useMemo } from 'react';
import { AREA_COLOR, BBG } from '../../lib/theme.js';
import { fmtK } from '../../lib/format.js';
import { byCommitsDesc } from '../../lib/contributors.js';
import { Chip, ChipGroup, DrawerToggle, ellipsis, sectionLabel } from '../ui.jsx';

const ROLES = ['maintainer', 'core', 'contributor'];
const AREAS = ['core', 'api', 'ui', 'infra', 'scrape', 'cli', 'ml', 'data', 'db', 'search', 'ci', 'dedup'];
const LANGS = ['TS', 'Rust', 'Python', 'Go', 'React', 'SQL', 'C', 'Bash'];
const LEADERBOARD_SIZE = 5;

export function ContribRail({
  isMobile, open, onToggleOpen, repo, filters, onToggle, filtered, selectedHandle, onSelect,
}) {
  const top = useMemo(() => [...filtered].sort(byCommitsDesc).slice(0, LEADERBOARD_SIZE), [filtered]);
  const activeCount = filters.role.size + filters.area.size + filters.lang.size;
  return (
    <div style={{
      borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}`,
      borderBottom: isMobile ? `1px solid ${BBG.rule2}` : 'none',
      overflow: isMobile ? 'visible' : 'auto',
    }}>
      {isMobile && (
        <DrawerToggle open={open} onToggle={onToggleOpen} label="REPO · FILTERS · TOP" activeCount={activeCount} />
      )}
      {(!isMobile || open) && (
        <>
          <RepoCard repo={repo} />
          <ChipGroup title="ROLE">
            {ROLES.map((r) => (
              <Chip flex key={r} on={filters.role.has(r)} onClick={() => onToggle('role', r)} label={r} />
            ))}
          </ChipGroup>
          <ChipGroup title="AREA">
            {AREAS.map((a) => (
              <Chip flex key={a} on={filters.area.has(a)} onClick={() => onToggle('area', a)} label={a} dot={AREA_COLOR[a]} />
            ))}
          </ChipGroup>
          <ChipGroup title="LANGUAGE">
            {LANGS.map((l) => (
              <Chip flex key={l} on={filters.lang.has(l)} onClick={() => onToggle('lang', l)} label={l.toLowerCase()} />
            ))}
          </ChipGroup>

          <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}` }}>
            <div style={sectionLabel}>TOP BY COMMITS</div>
            {top.map((c, i) => (
              <div key={c.handle} onClick={() => onSelect(c.handle)} style={{
                display: 'grid', gridTemplateColumns: '14px 1fr auto', gap: 6, padding: '2px 0',
                cursor: 'pointer', fontSize: 11,
              }}>
                <span style={{ color: i === 0 ? BBG.acc : BBG.dim }}>{i + 1}</span>
                <span style={{ color: c.handle === selectedHandle ? BBG.acc : BBG.ink, ...ellipsis }}>@{c.handle}</span>
                <span style={{ color: BBG.dim }}>{c.commits}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function RepoCard({ repo }) {
  const langColor = (l) => AREA_COLOR[l.toLowerCase()] || BBG.acc;
  return (
    <div style={{ padding: '14px 14px 12px', borderBottom: `1px solid ${BBG.rule2}` }}>
      <div style={{ color: BBG.acc, fontSize: 10, letterSpacing: 0.7, marginBottom: 2 }}>REPO</div>
      <div style={{ color: BBG.ink, fontSize: 12.5, fontWeight: 600 }}>{repo.name}</div>
      <div style={{ color: BBG.dim, fontSize: 10.5, marginTop: 4, lineHeight: 1.55 }}>{repo.desc}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8 }}>
        <RepoStat label="★" val={fmtK(repo.stars)} />
        <RepoStat label="forks" val={fmtK(repo.forks)} />
        <RepoStat label="open issues" val={repo.issues} />
        <RepoStat label="open PRs" val={repo.prs_open} />
      </div>
      <div style={{ marginTop: 10 }}>
        <div style={{ color: BBG.dim, fontSize: 9.5, letterSpacing: 0.6, marginBottom: 4 }}>LANGUAGES</div>
        <div style={{ display: 'flex', height: 5, background: BBG.panel2 }}>
          {repo.langs.map(([l, share]) => (
            <div key={l} title={`${l} ${share}%`} style={{ width: `${share}%`, background: langColor(l), opacity: 0.85 }} />
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 5, fontSize: 10, color: BBG.dim }}>
          {repo.langs.map(([l, share]) => (
            <span key={l}>
              <span style={{ display: 'inline-block', width: 6, height: 6, background: langColor(l), marginRight: 3 }} />
              {l} {share}%
            </span>
          ))}
        </div>
      </div>
      <div style={{ color: BBG.dim, fontSize: 10, marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
        <span>{repo.license}</span>
        <span>release <span style={{ color: BBG.ink }}>{repo.release}</span> · {repo.released}</span>
      </div>
    </div>
  );
}

function RepoStat({ label, val }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', fontSize: 10.5 }}>
      <span style={{ color: BBG.dim }}>{label}</span>
      <span style={{ color: BBG.ink, fontWeight: 600 }}>{val}</span>
    </div>
  );
}
