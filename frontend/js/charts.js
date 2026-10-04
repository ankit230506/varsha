/* ═══════════════════════════════════════════════════════════════
   VARSHA — Chart.js helpers (dark theme, amber/green/red palette)
   ═══════════════════════════════════════════════════════════════ */

// Global defaults
Chart.defaults.color = '#9a9a9a';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.resizeDelay = 100;

const CHART_COLORS = {
    amber:    '#d4940a',
    green:    '#1a8a50',
    red:      '#c62828',
    orange:   '#d4690a',
    grey:     '#3a3a48',
    gridLine: '#2a2a35',
    bgCard:   '#1c1c24',
};

function updateChartTheme(theme) {
    const isLight = theme === 'light';
    CHART_COLORS.gridLine = isLight ? '#cbd5e1' : '#2a2a35';
    CHART_COLORS.bgCard   = isLight ? '#ffffff' : '#1c1c24';
    CHART_COLORS.grey     = isLight ? '#94a3b8' : '#3a3a48';
    Chart.defaults.color   = isLight ? '#475569' : '#9a9a9a';
}
window.updateChartTheme = updateChartTheme;

// Track chart instances by canvas id for proper cleanup
const _charts = {};

function _destroyChart(canvasId) {
    if (_charts[canvasId]) {
        _charts[canvasId].destroy();
        delete _charts[canvasId];
    }
    const canvas = document.getElementById(canvasId);
    if (canvas) {
        canvas.removeAttribute('style');
        canvas.style.maxHeight = '100%';
        canvas.style.width = '100%';
    }
}

/**
 * 24-hour time series with dual Y axes (rainfall + temperature)
 */
function createTimeSeriesChart(canvasId, labels, rainData, tempData, humData) {
    _destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    _charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Rainfall (mm/h)',
                    data: rainData,
                    borderColor: CHART_COLORS.green,
                    backgroundColor: 'rgba(26, 138, 80, 0.15)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    yAxisID: 'y',
                    borderWidth: 2,
                },
                {
                    label: 'Temperature (°C)',
                    data: tempData,
                    borderColor: CHART_COLORS.amber,
                    borderDash: [4, 2],
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    yAxisID: 'y1',
                    borderWidth: 1.5,
                },
                {
                    label: 'Humidity (%)',
                    data: humData,
                    borderColor: CHART_COLORS.orange,
                    borderDash: [2, 2],
                    fill: false,
                    tension: 0.3,
                    pointRadius: 1,
                    yAxisID: 'y1',
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    grid: { color: CHART_COLORS.gridLine },
                    ticks: { maxTicksLimit: 8 },
                },
                y: {
                    position: 'left',
                    title: { display: true, text: 'Rainfall mm/h', color: CHART_COLORS.green },
                    grid: { color: CHART_COLORS.gridLine },
                    beginAtZero: true,
                },
                y1: {
                    position: 'right',
                    title: { display: true, text: 'Temp °C / Hum %' },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

/**
 * 6-hour forecast bar chart with confidence bands
 */
function createForecastChart(canvasId, forecastData) {
    _destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const labels = forecastData.map(f => f.hour);
    const rain = forecastData.map(f => f.predicted_rainfall);
    const lower = forecastData.map(f => f.confidence_lower);
    const upper = forecastData.map(f => f.confidence_upper);
    const probs = forecastData.map(f => f.rainfall_prob);

    _charts[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Rain (mm/h)',
                    data: rain,
                    backgroundColor: CHART_COLORS.green,
                    borderWidth: 0,
                    order: 2,
                },
                {
                    label: 'Upper Bound',
                    data: upper,
                    backgroundColor: 'rgba(26, 138, 80, 0.2)',
                    borderWidth: 0,
                    order: 3,
                },
                {
                    label: 'Rain Probability',
                    data: probs,
                    type: 'line',
                    borderColor: CHART_COLORS.amber,
                    pointRadius: 3,
                    fill: false,
                    yAxisID: 'y1',
                    borderWidth: 2,
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'mm/h', color: CHART_COLORS.green },
                    grid: { color: CHART_COLORS.gridLine },
                },
                y1: {
                    position: 'right',
                    min: 0, max: 1,
                    title: { display: true, text: 'Probability' },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

/**
 * XAI horizontal bar chart — channel attributions
 */
function createAttributionChart(canvasId, labels, values) {
    _destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Generate color gradient from amber to green
    const colors = values.map((_, i) => {
        const t = i / Math.max(values.length - 1, 1);
        return t < 0.5 ? CHART_COLORS.amber : CHART_COLORS.green;
    });

    _charts[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Attribution',
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    max: Math.max(...values) * 1.2,
                    grid: { color: CHART_COLORS.gridLine },
                    ticks: { callback: v => (v * 100).toFixed(0) + '%' },
                },
                y: { grid: { display: false } },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => (ctx.raw * 100).toFixed(1) + '% contribution',
                    },
                },
            },
        },
    });
}

/**
 * Reliability / calibration diagram
 */
function createReliabilityDiagram(canvasId, predicted, observed) {
    _destroyChart(canvasId);
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    _charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: predicted.map(p => p.toFixed(1)),
            datasets: [
                {
                    label: 'Model Calibration',
                    data: observed,
                    borderColor: CHART_COLORS.amber,
                    backgroundColor: CHART_COLORS.amber,
                    pointRadius: 4,
                    fill: false,
                    borderWidth: 2,
                },
                {
                    label: 'Perfect Calibration',
                    data: predicted,
                    borderColor: CHART_COLORS.grey,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Forecast Probability' },
                    grid: { color: CHART_COLORS.gridLine },
                },
                y: {
                    title: { display: true, text: 'Observed Frequency' },
                    grid: { color: CHART_COLORS.gridLine },
                    min: 0, max: 1,
                },
            },
        },
    });
}
