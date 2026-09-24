// Bloomberg-terminal palette shared by every view (hiring + contributors).
export const BBG = Object.freeze({
  bg: '#000000',
  panel: '#0a0a0a',
  panel2: '#101010',
  ink: '#e8e8e8',
  // Secondary text. #8a8a8a is 6.1:1 on black (the old #6e6e6e was 4.0:1 and
  // failed WCAG AA); color.test.js guards every background it sits on.
  dim: '#8a8a8a',
  placeholder: '#8a8a8a',
  rule: '#1c1c1c',
  rule2: '#2a2a2a',
  acc: '#ff9d3d', // amber
  acc2: '#62a3ff', // cyan-blue, secondary
  ok: '#5fd28a',
  hot: '#ff5050',
  warn: '#e8c443',
  selBg: '#1a1407', // selected-row / active-tab tint
});

export const FONT_STACK = '"JetBrains Mono", ui-monospace, monospace';

// Palette for contributor areas / repo languages (preserved from the design).
export const AREA_COLOR = Object.freeze({
  core: '#62a3ff', api: '#ff9d3d', ui: '#5fd28a', infra: '#e8c443', scrape: '#c084fc',
  dedup: '#c084fc', cli: '#62a3ff', db: '#ff9d3d', ml: '#ff5a9d', data: '#5fd28a', ci: '#e8c443', search: '#ff9d3d',
});

export const REPO_URL = 'https://github.com/ambicuity/New-Grad-Jobs';
