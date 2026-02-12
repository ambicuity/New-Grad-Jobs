/**
 * New Grad Jobs - Market Insights & Statistics
 * Analyzes real-time data from jobs.json
 */

// ============================================
// State Management
// ============================================
let jobsData = null;
let charts = {};

// ============================================
// DOM Elements
// ============================================
const elements = {
    totalJobs: document.getElementById('total-jobs'),
    totalCompanies: document.getElementById('total-companies'),
    totalCountries: document.getElementById('total-countries'),
    jobsToday: document.getElementById('jobs-today'),
    lastUpdated: document.getElementById('last-updated'),
    topCompanies: document.getElementById('top-companies'),
    topLocations: document.getElementById('top-locations'),
    insightsContainer: document.getElementById('insights-container'),
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
    
    // Update charts for new theme
    updateChartsTheme();
}

function updateChartsTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    Object.values(charts).forEach(chart => {
        if (chart.options.scales) {
            if (chart.options.scales.x) {
                chart.options.scales.x.ticks.color = textColor;
                chart.options.scales.x.grid.color = gridColor;
            }
            if (chart.options.scales.y) {
                chart.options.scales.y.ticks.color = textColor;
                chart.options.scales.y.grid.color = gridColor;
            }
        }
        if (chart.options.plugins.legend) {
            chart.options.plugins.legend.labels.color = textColor;
        }
        chart.update();
    });
}

// ============================================
// Data Fetching
// ============================================
async function fetchJobsData() {
    const paths = ['./jobs.json', '../jobs.json', '/New-Grad-Jobs/docs/jobs.json'];
    
    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.log(`Failed to fetch from ${path}`);
        }
    }
    
    throw new Error('Could not load jobs data');
}

async function fetchMarketHistory() {
    const paths = ['./market-history.json', '../market-history.json', '/New-Grad-Jobs/docs/market-history.json'];
    
    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.log(`Failed to fetch market history from ${path}`);
        }
    }
    
    // Return empty structure if file doesn't exist yet
    return { meta: {}, snapshots: [] };
}

async function fetchPredictions() {
    const paths = ['./predictions.json', '../predictions.json', '/New-Grad-Jobs/docs/predictions.json'];
    
    for (const path of paths) {
        try {
            const response = await fetch(path);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.log(`Failed to fetch predictions from ${path}`);
        }
    }
    
    // Return null if no predictions available yet
    return null;
}

function calculateComparisons(currentData, historyData) {
    const snapshots = historyData.snapshots || [];
    
    if (snapshots.length === 0) {
        return {
            weekOverWeek: null,
            monthOverMonth: null,
            message: 'Collecting data... Comparisons available after 7 days'
        };
    }
    
    const today = new Date();
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // Find snapshots closest to week and month ago
    const weekSnapshot = findClosestSnapshot(snapshots, weekAgo);
    const monthSnapshot = findClosestSnapshot(snapshots, monthAgo);
    
    const currentTotal = currentData.totalJobs;
    
    const comparisons = {
        weekOverWeek: null,
        monthOverMonth: null
    };
    
    if (weekSnapshot) {
        const weekTotal = weekSnapshot.total_jobs;
        const weekChange = currentTotal - weekTotal;
        const weekPercent = ((weekChange / weekTotal) * 100).toFixed(1);
        
        comparisons.weekOverWeek = {
            change: weekChange,
            percent: weekPercent,
            previous: weekTotal,
            current: currentTotal,
            direction: weekChange > 0 ? 'up' : weekChange < 0 ? 'down' : 'stable'
        };
    }
    
    if (monthSnapshot) {
        const monthTotal = monthSnapshot.total_jobs;
        const monthChange = currentTotal - monthTotal;
        const monthPercent = ((monthChange / monthTotal) * 100).toFixed(1);
        
        comparisons.monthOverMonth = {
            change: monthChange,
            percent: monthPercent,
            previous: monthTotal,
            current: currentTotal,
            direction: monthChange > 0 ? 'up' : monthChange < 0 ? 'down' : 'stable'
        };
    }
    
    return comparisons;
}

function findClosestSnapshot(snapshots, targetDate) {
    if (snapshots.length === 0) return null;
    
    const targetTime = targetDate.getTime();
    let closest = null;
    let minDiff = Infinity;
    
    snapshots.forEach(snapshot => {
        const snapshotDate = new Date(snapshot.date);
        const diff = Math.abs(snapshotDate.getTime() - targetTime);
        if (diff < minDiff) {
            minDiff = diff;
            closest = snapshot;
        }
    });
    
    return closest;
}

