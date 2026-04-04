/**
 * New Grad Jobs - Market Insights & Statistics
 * Renders observed market analytics from jobs.json and optional predictions.
 */

// ============================================
// State Management
// ============================================
let jobsData = null;
let charts = {};

const STALE_DATA_THRESHOLD_MINUTES = 120;

// ============================================
// DOM Elements
// ============================================
const elements = {
    totalJobs: document.getElementById('total-jobs'),
    totalCompanies: document.getElementById('total-companies'),
    totalCountries: document.getElementById('total-countries'),
    jobsToday: document.getElementById('jobs-today'),
    lastUpdated: document.getElementById('last-updated'),
    statusChip: document.getElementById('data-status-chip'),
    statusText: document.getElementById('data-status-text'),
    statusDetail: document.getElementById('data-status-detail'),
    topCompanies: document.getElementById('top-companies'),
    topLocations: document.getElementById('top-locations'),
    insightsContainer: document.getElementById('insights-container'),
    comparisonsContainer: document.getElementById('comparisons-container'),
    predictionsContainer: document.getElementById('predictions-container'),
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
    updateChartsTheme();
}

function updateChartsTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    Object.values(charts).forEach((chart) => {
        if (!chart || !chart.options) return;
        if (chart.options.scales) {
            if (chart.options.scales.x) {
                chart.options.scales.x.ticks.color = textColor;
                if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = gridColor;
            }
            if (chart.options.scales.y) {
                chart.options.scales.y.ticks.color = textColor;
                if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = gridColor;
            }
        }
        if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
            chart.options.plugins.legend.labels.color = textColor;
        }
        chart.update();
    });
}

// ============================================
// Data Fetching
// ============================================
async function fetchJsonWithFallback(paths, label, required = false) {
    let lastError = null;

    for (const path of paths) {
        try {
            const response = await fetch(path, { cache: 'no-store' });
            if (!response.ok) continue;
            const data = await response.json();
            return data;
        } catch (error) {
            lastError = error;
            console.log(`Failed to fetch ${label} from ${path}`);
        }
    }

    if (required) {
        throw new Error(`Could not load ${label}${lastError ? `: ${lastError.message}` : ''}`);
    }

    return null;
}

async function fetchJobsData() {
    return fetchJsonWithFallback(
        ['./jobs.json', '../jobs.json', '/New-Grad-Jobs/docs/jobs.json'],
        'jobs data',
        true
    );
}

async function fetchMarketHistory() {
    const data = await fetchJsonWithFallback(
        ['./market-history.json', '../market-history.json', '/New-Grad-Jobs/docs/market-history.json'],
        'market history'
    );

    return data || { meta: {}, snapshots: [] };
}

async function fetchPredictions() {
    return fetchJsonWithFallback(
        ['./predictions.json', '../predictions.json', '/New-Grad-Jobs/docs/predictions.json'],
        'predictions'
    );
}

// ============================================
// Data Normalization
// ============================================
function normalizeJobsData(data) {
    const payload = (data && typeof data === 'object') ? data : {};
    const meta = (payload.meta && typeof payload.meta === 'object') ? payload.meta : {};
    const jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
    const categories = Array.isArray(meta.categories) ? meta.categories : [];

    return {
        meta: {
            generated_at: typeof meta.generated_at === 'string' ? meta.generated_at : null,
            total_jobs: Number.isFinite(Number(meta.total_jobs)) ? Number(meta.total_jobs) : jobs.length,
            categories
        },
        jobs
    };
}

function normalizeMarketHistory(data) {
    const payload = (data && typeof data === 'object') ? data : {};
    const snapshots = Array.isArray(payload.snapshots) ? payload.snapshots : [];
    return {
        meta: payload.meta || {},
        snapshots
    };
}

