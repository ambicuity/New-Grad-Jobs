/**
 * contributors.js — Fetches docs/contributors.json and renders the contributor grid.
 *
 * Contribution type → emoji mapping follows the all-contributors specification:
 * https://allcontributors.org/docs/en/emoji-key
 */

const CONTRIBUTION_MAP = {
  code:          { emoji: '💻', label: 'Code' },
  doc:           { emoji: '📖', label: 'Docs' },
  test:          { emoji: '⚠️',  label: 'Tests' },
  design:        { emoji: '🎨', label: 'Design' },
  infra:         { emoji: '🚇', label: 'Infra' },
  ideas:         { emoji: '🤔', label: 'Ideas' },
  bug:           { emoji: '🐛', label: 'Bug Reports' },
  review:        { emoji: '👀', label: 'Code Review' },
  question:      { emoji: '💬', label: 'Answering Questions' },
  translation:   { emoji: '🌍', label: 'Translation' },
  tutorial:      { emoji: '✅', label: 'Tutorials' },
  data:          { emoji: '🔣', label: 'Data' },
  example:       { emoji: '💡', label: 'Examples' },
  maintenance:   { emoji: '🚧', label: 'Maintenance' },
  platform:      { emoji: '📦', label: 'Packaging' },
  security:      { emoji: '🛡️', label: 'Security' },
  tool:          { emoji: '🔧', label: 'Tools' },
  talk:          { emoji: '📢', label: 'Talks' },
  financial:     { emoji: '💵', label: 'Financial' },
  mentoring:     { emoji: '🧑‍🏫', label: 'Mentoring' },
  a11y:          { emoji: '♿️', label: 'Accessibility' },
  eventOrganizing: { emoji: '📋', label: 'Event Organizing' },
  fundingFinding: { emoji: '🔍', label: 'Funding Finding' },
  video:         { emoji: '📹', label: 'Videos' },
  blog:          { emoji: '📝', label: 'Blogging' },
  projectManagement: { emoji: '📆', label: 'Project Management' },
  content:       { emoji: '🖋',  label: 'Content' },
  research:      { emoji: '🔬', label: 'Research' },
  userTesting:   { emoji: '📓', label: 'User Testing' },
};

/**
 * Build a single contributor card DOM element.
 * @param {Object} contributor
 * @param {number} index — used to stagger the animation delay
 * @returns {HTMLElement}
 */
function buildCard(contributor, index) {
  const card = document.createElement('div');
  card.className = 'contributor-card';
  card.style.animationDelay = `${index * 60}ms`;

  // Avatar + link
  const link = document.createElement('a');
  link.href = contributor.profile || `https://github.com/${contributor.login}`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.className = 'contributor-avatar-link';
  link.setAttribute('aria-label', `Visit ${contributor.name}'s profile`);

  const img = document.createElement('img');
  img.src = contributor.avatar_url || `https://avatars.githubusercontent.com/${contributor.login}?s=100`;
  img.alt = `${contributor.name} avatar`;
  img.className = 'contributor-avatar';
  img.loading = 'lazy';
  img.width = 100;
  img.height = 100;
  link.appendChild(img);
  card.appendChild(link);

  // Name
  const nameEl = document.createElement('div');
  nameEl.className = 'contributor-name';
  nameEl.textContent = contributor.name || contributor.login;
  card.appendChild(nameEl);

  // GitHub handle
  const handleEl = document.createElement('a');
  handleEl.href = `https://github.com/${contributor.login}`;
  handleEl.target = '_blank';
  handleEl.rel = 'noopener noreferrer';
  handleEl.className = 'contributor-handle';
  handleEl.textContent = `@${contributor.login}`;
  card.appendChild(handleEl);

  // Contribution badges
  if (Array.isArray(contributor.contributions) && contributor.contributions.length > 0) {
    const badges = document.createElement('div');
    badges.className = 'contributor-badges';
    contributor.contributions.forEach(type => {
      const info = CONTRIBUTION_MAP[type] || { emoji: '🔹', label: type };
      const badge = document.createElement('span');
      badge.className = 'contributor-badge';
      badge.title = info.label;
      badge.setAttribute('aria-label', info.label);
      badge.textContent = `${info.emoji} ${info.label}`;
      badges.appendChild(badge);
    });
    card.appendChild(badges);
  }

  return card;
}

/**
 * Render the contributors grid from fetched data.
 * @param {Object[]} contributors
 */
function renderContributors(contributors) {
  const grid = document.getElementById('contributors-grid');
  const count = document.getElementById('contributor-count');
  const loading = document.getElementById('contributors-loading');
  const errorEl = document.getElementById('contributors-error');

  if (loading) loading.classList.add('hidden');
  if (errorEl) errorEl.classList.add('hidden');

  if (!contributors || contributors.length === 0) {
    if (errorEl) {
      errorEl.textContent = 'No contributors found.';
      errorEl.classList.remove('hidden');
    }
    return;
  }

  if (count) {
    count.textContent = contributors.length;
  }

  contributors.forEach((c, i) => {
    grid.appendChild(buildCard(c, i));
  });
}

/**
 * Entry point — fetches contributors.json and kicks off rendering.
 */
async function loadContributors() {
  const errorEl = document.getElementById('contributors-error');
  try {
    const response = await fetch('contributors.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    renderContributors(data.contributors || []);
  } catch (err) {
    const loading = document.getElementById('contributors-loading');
    if (loading) loading.classList.add('hidden');
    if (errorEl) {
      errorEl.textContent = `Failed to load contributors: ${err.message}`;
      errorEl.classList.remove('hidden');
    }
    console.error('Failed to load contributors.json:', err);
  }
}

// ============================================
// Theme Management
// ============================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');

    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Initialize mobile menu if ui.js loaded
    if (typeof window.initMobileMenu === 'function') {
        window.initMobileMenu();
    }

    loadContributors();
});