// ============================================
// Data Analysis
// ============================================
function analyzeData(data) {
    const jobs = data.jobs;
    
    // Basic counts
    const totalJobs = data.meta.total_jobs;
    const companies = [...new Set(jobs.map(j => j.company))];
    const countries = [...new Set(jobs.map(j => extractCountry(j.location)))];
    const today = new Date().toDateString();
    const jobsToday = jobs.filter(j => new Date(j.posted_at).toDateString() === today).length;
    
    // Category breakdown
    const categories = data.meta.categories;
    
    // Company tier breakdown
    const tierCounts = {};
    jobs.forEach(job => {
        const tier = job.company_tier?.tier || 'other';
        tierCounts[tier] = (tierCounts[tier] || 0) + 1;
    });
    
    // Location breakdown (top 15)
    const locationCounts = {};
    jobs.forEach(job => {
        const country = extractCountry(job.location);
        locationCounts[country] = (locationCounts[country] || 0) + 1;
    });
    const topLocations = Object.entries(locationCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);
    
    // Top companies (top 20)
    const companyCounts = {};
    jobs.forEach(job => {
        companyCounts[job.company] = (companyCounts[job.company] || 0) + 1;
    });
    const topCompanies = Object.entries(companyCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20);
    
    // Insights
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

function extractCountry(location) {
    if (!location) return 'Unknown';
    
    // USA patterns
    if (/\b(USA|United States|US)\b/i.test(location) || /\b[A-Z]{2}\b/.test(location.split(',').pop())) {
        return 'USA';
    }
    // Canada
    if (/Canada|Toronto|Vancouver|Montreal|Ottawa/i.test(location)) {
        return 'Canada';
    }
    // India
    if (/India|Bangalore|Hyderabad|Mumbai|Delhi|Pune/i.test(location)) {
        return 'India';
    }
    // UK
    if (/UK|United Kingdom|London|Manchester/i.test(location)) {
        return 'UK';
    }
    // Remote
    if (/Remote/i.test(location)) {
        return 'Remote';
    }
    
    // Extract last part (usually country)
    const parts = location.split(',').map(p => p.trim());
    return parts[parts.length - 1] || 'Other';
}

function generateInsights(jobs, categories, topCompanies, topLocations) {
    const insights = [];
    
    // Most popular category
    const topCategory = categories.reduce((max, cat) => cat.count > max.count ? cat : max, categories[0]);
    insights.push({
        icon: topCategory.emoji,
        title: 'Most In-Demand Role',
        value: topCategory.name,
        description: `${topCategory.count} positions (${Math.round(topCategory.count / jobs.length * 100)}% of all jobs)`
    });
    
    // Top hiring company
    insights.push({
        icon: '🏆',
        title: 'Top Hiring Company',
        value: topCompanies[0][0],
        description: `${topCompanies[0][1]} open positions right now`
    });
    
    // Location diversity
    insights.push({
        icon: '🌍',
        title: 'Geographic Reach',
        value: `${topLocations.length}+ countries`,
        description: `Opportunities available globally with ${topLocations[0][0]} leading at ${topLocations[0][1]} jobs`
    });
    
    // FAANG+ opportunities
    const faangCount = jobs.filter(j => j.company_tier?.tier === 'faang_plus').length;
    if (faangCount > 0) {
        insights.push({
            icon: '🔥',
            title: 'FAANG+ Opportunities',
            value: `${faangCount} positions`,
            description: `${Math.round(faangCount / jobs.length * 100)}% of all jobs are at top-tier companies`
        });
    }
    
    // Remote opportunities
    const remoteCount = jobs.filter(j => /remote/i.test(j.location)).length;
    if (remoteCount > 0) {
        insights.push({
            icon: '🏠',
            title: 'Remote-Friendly',
            value: `${remoteCount} remote jobs`,
            description: `${Math.round(remoteCount / jobs.length * 100)}% of positions offer remote work`
        });
    }
    
    // Sponsorship info
    const sponsorshipCount = jobs.filter(j => !j.flags?.no_sponsorship).length;
    insights.push({
        icon: '✈️',
        title: 'Visa Sponsorship',
        value: `${sponsorshipCount} jobs`,
        description: `${Math.round(sponsorshipCount / jobs.length * 100)}% don't explicitly exclude sponsorship`
    });
    
    return insights;
}

// ============================================
// Rendering
// ============================================
function renderStats(analysis) {
    elements.totalJobs.textContent = analysis.totalJobs.toLocaleString();
    elements.totalCompanies.textContent = analysis.totalCompanies;
    elements.totalCountries.textContent = analysis.totalCountries + '+';
    elements.jobsToday.textContent = analysis.jobsToday;
    
    if (jobsData.meta.generated_at) {
        const date = new Date(jobsData.meta.generated_at);
        elements.lastUpdated.textContent = date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short'
        });
    }
}