function normalizePredictions(data) {
    if (!data || typeof data !== 'object') return null;

    const windows = data.predictions || {};
    const sevenDay = windows['7_days'];
    const thirtyDay = windows['30_days'];

    if (!sevenDay || !thirtyDay) return null;

    return {
        outlook: typeof data.outlook === 'string' ? data.outlook : 'neutral',
        confidence: Number.isFinite(Number(data.confidence)) ? Number(data.confidence) : null,
        generated_at: typeof data.generated_at === 'string' ? data.generated_at : null,
        predictions: {
            '7_days': {
                total_jobs: Number.isFinite(Number(sevenDay.total_jobs)) ? Number(sevenDay.total_jobs) : null,
                change_percent: Number.isFinite(Number(sevenDay.change_percent)) ? Number(sevenDay.change_percent) : null
            },
            '30_days': {
                total_jobs: Number.isFinite(Number(thirtyDay.total_jobs)) ? Number(thirtyDay.total_jobs) : null,
                change_percent: Number.isFinite(Number(thirtyDay.change_percent)) ? Number(thirtyDay.change_percent) : null
            }
        },
        growing_categories: Array.isArray(data.growing_categories) ? data.growing_categories : [],
        declining_categories: Array.isArray(data.declining_categories) ? data.declining_categories : [],
        insights: Array.isArray(data.insights) ? data.insights : []
    };
}

// ============================================
// Data Analysis
// ============================================
function analyzeData(data) {
    const jobs = Array.isArray(data.jobs) ? data.jobs : [];

    const totalJobs = Number.isFinite(Number(data.meta.total_jobs))
        ? Number(data.meta.total_jobs)
        : jobs.length;

    const companies = [...new Set(jobs.map((job) => job.company).filter(Boolean))];
    const countries = [...new Set(jobs.map((job) => extractCountry(job.location)).filter(Boolean))];

    const today = new Date().toDateString();
    const jobsToday = jobs.filter((job) => {
        if (!job.posted_at) return false;
        const postedDate = new Date(job.posted_at);
        if (Number.isNaN(postedDate.getTime())) return false;
        return postedDate.toDateString() === today;
    }).length;

    const categories = normalizeCategories(data.meta.categories, jobs);

    const tierCounts = {};
    jobs.forEach((job) => {
        const tier = job.company_tier && job.company_tier.tier ? job.company_tier.tier : 'other';
        tierCounts[tier] = (tierCounts[tier] || 0) + 1;
    });

    const locationCounts = {};
    jobs.forEach((job) => {
        const country = extractCountry(job.location);
        locationCounts[country] = (locationCounts[country] || 0) + 1;
    });

    const topLocations = Object.entries(locationCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);

    const companyCounts = {};
    jobs.forEach((job) => {
        const company = job.company;
        if (!company) return;
        companyCounts[company] = (companyCounts[company] || 0) + 1;
    });

    const topCompanies = Object.entries(companyCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);

    const insights = generateInsights(jobs, categories, topCompanies, topLocations);

    return {
        totalJobs,
        totalCompanies: companies.length,
        totalCountries: countries.length,
        jobsToday,
        categories,
        tierCounts,
        topLocations,
        topCompanies,
        insights
    };
}

function normalizeCategories(metaCategories, jobs) {
    const sourceCategories = Array.isArray(metaCategories) ? metaCategories : [];

    if (sourceCategories.length > 0) {
        return sourceCategories
            .map((category) => ({
                name: category && category.name ? String(category.name) : 'Other',
                count: Number.isFinite(Number(category && category.count)) ? Number(category.count) : 0
            }))
            .filter((category) => category.count > 0)
            .sort((a, b) => b.count - a.count);
    }

    const fallback = {};
    jobs.forEach((job) => {
        const name = (job.category && job.category.name) ? job.category.name : 'Other';
        fallback[name] = (fallback[name] || 0) + 1;
    });

    return Object.entries(fallback)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
}

const US_STATE_CODES = new Set([
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL',
    'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT',
    'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
]);

const CANADA_PROVINCE_CODES = new Set([
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
]);

