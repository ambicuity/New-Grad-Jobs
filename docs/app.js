/**
 * New Grad Jobs - Interactive Job Board
 * Fetches jobs from jobs.json and renders them with search and filter
 * Features: Theme toggle, bookmarks, copy link, back to top
 */

// ============================================
// State Management
// ============================================
let allJobs = [];
let filteredJobs = [];
let bookmarkedJobs = new Set(JSON.parse(localStorage.getItem('bookmarkedJobs') || '[]'));
let currentFilters = {
    search: '',
    category: 'all',
    tier: 'all',
    location: 'all'
};

// Pagination state
let currentPage = 1;
const JOBS_PER_PAGE = 25;

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
    resetFilters: document.getElementById('reset-filters'),
    themeToggle: document.getElementById('theme-toggle'),
    backToTop: document.getElementById('back-to-top'),
    toast: document.getElementById('toast')
};

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

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'default') {
    if (!elements.toast) return;

    elements.toast.textContent = message;
    elements.toast.className = `toast visible ${type}`;

    setTimeout(() => {
        elements.toast.classList.remove('visible');
    }, 2500);
}

// ============================================
// Back to Top
// ============================================
function handleScroll() {
    if (!elements.backToTop) return;

    if (window.scrollY > 500) {
        elements.backToTop.classList.add('visible');
    } else {
        elements.backToTop.classList.remove('visible');
    }
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// Bookmark Management
// ============================================
function toggleBookmark(jobUrl) {
    if (bookmarkedJobs.has(jobUrl)) {
        bookmarkedJobs.delete(jobUrl);
        showToast('Bookmark removed', 'default');
    } else {
        bookmarkedJobs.add(jobUrl);
        showToast('Job bookmarked! ⭐', 'success');
    }

    localStorage.setItem('bookmarkedJobs', JSON.stringify([...bookmarkedJobs]));

    // Update UI
    const btn = document.querySelector(`[data-bookmark-url="${CSS.escape(jobUrl)}"]`);
    if (btn) {
        btn.classList.toggle('bookmarked', bookmarkedJobs.has(jobUrl));
        btn.innerHTML = bookmarkedJobs.has(jobUrl) ? '★' : '☆';
    }
}

function copyJobLink(jobUrl, jobTitle) {
    navigator.clipboard.writeText(jobUrl).then(() => {
        showToast('Link copied! 📋', 'success');
    }).catch(() => {
        showToast('Failed to copy link', 'default');
    });
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
        renderPagination(0, 0);
        return;
    }

    elements.emptyState.classList.add('hidden');

    // Pagination calculations
    const totalPages = Math.ceil(jobs.length / JOBS_PER_PAGE);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIndex = (currentPage - 1) * JOBS_PER_PAGE;
    const endIndex = Math.min(startIndex + JOBS_PER_PAGE, jobs.length);
    const pageJobs = jobs.slice(startIndex, endIndex);

    const html = pageJobs.map((job, index) => {
        const tierEmoji = job.company_tier?.emoji || '';
        const tierLabel = job.company_tier?.label || '';
        const categoryEmoji = job.category?.emoji || '💼';
        const categoryName = job.category?.name || 'Other';
        const isBookmarked = bookmarkedJobs.has(job.url);

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

        // Staggered animation delay (cap at 0.5s for performance)
        const animationDelay = Math.min(index * 0.03, 0.5);

        return `
            <article class="job-card" style="--animation-delay: ${animationDelay}s">
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
                    <div class="job-action-buttons">
                        <button 
                            class="action-icon${isBookmarked ? ' bookmarked' : ''}" 
                            data-bookmark-url="${escapeHtml(job.url)}"
                            onclick="toggleBookmark('${escapeHtml(job.url)}')"
                            aria-label="${isBookmarked ? 'Remove bookmark' : 'Bookmark job'}"
                            title="${isBookmarked ? 'Remove bookmark' : 'Bookmark job'}"
                        >${isBookmarked ? '★' : '☆'}</button>
                        <button 
                            class="action-icon" 
                            onclick="copyJobLink('${escapeHtml(job.url)}', '${escapeHtml(job.title)}')"
                            aria-label="Copy job link"
                            title="Copy link"
                        >🔗</button>
                        ${applyLink}
                    </div>
                    <span class="posted-date">${escapeHtml(job.posted_display || 'Unknown')}</span>
                </div>
            </article>
        `;
    }).join('');

    elements.jobContainer.innerHTML = html;
    renderPagination(totalPages, jobs.length);
}

