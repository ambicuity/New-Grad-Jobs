/**
 * New Grad Jobs - Interactive Job Board
 * Fetches jobs from jobs.json and renders them with search, filter, and theme toggle
 */

// ============================================
// State Management
// ============================================
let allJobs = [];
let filteredJobs = [];
let currentFilters = {
    search: '',
    category: 'all',
    tier: 'all',
    location: 'all'
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    jobContainer: document.getElementById('jobs-container'),
    loading: document.getElementById('loading'),
    emptyState: document.getElementById('empty-state'),
    searchInput: document.getElementById('search-input'),
    searchClear: document.getElementById('search-clear'),
    categoryFilters: document.getElementById('category-filters'),
    tierFilters: document.getElementById('tier-filters'),
    locationFilter: document.getElementById('location-filter'),
    jobCount: document.getElementById('job-count'),
    visibleCount: document.getElementById('visible-count'),
    totalCount: document.getElementById('total-count'),
    lastUpdated: document.getElementById('last-updated'),
    themeToggle: document.getElementById('theme-toggle'),
    resetFilters: document.getElementById('reset-filters')
};

// ============================================
// Theme Management
// ============================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');

    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const themeIcon = elements.themeToggle.querySelector('.theme-icon');
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// ============================================
// Data Fetching
// ============================================
async function fetchJobs() {
    // Try multiple paths for different deployment scenarios
    const paths = [
        './jobs.json',                              // Same directory (GitHub Pages /docs)
        '../jobs.json',                             // Parent directory
        '/New-Grad-Jobs/docs/jobs.json',           // GitHub Pages with repo name
        '/New-Grad-Jobs/jobs.json',                // GitHub Pages root
        'jobs.json'                                 // Relative path
    ];

    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                const data = await response.json();
                if (data && data.jobs) {
                    console.log('Loaded jobs from:', path);
                    return data;
                }
            }
        } catch (error) {
            // Continue to next path
            console.log('Failed to load from:', path);
        }
    }

    console.error('Could not load jobs from any path');
    return null;
}

// ============================================
// Rendering
// ============================================
function renderJobs(jobs) {
    if (jobs.length === 0) {
        elements.jobContainer.innerHTML = '';
        elements.emptyState.classList.remove('hidden');
        return;
    }

    elements.emptyState.classList.add('hidden');

    const html = jobs.map((job, index) => {
        const tierEmoji = job.company_tier?.emoji || '';
        const tierLabel = job.company_tier?.label || '';
        const categoryEmoji = job.category?.emoji || '💼';
        const categoryName = job.category?.name || 'Other';

        // Build flags
        let flagsHtml = '';
        if (job.flags?.no_sponsorship) {
            flagsHtml += '<span class="flag" title="No Visa Sponsorship">🛂</span>';
        }
        if (job.flags?.us_citizenship_required) {
            flagsHtml += '<span class="flag" title="US Citizenship Required">🇺🇸</span>';
        }
        if (job.is_closed) {
            flagsHtml += '<span class="flag" title="Position Closed">🔒</span>';
        }

        const applyButtonClass = job.is_closed ? 'apply-btn closed' : 'apply-btn';
        const applyButtonText = job.is_closed ? '🔒 Closed' : 'Apply →';
        const applyLink = job.is_closed
            ? `<span class="${applyButtonClass}">${applyButtonText}</span>`
            : `<a href="${escapeHtml(job.url)}" class="${applyButtonClass}" target="_blank" rel="noopener">${applyButtonText}</a>`;

        return `
            <article class="job-card" style="animation-delay: ${Math.min(index * 0.05, 0.25)}s">
                <div class="job-info">
                    <div class="job-header">
                        <span class="company-name">${tierEmoji ? tierEmoji + ' ' : ''}${escapeHtml(job.company)}</span>
                        ${tierLabel ? `<span class="company-badge">${tierLabel}</span>` : ''}
                        ${flagsHtml ? `<div class="job-flags">${flagsHtml}</div>` : ''}
                    </div>
                    <h3 class="job-title">${escapeHtml(job.title)}</h3>
                    <div class="job-meta">
                        <span>📍 ${escapeHtml(job.location)}</span>
                        <span class="category-badge">${categoryEmoji} ${categoryName}</span>
                    </div>
                </div>
                <div class="job-actions">
                    ${applyLink}
                    <span class="posted-date">${escapeHtml(job.posted_display || 'Unknown')}</span>
                </div>
            </article>
        `;
    }).join('');

    elements.jobContainer.innerHTML = html;
}