const INDIA_STATE_CODES = new Set([
    'AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 'JH', 'KA', 'KL', 'MP',
    'MH', 'MN', 'ML', 'MZ', 'NL', 'OD', 'PB', 'RJ', 'SK', 'TN', 'TS', 'TR', 'UP',
    'WB', 'DL', 'JK', 'LA', 'PY', 'AN', 'CH', 'DH', 'DN'
]);

function extractCountry(location) {
    if (!location) return 'Unknown';
    const text = String(location).trim();

    if (/\bRemote\b/i.test(text)) return 'Remote';
    if (/\b(United Kingdom|UK)\b|London|Manchester/i.test(text)) return 'UK';
    if (/\bCanada\b|Toronto|Vancouver|Montreal|Ottawa/i.test(text)) return 'Canada';
    if (/\bIndia\b|Bangalore|Hyderabad|Mumbai|Delhi|Pune/i.test(text)) return 'India';
    if (/\b(USA|United States|US|U\.S\.)\b/i.test(text)) return 'USA';

    const parts = text.split(',').map((part) => part.trim()).filter(Boolean);
    const lastPart = parts[parts.length - 1] || '';
    const previousPart = parts[parts.length - 2] || '';
    const tail = lastPart.toUpperCase();
    const previousTail = previousPart.toUpperCase();

    if (tail === 'CA' && CANADA_PROVINCE_CODES.has(previousTail)) return 'Canada';
    if (tail === 'IN' || INDIA_STATE_CODES.has(tail) || INDIA_STATE_CODES.has(previousTail)) return 'India';
    if (US_STATE_CODES.has(tail)) return 'USA';
    if (CANADA_PROVINCE_CODES.has(tail)) return 'Canada';
    if (tail === 'UK' || tail === 'GB' || tail === 'UNITED KINGDOM') return 'UK';

    if (tail === 'US') return 'USA';
    if (tail === 'CA') return 'Canada';

    if (!parts.length) return 'Other';
    return parts[parts.length - 1] || 'Other';
}

function generateInsights(jobs, categories, topCompanies, topLocations) {
    if (!jobs.length) {
        return [{
            title: 'No Active Data',
            value: '0 jobs',
            description: 'No active jobs were available in the latest dataset snapshot.'
        }];
    }

    const insights = [];

    if (categories.length > 0) {
        const topCategory = categories[0];
        insights.push({
            title: 'Most In-Demand Role',
            value: topCategory.name,
            description: `${topCategory.count} positions (${Math.round((topCategory.count / jobs.length) * 100)}% of all jobs)`
        });
    }

    if (topCompanies.length > 0) {
        insights.push({
            title: 'Top Hiring Company',
            value: topCompanies[0][0],
            description: `${topCompanies[0][1]} open positions right now`
        });
    }

    if (topLocations.length > 0) {
        insights.push({
            title: 'Geographic Reach',
            value: `${topLocations.length}+ countries`,
            description: `${topLocations[0][0]} currently leads with ${topLocations[0][1]} jobs`
        });
    }

    const faangCount = jobs.filter((job) => job.company_tier && job.company_tier.tier === 'faang_plus').length;
    if (faangCount > 0) {
        insights.push({
            title: 'FAANG+ Opportunities',
            value: `${faangCount} positions`,
            description: `${Math.round((faangCount / jobs.length) * 100)}% of all jobs are at top-tier companies`
        });
    }

    const remoteCount = jobs.filter((job) => /remote/i.test(job.location || '')).length;
    if (remoteCount > 0) {
        insights.push({
            title: 'Remote-Friendly Roles',
            value: `${remoteCount} jobs`,
            description: `${Math.round((remoteCount / jobs.length) * 100)}% of positions mention remote work`
        });
    }

    const sponsorshipCount = jobs.filter((job) => !(job.flags && job.flags.no_sponsorship)).length;
    insights.push({
        title: 'Visa Sponsorship',
        value: `${sponsorshipCount} jobs`,
        description: `${Math.round((sponsorshipCount / jobs.length) * 100)}% do not explicitly exclude sponsorship`
    });

    return insights;
}