// ============================================
// Pagination Controls
// ============================================
function renderPagination(totalPages, totalJobs) {
    // Remove existing pagination
    const existingPagination = document.querySelector('.pagination');
    if (existingPagination) existingPagination.remove();

    if (totalPages <= 1) return;

    const startItem = (currentPage - 1) * JOBS_PER_PAGE + 1;
    const endItem = Math.min(currentPage * JOBS_PER_PAGE, totalJobs);

    const paginationHtml = `
        <div class="pagination">
            <span class="pagination-info">Showing ${startItem}-${endItem} of ${totalJobs} jobs</span>
            <div class="pagination-controls">
                <button class="pagination-btn" onclick="goToPage(1)" ${currentPage === 1 ? 'disabled' : ''}>« First</button>
                <button class="pagination-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>‹ Prev</button>
                ${generatePageNumbers(totalPages)}
                <button class="pagination-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>Next ›</button>
                <button class="pagination-btn" onclick="goToPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>Last »</button>
            </div>
        </div>
    `;

    elements.jobContainer.insertAdjacentHTML('afterend', paginationHtml);
}

function generatePageNumbers(totalPages) {
    let pages = [];
    const maxVisible = 5;

    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
        start = Math.max(1, end - maxVisible + 1);
    }

    if (start > 1) {
        pages.push(`<button class="pagination-btn" onclick="goToPage(1)">1</button>`);
        if (start > 2) pages.push(`<span class="pagination-ellipsis">...</span>`);
    }

    for (let i = start; i <= end; i++) {
        pages.push(`<button class="pagination-btn${i === currentPage ? ' active' : ''}" onclick="goToPage(${i})">${i}</button>`);
    }

    if (end < totalPages) {
        if (end < totalPages - 1) pages.push(`<span class="pagination-ellipsis">...</span>`);
        pages.push(`<button class="pagination-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`);
    }

    return pages.join('');
}

function goToPage(page) {
    const totalPages = Math.ceil(filteredJobs.length / JOBS_PER_PAGE);
    if (page < 1 || page > totalPages) return;

    currentPage = page;
    renderJobs(filteredJobs);

    // Smooth scroll to jobs section
    document.getElementById('jobs-container')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateCounts() {
    const visibleCount = filteredJobs.length;
    const totalCount = allJobs.length;

    if (elements.visibleCount) {
        elements.visibleCount.textContent = visibleCount;
    }
    if (elements.totalCount) {
        elements.totalCount.textContent = totalCount;
    }

    // Update header job count
    if (elements.jobCount) {
        const statNumber = elements.jobCount.querySelector('.stat-number');
        if (statNumber) {
            statNumber.textContent = totalCount;
        }
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

        // Company tier filter (also checks sectors for Defense/Finance/Healthcare/Startup)
        if (tier !== 'all') {
            const jobTier = job.company_tier?.tier;
            const jobSectors = job.company_tier?.sectors || [];

            // Check if tier matches directly OR if it's in the sectors array
            if (jobTier !== tier && !jobSectors.includes(tier)) {
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

    // Reset to page 1 when filters change
    currentPage = 1;
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
    // Initialize theme
    initTheme();

    // Set up event listeners (with null checks)
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
    if (elements.backToTop) {
        elements.backToTop.addEventListener('click', scrollToTop);
    }
    if (elements.searchInput) {
        elements.searchInput.addEventListener('input', handleSearch);
    }
    if (elements.searchClear) {
        elements.searchClear.addEventListener('click', () => {
            elements.searchInput.value = '';
            elements.searchClear.classList.remove('visible');
            currentFilters.search = '';
            applyFilters();
        });
    }
    if (elements.categoryFilters) {
        elements.categoryFilters.addEventListener('click', handleChipClick);
    }
    if (elements.tierFilters) {
        elements.tierFilters.addEventListener('click', handleChipClick);
    }
    if (elements.locationFilter) {
        elements.locationFilter.addEventListener('change', handleLocationChange);
    }
    if (elements.resetFilters) {
        elements.resetFilters.addEventListener('click', resetFilters);
    }

    // Scroll listener for back to top
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Fetch and render jobs
    const data = await fetchJobs();

    if (data && data.jobs) {
        allJobs = data.jobs;
        filteredJobs = [...allJobs];

        // Hide loading
        if (elements.loading) {
            elements.loading.style.display = 'none';
        }

        // Render
        renderJobs(filteredJobs);
        updateCounts();
        updateLastUpdated(data.meta?.generated_at);
    } else {
        // Show error state
        if (elements.loading) {
            elements.loading.innerHTML = `
                <div class="empty-icon">⚠️</div>
                <h3>Could not load jobs</h3>
                <p>Please try refreshing the page</p>
            `;
            elements.loading.style.display = 'flex';
            elements.loading.style.flexDirection = 'column';
            elements.loading.style.alignItems = 'center';
            elements.loading.style.justifyContent = 'center';
            elements.loading.style.padding = '4rem';
        }
    }
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
