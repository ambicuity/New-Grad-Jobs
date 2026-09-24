// Left rail of the contributors view: repo card, facet chips, leaderboard.
// Chip options come from the data (roles / contribution types present).

import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { fmtK } from '../../lib/format.js';
import { byCommitsDesc, langColor } from '../../lib/contributors.js';
import { Chip, ChipGroup, DrawerToggle, ellipsis, sectionLabel } from '../ui.jsx';

const LEADERBOARD_SIZE = 5;

export function ContribRail({
  isMobile, open, onToggleOpen, repo, options, filters, onToggle, filtered, selectedHandle, onSelect,
}) {
  const top = useMemo(
    () => filtered.filter((c) => typeof c.commits === 'number').sort(byCommitsDesc).slice(0, LEADERBOARD_SIZE),
    [filtered],
  );
  const activeCount = filters.role.size + filters.type.size;
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
          {options.roles.length > 0 && (
            <ChipGroup title="ROLE">
              {options.roles.map((r) => (
                <Chip flex key={r} on={filters.role.has(r)} onClick={() => onToggle('role', r)} label={r} />
              ))}
            </ChipGroup>
          )}
          {options.types.length > 0 && (
            <ChipGroup title="CONTRIBUTION">
              {options.types.map((t) => (
                <Chip flex key={t} on={filters.type.has(t)} onClick={() => onToggle('type', t)} label={t} />
              ))}
            </ChipGroup>
          )}

          <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}` }}>
            <div style={sectionLabel}>TOP BY COMMITS</div>
            {top.length === 0 && <div style={{ color: BBG.dim, fontSize: 11 }}>commit counts unavailable</div>}
            {top.map((c, i) => (
              <button key={c.handle} type="button" onClick={() => onSelect(c.handle)} style={{
                display: 'grid', gridTemplateColumns: '14px 1fr auto', gap: 6, padding: '2px 0', width: '100%',
                cursor: 'pointer', fontSize: 11, background: 'transparent', border: 'none', textAlign: 'left',
                fontFamily: 'inherit',
              }}>
                <span style={{ color: i === 0 ? BBG.acc : BBG.dim }}>{i + 1}</span>
                <span style={{ color: c.handle === selectedHandle ? BBG.acc : BBG.ink, ...ellipsis }}>@{c.handle}</span>
                <span style={{ color: BBG.dim }}>{c.commits}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function RepoCard({ repo }) {
  return (
    <div style={{ padding: '14px 14px 12px', borderBottom: `1px solid ${BBG.rule2}` }}>
      <div style={{ color: BBG.acc, fontSize: 10, letterSpacing: 0.7, marginBottom: 2 }}>REPO</div>
      <div style={{ color: BBG.ink, fontSize: 12.5, fontWeight: 600 }}>{repo.name}</div>
      <div style={{ color: BBG.dim, fontSize: 10.5, marginTop: 4, lineHeight: 1.55 }}>{repo.desc}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8 }}>
        <RepoStat label="★" val={fmtK(repo.stars)} />
        <RepoStat label="forks" val={fmtK(repo.forks)} />
        <RepoStat label="open issues" val={fmtK(repo.issues)} />
        <RepoStat label="open PRs" val={fmtK(repo.prs_open)} />
      </div>
      <div style={{ marginTop: 10 }}>
        <div style={{ color: BBG.dim, fontSize: 9.5, letterSpacing: 0.6, marginBottom: 4 }}>LANGUAGES</div>
        {repo.langs.length === 0 ? (
          <div style={{ color: BBG.dim, fontSize: 10 }}>—</div>
        ) : (
          <>
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
          </>
        )}
      </div>
      <div style={{ color: BBG.dim, fontSize: 10, marginTop: 8 }}>{repo.license}</div>
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