function calculateComparisons(currentData, historyData) {
    const snapshots = Array.isArray(historyData.snapshots) ? historyData.snapshots : [];

    if (snapshots.length === 0) {
        return {
            weekOverWeek: null,
            monthOverMonth: null,
            message: 'No historical snapshots yet. Trend comparisons appear once history accumulates.'
        };
    }

    const today = new Date();
    const weekAgo = new Date(today.getTime() - (7 * 24 * 60 * 60 * 1000));
    const monthAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    const weekSnapshot = findClosestSnapshot(snapshots, weekAgo);
    const monthSnapshot = findClosestSnapshot(snapshots, monthAgo);

    const currentTotal = currentData.totalJobs;

    return {
        weekOverWeek: buildComparison(weekSnapshot, currentTotal),
        monthOverMonth: buildComparison(monthSnapshot, currentTotal)
    };
}

function findClosestSnapshot(snapshots, targetDate) {
    if (!snapshots.length) return null;

    const targetTime = targetDate.getTime();
    let closest = null;
    let minDiff = Infinity;

    snapshots.forEach((snapshot) => {
        const snapshotDate = new Date(snapshot.date || snapshot.timestamp || '');
        if (Number.isNaN(snapshotDate.getTime())) return;

        const diff = Math.abs(snapshotDate.getTime() - targetTime);
        if (diff < minDiff) {
            minDiff = diff;
            closest = snapshot;
        }
    });

    return closest;
}

function buildComparison(snapshot, currentTotal) {
    if (!snapshot || !Number.isFinite(Number(snapshot.total_jobs))) return null;

    const previous = Number(snapshot.total_jobs);
    const change = currentTotal - previous;
    const percent = previous > 0 ? ((change / previous) * 100) : 0;

    return {
        change,
        percent,
        previous,
        current: currentTotal,
        direction: change > 0 ? 'up' : change < 0 ? 'down' : 'stable'
    };
}

// ============================================
// Rendering Utilities
// ============================================
function setKpiCardState(stateClass) {
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach((card) => {
        card.classList.remove('is-loading', 'is-ready', 'is-empty', 'is-error', 'is-stale');
        card.classList.add(stateClass);
    });
}

function setStatusChip(stateClass, message, detail) {
    if (elements.statusChip) {
        elements.statusChip.classList.remove('is-loading', 'is-ready', 'is-empty', 'is-error', 'is-stale');
        elements.statusChip.classList.add(stateClass);
    }
    if (elements.statusText) elements.statusText.textContent = message;
    if (elements.statusDetail) elements.statusDetail.textContent = detail;
}

function setSectionMessage(container, message, variant = '') {
    if (!container) return;
    const variantClass = variant ? ` ${variant}` : '';
    container.innerHTML = `<div class="section-message${variantClass}">${escapeHtml(message)}</div>`;
}

function setLoadingState() {
    setKpiCardState('is-loading');

    if (elements.totalJobs) elements.totalJobs.textContent = '--';
    if (elements.totalCompanies) elements.totalCompanies.textContent = '--';
    if (elements.totalCountries) elements.totalCountries.textContent = '--';
    if (elements.jobsToday) elements.jobsToday.textContent = '--';
    if (elements.lastUpdated) elements.lastUpdated.textContent = 'Loading...';

    setStatusChip(
        'is-loading',
        'Loading analytics data...',
        'Validating freshness, trends, and chart availability.'
    );

    setSectionMessage(elements.comparisonsContainer, 'Loading market trend comparisons...', 'loading');
    setSectionMessage(elements.topCompanies, 'Loading top companies...', 'loading');
    setSectionMessage(elements.topLocations, 'Loading location breakdown...', 'loading');
    setSectionMessage(elements.insightsContainer, 'Loading key insights...', 'loading');
    setSectionMessage(elements.predictionsContainer, 'Loading forecast module...', 'loading');
}

