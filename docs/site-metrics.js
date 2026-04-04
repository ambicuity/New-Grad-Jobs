/**
 * Shared site metric loader.
 * Fetches docs/health.json and hydrates data-site-metric placeholders.
 */

(function initSiteMetrics(window, document) {
    const METRIC_PATHS = [
        './health.json',
        '../health.json',
        '/New-Grad-Jobs/docs/health.json',
        '/New-Grad-Jobs/health.json',
        'health.json',
    ];

    let cachedPromise = null;

    function toNumber(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    function formatMetric(value, suffix = '') {
        const asNumber = toNumber(value);
        if (asNumber === null) return '--';
        return `${asNumber.toLocaleString()}${suffix}`;
    }

    function applyMetricBindings(metrics) {
        const nodes = document.querySelectorAll('[data-site-metric]');
        nodes.forEach((node) => {
            const key = node.getAttribute('data-site-metric');
            const suffix = node.getAttribute('data-metric-suffix') || '';
            if (!key || !(key in metrics)) return;
            node.textContent = formatMetric(metrics[key], suffix);
        });
    }

    async function fetchMetrics() {
        for (const path of METRIC_PATHS) {
            try {
                const response = await fetch(path, { priority: 'low' });
                if (!response.ok) continue;

                const data = await response.json();
                if (data && typeof data === 'object') {
                    window.siteMetrics = data;
                    applyMetricBindings(data);
                    return data;
                }
            } catch (error) {
                console.log('Failed to load site metrics from:', path);
            }
        }

        window.siteMetrics = null;
        return null;
    }

    window.loadSiteMetrics = function loadSiteMetrics() {
        if (!cachedPromise) {
            cachedPromise = fetchMetrics();
        }
        return cachedPromise;
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.loadSiteMetrics();
    });
})(window, document);