function renderComparisons(comparisons) {
    const container = document.getElementById('comparisons-container');
    if (!container) return;
    
    // Check if we have data
    if (comparisons.message) {
        container.innerHTML = `
            <div class="comparison-message">
                <span class="icon">📊</span>
                <p>${comparisons.message}</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    // Week-over-week comparison
    if (comparisons.weekOverWeek) {
        const wow = comparisons.weekOverWeek;
        const arrow = wow.direction === 'up' ? '↑' : wow.direction === 'down' ? '↓' : '→';
        const colorClass = wow.direction === 'up' ? 'positive' : wow.direction === 'down' ? 'negative' : 'neutral';
        
        html += `
            <div class="comparison-card">
                <div class="comparison-header">
                    <span class="icon">📈</span>
                    <h3>Week-over-Week</h3>
                </div>
                <div class="comparison-value ${colorClass}">
                    <span class="arrow">${arrow}</span>
                    <span class="percent">${Math.abs(wow.percent)}%</span>
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
    
    // Month-over-month comparison
    if (comparisons.monthOverMonth) {
        const mom = comparisons.monthOverMonth;
        const arrow = mom.direction === 'up' ? '↑' : mom.direction === 'down' ? '↓' : '→';
        const colorClass = mom.direction === 'up' ? 'positive' : mom.direction === 'down' ? 'negative' : 'neutral';
        
        html += `
            <div class="comparison-card">
                <div class="comparison-header">
                    <span class="icon">📊</span>
                    <h3>Month-over-Month</h3>
                </div>
                <div class="comparison-value ${colorClass}">
                    <span class="arrow">${arrow}</span>
                    <span class="percent">${Math.abs(mom.percent)}%</span>
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
    
    container.innerHTML = html;
}

function renderPredictions(predictions) {
    const container = document.getElementById('predictions-container');
    if (!container) return;
    
    // Check if predictions are available
    if (!predictions) {
        container.innerHTML = `
            <div class="prediction-message">
                <span class="icon">🔮</span>
                <p>AI predictions available after 7 days of data collection</p>
            </div>
        `;
        return;
    }
    
    const outlookConfig = {
        bullish: { emoji: '📈', color: 'positive', label: 'Bullish' },
        neutral: { emoji: '➡️', color: 'neutral', label: 'Neutral' },
        bearish: { emoji: '📉', color: 'negative', label: 'Bearish' }
    };
    
    const outlook = outlookConfig[predictions.outlook] || outlookConfig.neutral;
    
    let html = `
        <div class="predictions-header">
            <div class="prediction-outlook ${outlook.color}">
                <span class="outlook-emoji">${outlook.emoji}</span>
                <div class="outlook-content">
                    <h3>Market Outlook: ${outlook.label}</h3>
                    <p class="confidence">Confidence: ${predictions.confidence}%</p>
                </div>
            </div>
        </div>
        
        <div class="predictions-grid">
            <div class="prediction-card">
                <div class="prediction-header">
                    <span class="icon">📅</span>
                    <h4>7-Day Forecast</h4>
                </div>
                <div class="prediction-value">
                    <span class="number">${predictions.predictions['7_days'].total_jobs.toLocaleString()}</span>
                    <span class="label">Expected Jobs</span>
                </div>
                <div class="prediction-change ${predictions.predictions['7_days'].change_percent >= 0 ? 'positive' : 'negative'}">
                    ${predictions.predictions['7_days'].change_percent >= 0 ? '↑' : '↓'} 
                    ${Math.abs(predictions.predictions['7_days'].change_percent).toFixed(1)}% change
                </div>
            </div>
            
            <div class="prediction-card">
                <div class="prediction-header">
                    <span class="icon">📆</span>
                    <h4>30-Day Forecast</h4>
                </div>
                <div class="prediction-value">
                    <span class="number">${predictions.predictions['30_days'].total_jobs.toLocaleString()}</span>
                    <span class="label">Expected Jobs</span>
                </div>
                <div class="prediction-change ${predictions.predictions['30_days'].change_percent >= 0 ? 'positive' : 'negative'}">
                    ${predictions.predictions['30_days'].change_percent >= 0 ? '↑' : '↓'} 
                    ${Math.abs(predictions.predictions['30_days'].change_percent).toFixed(1)}% change
                </div>
            </div>
        </div>
        
        <div class="trends-container">
            <div class="trend-section growing">
                <h4>🚀 Growing Categories</h4>
                <ul>
                    ${predictions.growing_categories.map(cat => `<li>${cat}</li>`).join('')}
                </ul>
            </div>
            
            <div class="trend-section declining">
                <h4>📊 Declining Categories</h4>
                <ul>
                    ${predictions.declining_categories.map(cat => `<li>${cat}</li>`).join('')}
                </ul>
            </div>
        </div>
        
        <div class="insights-section">
            <h4>💡 AI Insights</h4>
            <ul class="ai-insights">
                ${predictions.insights.map(insight => `<li>${insight}</li>`).join('')}
            </ul>
        </div>
    `;
    
    container.innerHTML = html;
}

function renderCharts(analysis) {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Category Chart
    const categoryCtx = document.getElementById('category-chart').getContext('2d');
    charts.category = new Chart(categoryCtx, {
        type: 'doughnut',
        data: {
            labels: analysis.categories.map(c => c.name),
            datasets: [{
                data: analysis.categories.map(c => c.count),
                backgroundColor: [
                    '#6366f1', '#8b5cf6', '#a855f7', '#ec4899', 
                    '#f59e0b', '#10b981', '#3b82f6'
                ],
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
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round(value / total * 100);
                            return `${label}: ${value} jobs (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Tier Chart
    const tierLabels = {
        'faang_plus': '🔥 FAANG+',
        'unicorn': '🚀 Unicorn',
        'defense': '🛡️ Defense',
        'finance': '💰 Finance',
        'healthcare': '🏥 Healthcare',
        'startup': '⚡ Startup',
        'other': '🏢 Other'
    };
    
    const tierData = Object.entries(analysis.tierCounts)
        .sort((a, b) => b[1] - a[1]);
    
    const tierCtx = document.getElementById('tier-chart').getContext('2d');
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
                        label: function(context) {
                            return `${context.parsed.y} jobs`;
                        }
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
    
    // Location Chart
    const locationCtx = document.getElementById('location-chart').getContext('2d');
    charts.location = new Chart(locationCtx, {
        type: 'bar',
        data: {
            labels: analysis.topLocations.map(([loc]) => loc),
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
                        label: function(context) {
                            return `${context.parsed.x} jobs`;
                        }
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

function renderTopCompanies(topCompanies) {
    const html = topCompanies.map(([company, count], index) => `
        <div class="company-item">
            <div class="company-rank">${index + 1}</div>
            <div class="company-info">
                <div class="company-name">${escapeHtml(company)}</div>
                <div class="company-count">${count} ${count === 1 ? 'job' : 'jobs'}</div>
            </div>
        </div>
    `).join('');
    
    elements.topCompanies.innerHTML = html;
}

function renderTopLocations(topLocations) {
    const html = topLocations.slice(0, 5).map(([location, count], index) => `
        <div class="location-item">
            <div class="location-rank">#${index + 1}</div>
            <div class="location-name">${escapeHtml(location)}</div>
            <div class="location-count">${count}</div>
        </div>
    `).join('');
    
    elements.topLocations.innerHTML = html;
}

function renderInsights(insights) {
    const html = insights.map(insight => `
        <div class="insight-card">
            <div class="insight-icon">${insight.icon}</div>
            <div class="insight-content">
                <h3 class="insight-title">${insight.title}</h3>
                <div class="insight-value">${escapeHtml(insight.value)}</div>
                <p class="insight-description">${escapeHtml(insight.description)}</p>
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
    // Initialize theme
    initTheme();
    
    // Show loading state
    elements.totalJobs.textContent = 'Loading...';
    
    try {
        // Fetch data (parallel for speed)
        const [jobsDataResult, marketHistory, predictions] = await Promise.all([
            fetchJobsData(),
            fetchMarketHistory(),
            fetchPredictions()
        ]);
        
        jobsData = jobsDataResult;
        
        // Analyze data
        const analysis = analyzeData(jobsData);
        
        // Calculate comparisons
        const comparisons = calculateComparisons(analysis, marketHistory);
        
        // Render everything
        renderStats(analysis);
        renderComparisons(comparisons);
        renderPredictions(predictions);
        renderCharts(analysis);
        renderTopCompanies(analysis.topCompanies);
        renderTopLocations(analysis.topLocations);
        renderInsights(analysis.insights);
        
    } catch (error) {
        console.error('Failed to load data:', error);
        elements.totalJobs.textContent = 'Error';
        if (elements.toast) {
            elements.toast.textContent = 'Failed to load job data';
            elements.toast.className = 'toast visible';
            setTimeout(() => elements.toast.classList.remove('visible'), 3000);
        }
    }
    
    // Set up event listeners
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
    if (elements.backToTop) {
        elements.backToTop.addEventListener('click', scrollToTop);
    }
    window.addEventListener('scroll', handleScroll, { passive: true });
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