function setErrorState(message) {
    destroyCharts();
    setKpiCardState('is-error');

    if (elements.totalJobs) elements.totalJobs.textContent = 'Unavailable';
    if (elements.totalCompanies) elements.totalCompanies.textContent = 'Unavailable';
    if (elements.totalCountries) elements.totalCountries.textContent = 'Unavailable';
    if (elements.jobsToday) elements.jobsToday.textContent = 'Unavailable';
    if (elements.lastUpdated) elements.lastUpdated.textContent = 'Unavailable';

    setStatusChip(
        'is-error',
        'Analytics temporarily unavailable',
        message || 'The latest stats payload could not be loaded or parsed.'
    );

    setSectionMessage(elements.comparisonsContainer, 'Market trend comparisons are unavailable right now.', 'error');
    setSectionMessage(elements.topCompanies, 'Top hiring companies are unavailable right now.', 'error');
    setSectionMessage(elements.topLocations, 'Location insights are unavailable right now.', 'error');
    setSectionMessage(elements.insightsContainer, 'Key insights are unavailable right now.', 'error');
    setSectionMessage(elements.predictionsContainer, 'Predictions are unavailable right now.', 'error');

    if (elements.toast) {
        elements.toast.textContent = 'Failed to load analytics data';
        elements.toast.className = 'toast visible';
        setTimeout(() => elements.toast.classList.remove('visible'), 3000);
    }
}

function destroyCharts() {
    Object.values(charts).forEach((chart) => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    charts = {};
}

function formatDateForDisplay(rawDate) {
    if (!rawDate) return null;
    const date = new Date(rawDate);
    if (Number.isNaN(date.getTime())) return null;

    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    });
}

function getDataAgeMinutes(rawDate) {
    if (!rawDate) return null;
    const generated = new Date(rawDate);
    if (Number.isNaN(generated.getTime())) return null;

    return Math.floor((Date.now() - generated.getTime()) / (1000 * 60));
}

// ============================================
// Rendering
// ============================================
function renderStats(analysis, generatedAt) {
    if (elements.totalJobs) elements.totalJobs.textContent = analysis.totalJobs.toLocaleString();
    if (elements.totalCompanies) elements.totalCompanies.textContent = analysis.totalCompanies.toLocaleString();
    if (elements.totalCountries) elements.totalCountries.textContent = `${analysis.totalCountries}+`;
    if (elements.jobsToday) elements.jobsToday.textContent = analysis.jobsToday.toLocaleString();

    const formattedDate = formatDateForDisplay(generatedAt);
    if (elements.lastUpdated) {
        elements.lastUpdated.textContent = formattedDate || 'Unavailable';
    }

    if (analysis.totalJobs === 0) {
        setKpiCardState('is-empty');
        setStatusChip(
            'is-empty',
            'No active jobs in the latest snapshot',
            'The data payload is valid, but currently contains zero active postings.'
        );
        return;
    }

    const ageMinutes = getDataAgeMinutes(generatedAt);
    if (ageMinutes !== null && ageMinutes > STALE_DATA_THRESHOLD_MINUTES) {
        setKpiCardState('is-stale');
        setStatusChip(
            'is-stale',
            'Data may be stale',
            `Last successful update was ${ageMinutes} minutes ago (expected cadence: every 5 minutes).`
        );
        return;
    }

    setKpiCardState('is-ready');
    setStatusChip(
        'is-ready',
        'Analytics data is current',
        'Observed metrics and charts are based on the latest available snapshot.'
    );
}

