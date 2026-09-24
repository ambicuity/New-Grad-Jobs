// Canned GitHub REST API responses for the contributors view. Matched in
// order against `pathname + search` of each intercepted api.github.com call.

const REPO = '/repos/ambicuity/New-Grad-Jobs';

export const FIXTURE_STARS = 4242;
/** How the contributors view renders FIXTURE_STARS (fmtK). */
export const FIXTURE_STARS_DISPLAY = '4.2k';

const COMMIT = {
  sha: '0123456789abcdef0123456789abcdef01234567',
  commit: { message: 'test: e2e fixture commit\n\nbody', author: { date: '2026-09-20T12:00:00Z' } },
  html_url: 'https://github.com/ambicuity/New-Grad-Jobs/commit/0123456789abcdef0123456789abcdef01234567',
};

/** @type {Array<[RegExp, unknown]>} */
export const GH_FIXTURES = [
  [/^\/search\/issues\?/, { total_count: 7 }],
  [new RegExp(`^${REPO}/contributors\\?`), [
    { login: 'ambicuity', contributions: 900 },
    { login: 'WarlenSilvaa7', contributions: 12 },
    { login: 'rvac-bucky', contributions: 3 },
  ]],
  [new RegExp(`^${REPO}/languages$`), { Python: 7000, JavaScript: 3000 }],
  [new RegExp(`^${REPO}/commits\\?`), [COMMIT]],
  [new RegExp(`^${REPO}$`), {
    stargazers_count: FIXTURE_STARS, forks_count: 321, open_issues_count: 12, license: { spdx_id: 'MIT' },
  }],
];

/** 1×1 transparent PNG, served for every avatar. */
export const PIXEL_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64',
);