function updateCounts() {
    const visibleCount = filteredJobs.length;
    const totalCount = allJobs.length;

    elements.visibleCount.textContent = visibleCount;
    elements.totalCount.textContent = totalCount;

    // Update header job count
    const statNumber = elements.jobCount.querySelector('.stat-number');
    if (statNumber) {
        statNumber.textContent = totalCount;
    }

    // Update hero stat
    const heroCount = document.getElementById('job-count-hero');
    if (heroCount) {
        heroCount.textContent = totalCount;
    }
}

function updateLastUpdated(timestamp) {
    if (!timestamp) return;

    try {
        const date = new Date(timestamp);
        const options = {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        };
        elements.lastUpdated.textContent = date.toLocaleString('en-US', options);
    } catch (e) {
        elements.lastUpdated.textContent = 'Unknown';
    }
}

// ============================================
// Filtering
// ============================================
function applyFilters() {
    const { search, category, tier, location } = currentFilters;
    const searchLower = search.toLowerCase();

    filteredJobs = allJobs.filter(job => {
        // Search filter
        if (searchLower) {
            const searchableText = `${job.company} ${job.title} ${job.location}`.toLowerCase();
            if (!searchableText.includes(searchLower)) {
                return false;
            }
        }

        // Category filter
        if (category !== 'all') {
            if (job.category?.id !== category) {
                return false;
            }
        }

        // Company tier filter
        if (tier !== 'all') {
            if (job.company_tier?.tier !== tier) {
                return false;
            }
        }

        // Location filter
        if (location !== 'all') {
            const jobLocation = job.location.toLowerCase();
            if (location === 'remote') {
                if (!jobLocation.includes('remote')) {
                    return false;
                }
            } else {
                if (!jobLocation.includes(location)) {
                    return false;
                }
            }
        }

        return true;
    });

    renderJobs(filteredJobs);
    updateCounts();
}

function resetFilters() {
    currentFilters = {
        search: '',
        category: 'all',
        tier: 'all',
        location: 'all'
    };

    // Reset UI
    elements.searchInput.value = '';
    elements.searchClear.classList.remove('visible');
    elements.locationFilter.value = 'all';

    // Reset chips
    document.querySelectorAll('#category-filters .chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.filter === 'all');
    });
    document.querySelectorAll('#tier-filters .chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.filter === 'all');
    });

    applyFilters();
}

// ============================================
// Event Handlers
// ============================================
function handleSearch(e) {
    const value = e.target.value;
    currentFilters.search = value;

    // Show/hide clear button
    elements.searchClear.classList.toggle('visible', value.length > 0);

    // Debounce search
    clearTimeout(handleSearch.timeout);
    handleSearch.timeout = setTimeout(applyFilters, 150);
}

function handleChipClick(e) {
    const chip = e.target.closest('.chip');
    if (!chip) return;

    const filterGroup = chip.closest('.filter-chips');
    const filterType = filterGroup.id === 'category-filters' ? 'category' : 'tier';
    const filterValue = chip.dataset.filter;

    // Update active state
    filterGroup.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');

    // Update filter
    currentFilters[filterType] = filterValue;
    applyFilters();
}

function handleLocationChange(e) {
    currentFilters.location = e.target.value;
    applyFilters();
}

// ============================================
// Utilities
// ============================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Initialization
// ============================================
async function init() {
    // Set up theme
    initTheme();

    // Set up event listeners
    elements.themeToggle.addEventListener('click', toggleTheme);
    elements.searchInput.addEventListener('input', handleSearch);
    elements.searchClear.addEventListener('click', () => {
        elements.searchInput.value = '';
        elements.searchClear.classList.remove('visible');
        currentFilters.search = '';
        applyFilters();
    });
    elements.categoryFilters.addEventListener('click', handleChipClick);
    elements.tierFilters.addEventListener('click', handleChipClick);
    elements.locationFilter.addEventListener('change', handleLocationChange);
    elements.resetFilters.addEventListener('click', resetFilters);

    // Fetch and render jobs
    const data = await fetchJobs();

    if (data && data.jobs) {
        allJobs = data.jobs;
        filteredJobs = [...allJobs];

        // Hide loading
        elements.loading.style.display = 'none';

        // Render
        renderJobs(filteredJobs);
        updateCounts();
        updateLastUpdated(data.meta?.generated_at);
    } else {
        // Show error state
        elements.loading.innerHTML = `
            <div class="empty-icon">⚠️</div>
            <h3>Could not load jobs</h3>
            <p>Please try refreshing the page</p>
        `;
    }
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