function renderComparisons(comparisons) {
    const container = elements.comparisonsContainer;
    if (!container) return;

    if (comparisons.message) {
        setSectionMessage(container, comparisons.message);
        return;
    }

    let html = '';

    if (comparisons.weekOverWeek) {
        const wow = comparisons.weekOverWeek;
        const arrow = wow.direction === 'up' ? '↑' : wow.direction === 'down' ? '↓' : '→';
        const colorClass = wow.direction === 'up' ? 'positive' : wow.direction === 'down' ? 'negative' : 'neutral';

        html += `
            <div class="comparison-card">
                <div class="comparison-header">
                    <h3>Week-over-Week</h3>
                </div>
                <div class="comparison-value ${colorClass}">
                    <span class="arrow">${arrow}</span>
                    <span class="percent">${Math.abs(wow.percent).toFixed(1)}%</span>
                </div>
                <div class="comparison-details">
                    <div class="detail-row">
                        <span>Current:</span>
                        <strong>${wow.current.toLocaleString()} jobs</strong>
                    </div>
                    <div class="detail-row">
                        <span>Last Week:</span>
                        <strong>${wow.previous.toLocaleString()} jobs</strong>
                    </div>
                    <div class="detail-row">
                        <span>Change:</span>
                        <strong>${wow.change > 0 ? '+' : ''}${wow.change.toLocaleString()} jobs</strong>
                    </div>
                </div>
            </div>
        `;
    }

    if (comparisons.monthOverMonth) {
        const mom = comparisons.monthOverMonth;
        const arrow = mom.direction === 'up' ? '↑' : mom.direction === 'down' ? '↓' : '→';
        const colorClass = mom.direction === 'up' ? 'positive' : mom.direction === 'down' ? 'negative' : 'neutral';

        html += `
            <div class="comparison-card">
                <div class="comparison-header">
                    <h3>Month-over-Month</h3>
                </div>
                <div class="comparison-value ${colorClass}">
                    <span class="arrow">${arrow}</span>
                    <span class="percent">${Math.abs(mom.percent).toFixed(1)}%</span>
                </div>
                <div class="comparison-details">
                    <div class="detail-row">
                        <span>Current:</span>
                        <strong>${mom.current.toLocaleString()} jobs</strong>
                    </div>
                    <div class="detail-row">
                        <span>Last Month:</span>
                        <strong>${mom.previous.toLocaleString()} jobs</strong>
                    </div>
                    <div class="detail-row">
                        <span>Change:</span>
                        <strong>${mom.change > 0 ? '+' : ''}${mom.change.toLocaleString()} jobs</strong>
                    </div>
                </div>
            </div>
        `;
    }

    if (!html) {
        setSectionMessage(container, 'Historical comparison data is not available yet.');
        return;
    }

    container.innerHTML = html;
}

function renderPredictions(predictions) {
    const container = elements.predictionsContainer;
    if (!container) return;

    const normalized = predictions;

    if (!normalized) {
        container.innerHTML = `
            <div class="prediction-message">
                <p>Forecasts are unavailable right now. They appear after enough historical data is collected.</p>
                <p class="prediction-disclaimer">Forecasts are directional estimates and should be used with observed trend data above.</p>
            </div>
        `;
        return;
    }

    const outlookConfig = {
        bullish: { color: 'positive', label: 'Bullish' },
        neutral: { color: 'neutral', label: 'Neutral' },
        bearish: { color: 'negative', label: 'Bearish' }
    };

    const outlook = outlookConfig[normalized.outlook] || outlookConfig.neutral;
    const sevenDay = normalized.predictions['7_days'];
    const thirtyDay = normalized.predictions['30_days'];
    const generatedLabel = formatDateForDisplay(normalized.generated_at);

    if (sevenDay.total_jobs === null || sevenDay.change_percent === null || thirtyDay.total_jobs === null || thirtyDay.change_percent === null) {
        setSectionMessage(container, 'Prediction payload is incomplete. Showing observed analytics only.');
        return;
    }

    const confidenceText = normalized.confidence === null ? 'Not available' : `${normalized.confidence}%`;

    container.innerHTML = `
        <div class="predictions-header">
            <div class="prediction-outlook ${outlook.color}">
                <div class="outlook-content">
                    <h3>Market Outlook: ${outlook.label}</h3>
                    <p class="confidence">Confidence: ${confidenceText}</p>
                    ${generatedLabel ? `<p class="confidence">Forecast generated: ${generatedLabel}</p>` : ''}
                </div>
            </div>
        </div>

        <div class="predictions-grid">
            <div class="prediction-card">
                <div class="prediction-header">
                    <h4>7-Day Forecast</h4>
                </div>
                <div class="prediction-value">
                    <span class="number">${sevenDay.total_jobs.toLocaleString()}</span>
                    <span class="label">Estimated Total Jobs</span>
                </div>
                <div class="prediction-change ${sevenDay.change_percent >= 0 ? 'positive' : 'negative'}">
                    ${sevenDay.change_percent >= 0 ? '↑' : '↓'}
                    ${Math.abs(sevenDay.change_percent).toFixed(1)}% projected change
                </div>
            </div>

            <div class="prediction-card">
                <div class="prediction-header">
                    <h4>30-Day Forecast</h4>
                </div>
                <div class="prediction-value">
                    <span class="number">${thirtyDay.total_jobs.toLocaleString()}</span>
                    <span class="label">Estimated Total Jobs</span>
                </div>
                <div class="prediction-change ${thirtyDay.change_percent >= 0 ? 'positive' : 'negative'}">
                    ${thirtyDay.change_percent >= 0 ? '↑' : '↓'}
                    ${Math.abs(thirtyDay.change_percent).toFixed(1)}% projected change
                </div>
            </div>
        </div>

        <div class="trends-container">
            <div class="trend-section growing">
                <h4>Growing Categories</h4>
                <ul>
                    ${(normalized.growing_categories.length ? normalized.growing_categories : ['No forecast signal']).map((category) => `<li>${escapeHtml(String(category))}</li>`).join('')}
                </ul>
            </div>

            <div class="trend-section declining">
                <h4>Declining Categories</h4>
                <ul>
                    ${(normalized.declining_categories.length ? normalized.declining_categories : ['No forecast signal']).map((category) => `<li>${escapeHtml(String(category))}</li>`).join('')}
                </ul>
            </div>
        </div>

        <div class="insights-section">
            <h4>AI Insights</h4>
            <ul class="ai-insights">
                ${(normalized.insights.length ? normalized.insights : ['No additional forecast insights available.']).map((insight) => `<li>${escapeHtml(String(insight))}</li>`).join('')}
            </ul>
            <p class="prediction-disclaimer">Forecasts are model-generated estimates. Use them alongside observed analytics, not as confirmed outcomes.</p>
        </div>
    `;
}

function renderCharts(analysis) {
    destroyCharts();

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    if (!analysis.categories.length && analysis.totalJobs === 0) {
        return;
    }

    const categoryCanvas = document.getElementById('category-chart');
    const tierCanvas = document.getElementById('tier-chart');
    const locationCanvas = document.getElementById('location-chart');

    if (categoryCanvas && analysis.categories.length > 0) {
        const categoryCtx = categoryCanvas.getContext('2d');
        charts.category = new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: analysis.categories.map((category) => category.name),
                datasets: [{
                    data: analysis.categories.map((category) => category.count),
                    backgroundColor: ['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: textColor,
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((sum, item) => sum + item, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} jobs (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    if (tierCanvas && Object.keys(analysis.tierCounts).length > 0) {
        const tierLabels = {
            faang_plus: 'FAANG+',
            unicorn: 'Unicorn',
            defense: 'Defense',
            finance: 'Finance',
            healthcare: 'Healthcare',
            startup: 'Startup',
            other: 'Other'
        };

        const tierData = Object.entries(analysis.tierCounts).sort((a, b) => b[1] - a[1]);
        const tierCtx = tierCanvas.getContext('2d');

        charts.tier = new Chart(tierCtx, {
            type: 'bar',
            data: {
                labels: tierData.map(([tier]) => tierLabels[tier] || tier),
                datasets: [{
                    label: 'Jobs',
                    data: tierData.map(([, count]) => count),
                    backgroundColor: '#6366f1',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        callbacks: {
                            label: (context) => `${context.parsed.y} jobs`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: textColor }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: { color: textColor },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    if (locationCanvas && analysis.topLocations.length > 0) {
        const locationCtx = locationCanvas.getContext('2d');
        charts.location = new Chart(locationCtx, {
            type: 'bar',
            data: {
                labels: analysis.topLocations.map(([location]) => location),
                datasets: [{
                    label: 'Jobs',
                    data: analysis.topLocations.map(([, count]) => count),
                    backgroundColor: '#8b5cf6',
                    borderRadius: 8
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        callbacks: {
                            label: (context) => `${context.parsed.x} jobs`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: textColor }
                    }
                }
            }
        });
    }
}

function renderTopCompanies(topCompanies) {
    if (!elements.topCompanies) return;

    if (!topCompanies.length) {
        setSectionMessage(elements.topCompanies, 'No company-level hiring data available.');
        return;
    }

    const html = topCompanies.map(([company, count], index) => `
        <div class="company-item">
            <div class="company-rank">${index + 1}</div>
            <div class="company-info">
                <div class="company-name">${escapeHtml(String(company))}</div>
                <div class="company-count">${count} ${count === 1 ? 'job' : 'jobs'}</div>
            </div>
        </div>
    `).join('');

    elements.topCompanies.innerHTML = html;
}

function renderTopLocations(topLocations) {
    if (!elements.topLocations) return;

    if (!topLocations.length) {
        setSectionMessage(elements.topLocations, 'No location data available.');
        return;
    }

    const html = topLocations.slice(0, 5).map(([location, count], index) => `
        <div class="location-item">
            <div class="location-rank">#${index + 1}</div>
            <div class="location-name">${escapeHtml(String(location))}</div>
            <div class="location-count">${count}</div>
        </div>
    `).join('');

    elements.topLocations.innerHTML = html;
}

function renderInsights(insights) {
    if (!elements.insightsContainer) return;

    if (!insights.length) {
        setSectionMessage(elements.insightsContainer, 'No derived insights available.');
        return;
    }

    const html = insights.map((insight) => `
        <div class="insight-card">
            <div class="insight-content">
                <h3 class="insight-title">${escapeHtml(String(insight.title))}</h3>
                <div class="insight-value">${escapeHtml(String(insight.value))}</div>
                <p class="insight-description">${escapeHtml(String(insight.description))}</p>
            </div>
        </div>
    `).join('');

    elements.insightsContainer.innerHTML = html;
}

// ============================================
// Utilities
// ============================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function handleScroll() {
    if (!elements.backToTop) return;
    if (window.scrollY > 500) {
        elements.backToTop.classList.add('visible');
    } else {
        elements.backToTop.classList.remove('visible');
    }
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================
// Initialization
// ============================================
async function init() {
    initTheme();

    if (typeof window.initMobileMenu === 'function') {
        window.initMobileMenu();
    }

    setLoadingState();

    try {
        const [jobsDataRaw, marketHistoryRaw, predictionsRaw] = await Promise.all([
            fetchJobsData(),
            fetchMarketHistory(),
            fetchPredictions()
        ]);

        jobsData = normalizeJobsData(jobsDataRaw);
        const marketHistory = normalizeMarketHistory(marketHistoryRaw);
        const predictions = normalizePredictions(predictionsRaw);

        const analysis = analyzeData(jobsData);
        const comparisons = calculateComparisons(analysis, marketHistory);

        renderStats(analysis, jobsData.meta.generated_at);
        renderComparisons(comparisons);
        renderTopCompanies(analysis.topCompanies);
        renderCharts(analysis);
        renderTopLocations(analysis.topLocations);
        renderInsights(analysis.insights);
        renderPredictions(predictions);
    } catch (error) {
        console.error('Failed to load analytics data:', error);
        setErrorState(error.message);
    }

    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
    if (elements.backToTop) {
        elements.backToTop.addEventListener('click', scrollToTop);
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
}

document.addEventListener('DOMContentLoaded', init);
