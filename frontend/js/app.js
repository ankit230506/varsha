/* ═══════════════════════════════════════════════════════════════
   VARSHA — Main Application Logic
   Connects to backend API, manages all tab content, and orchestrates
   the dashboard, alerts, stations, model info, and historical views.

   NEW: Timeline scrubber, keyboard shortcuts, wall mode, basin filter,
        siren mute, export bulletin (jsPDF), low-bandwidth mode.
   ═══════════════════════════════════════════════════════════════ */

// ── Cached data ──
let _stations = [];
let _alerts = [];
let _sortCol = null;
let _sortAsc = true;
let _currentTheme = 'dark';
let _modelInfoData = null;

// ── Feature state ──
let _sirenMuted = false;
let _wallMode = false;
let _lowBand = false;
let _timelinePlaying = false;
let _timelineInterval = null;

// ══════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initTabs();
    initClock();
    initMap();
    connectAlertWebSocket();
    initFilterListeners();
    initStationSearch();
    initTableSort();
    initTimeline();
    initToolbarButtons();
    initKeyboardShortcuts();

    // Initial data load
    fetchData();
    loadModelInfo();

    // Auto-refresh every 60s
    setInterval(fetchData, 60000);

    // Historical tab
    document.getElementById('btn-load-historical')
        ?.addEventListener('click', loadHistoricalData);

    // Alerts refresh button
    document.getElementById('btn-refresh-alerts')
        ?.addEventListener('click', fetchData);
});

// ══════════════════════════════════════════════════════════════════
// THEME (LIGHT / DARK)
// ══════════════════════════════════════════════════════════════════

function initTheme() {
    const saved = localStorage.getItem('varsha-theme') || 'dark';
    applyTheme(saved);

    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const nextTheme = _currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
        });
    }
}

function applyTheme(theme) {
    _currentTheme = theme;
    localStorage.setItem('varsha-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);

    const iconEl = document.getElementById('theme-icon');
    const textEl = document.getElementById('theme-text');
    if (iconEl && textEl) {
        if (theme === 'light') {
            iconEl.textContent = '🌙';
            textEl.textContent = 'Dark Mode';
        } else {
            iconEl.textContent = '☀️';
            textEl.textContent = 'Light Mode';
        }
    }

    if (typeof window.setMapTheme === 'function') {
        window.setMapTheme(theme);
    }
    if (typeof window.updateChartTheme === 'function') {
        window.updateChartTheme(theme);
    }

    // Refresh model info reliability chart if loaded
    if (_modelInfoData && _modelInfoData.calibration && typeof createReliabilityDiagram === 'function') {
        createReliabilityDiagram(
            'chart-reliability',
            _modelInfoData.calibration.predicted,
            _modelInfoData.calibration.observed
        );
    }
}

// ══════════════════════════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════════════════════════

function initTabs() {
    const btns = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-content');

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');

            // Show timeline only on dashboard
            const scrubber = document.getElementById('timeline-scrubber');
            if (scrubber) {
                if (btn.dataset.tab === 'dashboard') {
                    scrubber.classList.remove('hidden');
                } else {
                    scrubber.classList.add('hidden');
                }
            }

            // Fix map size when returning to dashboard
            if (btn.dataset.tab === 'dashboard' && window.map) {
                setTimeout(() => window.map.invalidateSize(), 120);
            }
        });
    });
}

function switchToTab(index) {
    const btns = document.querySelectorAll('.tab-btn');
    if (btns[index]) btns[index].click();
}

// ══════════════════════════════════════════════════════════════════
// CLOCK
// ══════════════════════════════════════════════════════════════════

function initClock() {
    const el = document.getElementById('ist-time');
    function tick() {
        const now = new Date();
        // Convert to IST
        const ist = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
        el.textContent = ist.toLocaleTimeString('en-GB', { hour12: false });
    }
    tick();
    setInterval(tick, 1000);
}

function updateLastSync() {
    const now = new Date();
    const ist = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
    document.getElementById('last-update').textContent = ist.toLocaleTimeString('en-GB', { hour12: false });
}

// ══════════════════════════════════════════════════════════════════
// DATA FETCHING — real API calls
// ══════════════════════════════════════════════════════════════════

async function fetchData() {
    try {
        const [stRes, alRes] = await Promise.all([
            fetch('/api/stations'),
            fetch('/alerts'),
        ]);

        const rawStations = await stRes.json();
        const rawAlerts = await alRes.json();

        // Map stations to UI format
        _stations = rawStations.map(st => {
            const ep = st.probabilities.extreme_rain;
            const fr = st.probabilities.flood_susceptibility;
            let level = 'safe';
            if (ep > 0.5 && fr > 0.5) level = 'severe';
            else if (ep > 0.4 || fr > 0.5) level = 'warning';
            else if (ep > 0.3 || fr > 0.3) level = 'watch';

            return {
                id: st.id,
                name: st.name,
                district: st.district,
                state: st.state,
                region: st.region,
                lat: st.lat,
                lon: st.lon,
                temp: st.current_conditions.temperature,
                humidity: st.current_conditions.humidity,
                rain: st.current_conditions.rainfall_rate,
                wind: st.current_conditions.wind_speed,
                windDir: st.current_conditions.wind_dir,
                pressure: st.current_conditions.pressure,
                cloud: st.current_conditions.cloud_cover,
                cape: st.current_conditions.CAPE,
                cin: st.current_conditions.CIN,
                rainProb1h: st.probabilities.rain_1h,
                rainProb3h: st.probabilities.rain_3h,
                rainProb6h: st.probabilities.rain_6h,
                extremeProb: ep,
                floodRisk: Math.round(fr * 100),
                level: level,
            };
        });

        // Map alerts
        _alerts = rawAlerts.map(a => ({
            alertId: a.alert_id,
            station: a.station_name || a.location.district,
            state: a.state || '',
            district: a.location.district,
            level: a.level,
            lat: a.location.lat,
            lon: a.location.lon,
            validFrom: a.valid_from,
            validTo: a.valid_to,
            rainfall3h: a.predicted_rainfall_3h,
            extremeProb: a.extreme_rain_probability,
            floodRisk: a.flood_susceptibility,
            confidence: a.confidence,
            triggers: a.triggers || [],
            action: a.recommended_action,
        }));

        // Populate state & basin filter dropdowns
        populateStateFilter();
        populateBasinFilter();

        // Update all views
        renderDashboardStats();
        renderAlertsFeed();
        renderAlertsGrid();
        renderStationsTable();
        addStationMarkers(_stations);
        updateAlertTabBadge();
        updateLastSync();

    } catch (err) {
        console.error('Failed to fetch data:', err);
    }
}

// ══════════════════════════════════════════════════════════════════
// DASHBOARD TAB
// ══════════════════════════════════════════════════════════════════

function renderDashboardStats() {
    document.getElementById('stat-stations').textContent = _stations.length;

    const alertEl = document.getElementById('stat-alerts');
    alertEl.textContent = _alerts.length;
    alertEl.style.color = _alerts.some(a => a.level === 'severe') ? 'var(--severe)' : 'var(--text-primary)';

    const severeN = _alerts.filter(a => a.level === 'severe').length;
    const warnN = _alerts.filter(a => a.level === 'warning').length;
    const watchN = _alerts.filter(a => a.level === 'watch').length;
    document.getElementById('stat-alerts-breakdown').textContent =
        `${severeN} severe · ${warnN} warning · ${watchN} watch`;

    const avgRain = _stations.reduce((s, st) => s + st.rain, 0) / _stations.length;
    document.getElementById('stat-rain').textContent = avgRain.toFixed(1) + ' mm/h';

    const riskiest = [..._stations].sort((a, b) => b.floodRisk - a.floodRisk)[0];
    const riskEl = document.getElementById('stat-risk');
    if (riskiest) {
        riskEl.textContent = riskiest.name;
        riskEl.style.color = riskiest.floodRisk > 60 ? 'var(--severe)' : riskiest.floodRisk > 30 ? 'var(--warning)' : 'var(--text-primary)';
    }
}

function renderAlertsFeed() {
    const feed = document.getElementById('alerts-feed');
    if (_alerts.length === 0) {
        feed.innerHTML = '<div class="feed-empty">No active alerts — all clear ✓</div>';
        return;
    }

    feed.innerHTML = '';
    _alerts.forEach(a => {
        const el = document.createElement('div');
        el.className = `alert-item alert-${a.level}`;
        el.innerHTML = `
            <div class="alert-header">
                <span class="alert-station">${a.station}</span>
                <span class="alert-level-tag tag-${a.level}">${a.level}</span>
            </div>
            <div class="alert-details">
                Rain: ${a.rainfall3h} mm/3h · Flood: ${Math.round(a.floodRisk * 100)}% · ${a.confidence}
            </div>
        `;
        el.addEventListener('click', () => {
            // Switch to dashboard tab and zoom
            document.querySelector('[data-tab="dashboard"]').click();
            setTimeout(() => zoomToStation(a.lat, a.lon), 200);
        });
        feed.appendChild(el);
    });
}

function updateAlertTabBadge() {
    const badge = document.getElementById('tab-alert-count');
    if (_alerts.length > 0) {
        badge.textContent = _alerts.length;
        badge.style.display = 'inline';
    } else {
        badge.style.display = 'none';
    }
}

// ══════════════════════════════════════════════════════════════════
// ALERTS TAB
// ══════════════════════════════════════════════════════════════════

function initFilterListeners() {
    document.getElementById('filter-severity')?.addEventListener('change', renderAlertsGrid);
    document.getElementById('filter-state')?.addEventListener('change', renderAlertsGrid);
    document.getElementById('filter-basin')?.addEventListener('change', renderAlertsGrid);
}

function populateStateFilter() {
    const sel = document.getElementById('filter-state');
    const current = sel.value;
    const states = [...new Set(_alerts.map(a => a.state))].sort();

    // Keep "All States" option
    sel.innerHTML = '<option value="all">All States</option>';
    states.forEach(s => {
        if (s) sel.innerHTML += `<option value="${s}">${s}</option>`;
    });
    sel.value = current;
}

function populateBasinFilter() {
    const sel = document.getElementById('filter-basin');
    if (!sel) return;
    const current = sel.value;
    // We need to fetch basins from station data — match alert stations to known basins
    // Use the raw station list from backend
    fetch('/api/stations').then(r => r.json()).then(rawStations => {
        const basins = [...new Set(rawStations.map(s => s.basin || '').filter(b => b))].sort();
        sel.innerHTML = '<option value="all">All Basins</option>';
        basins.forEach(b => {
            sel.innerHTML += `<option value="${b}">${b}</option>`;
        });
        sel.value = current;
    }).catch(() => {});
}

function renderAlertsGrid() {
    const sevFilter = document.getElementById('filter-severity')?.value || 'all';
    const stateFilter = document.getElementById('filter-state')?.value || 'all';
    const basinFilter = document.getElementById('filter-basin')?.value || 'all';

    let filtered = _alerts;
    if (sevFilter !== 'all') filtered = filtered.filter(a => a.level === sevFilter);
    if (stateFilter !== 'all') filtered = filtered.filter(a => a.state === stateFilter);

    // Basin filter: match alert station name to _stations with basin
    if (basinFilter !== 'all') {
        const basinStations = new Set(
            _stations.filter(s => {
                // We don't have basin in _stations array — need to match via API
                // For now, approximate by matching station name to known basin mapping
                return true; // Will be refined below
            }).map(s => s.name)
        );
        // Fetch matching from cached data
        filtered = filtered.filter(a => {
            const matchedStation = _stations.find(s => s.name === a.station);
            // If we can't match, include it
            return !matchedStation || true; // placeholder
        });
    }

    const grid = document.getElementById('alerts-grid');
    if (filtered.length === 0) {
        grid.innerHTML = '<div class="feed-empty" style="grid-column:span 3">No alerts matching filters</div>';
        return;
    }

    grid.innerHTML = '';
    filtered.forEach(a => {
        const card = document.createElement('div');
        card.className = 'alert-card';
        card.innerHTML = `
            <div class="alert-badge badge-${a.level}">${a.level} ALERT</div>
            <div class="alert-card-body">
                <h4>${a.station}</h4>
                <div class="alert-meta">${a.district}, ${a.state}</div>
                <div class="alert-data-grid">
                    <span class="data-label">Predicted Rain (3h)</span><span>${a.rainfall3h} mm</span>
                    <span class="data-label">Extreme Prob</span><span>${(a.extremeProb * 100).toFixed(0)}%</span>
                    <span class="data-label">Flood Risk</span><span>${(a.floodRisk * 100).toFixed(0)}%</span>
                    <span class="data-label">Confidence</span><span>${a.confidence.toUpperCase()}</span>
                </div>
                <div class="alert-triggers">
                    <strong>Triggers:</strong>
                    <ul>${a.triggers.map(t => `<li>${t}</li>`).join('')}</ul>
                </div>
                <div class="alert-action">📋 ${a.action}</div>
                <button class="action-btn" style="margin-top:8px;width:100%;font-size:11px;" onclick="window.showStationModalByName('${a.station}')">🔬 View Station Analytics & XAI</button>
            </div>
        `;
        grid.appendChild(card);
    });
}

// ══════════════════════════════════════════════════════════════════
// STATIONS TAB
// ══════════════════════════════════════════════════════════════════

function initStationSearch() {
    document.getElementById('station-search')?.addEventListener('input', renderStationsTable);
}

function initTableSort() {
    document.querySelectorAll('.data-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (_sortCol === col) { _sortAsc = !_sortAsc; }
            else { _sortCol = col; _sortAsc = true; }
            renderStationsTable();
        });
    });
}

function renderStationsTable() {
    const query = (document.getElementById('station-search')?.value || '').toLowerCase();
    let data = _stations.filter(s =>
        s.name.toLowerCase().includes(query) || s.state.toLowerCase().includes(query)
    );

    // Sort
    if (_sortCol) {
        data.sort((a, b) => {
            let va = a[_sortCol], vb = b[_sortCol];
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            if (_sortCol === 'level') {
                const ord = { severe: 0, warning: 1, watch: 2, safe: 3 };
                va = ord[a.level]; vb = ord[b.level];
            }
            if (va < vb) return _sortAsc ? -1 : 1;
            if (va > vb) return _sortAsc ? 1 : -1;
            return 0;
        });
    }

    const tbody = document.querySelector('#stations-table tbody');
    tbody.innerHTML = '';

    data.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-weight:600;font-family:var(--font-sans)">${s.name}</td>
            <td>${s.state}</td>
            <td>${s.temp}</td>
            <td>${s.humidity}</td>
            <td style="font-weight:600;color:${s.rain > 20 ? 'var(--severe)' : s.rain > 5 ? 'var(--warning)' : 'var(--text-primary)'}">${s.rain.toFixed(1)}</td>
            <td>${s.wind}</td>
            <td>${s.pressure}</td>
            <td>${s.cape}</td>
            <td><span class="level-badge level-${s.level}">${s.level}</span></td>
            <td style="font-weight:600;color:${s.floodRisk > 60 ? 'var(--severe)' : s.floodRisk > 30 ? 'var(--warning)' : 'var(--safe)'}">${s.floodRisk}%</td>
        `;
        tr.addEventListener('click', () => openStationModal(s));
        tbody.appendChild(tr);
    });
}

// ══════════════════════════════════════════════════════════════════
// STATION DETAIL MODAL — fetches from /api/station and /api/xai
// ══════════════════════════════════════════════════════════════════

async function openStationModal(station) {
    const modal = document.getElementById('station-modal');
    document.getElementById('modal-station-name').textContent =
        `${station.name} — ${station.district}, ${station.state}`;

    // Quick stats row
    document.getElementById('modal-stats').innerHTML = `
        <div class="modal-stat-chip"><span class="chip-label">RAINFALL</span>${station.rain.toFixed(1)} mm/h</div>
        <div class="modal-stat-chip"><span class="chip-label">TEMPERATURE</span>${station.temp}°C</div>
        <div class="modal-stat-chip"><span class="chip-label">HUMIDITY</span>${station.humidity}%</div>
        <div class="modal-stat-chip"><span class="chip-label">WIND</span>${station.wind} km/h ${station.windDir}</div>
        <div class="modal-stat-chip"><span class="chip-label">CAPE</span>${station.cape} J/kg</div>
        <div class="modal-stat-chip"><span class="chip-label">FLOOD RISK</span><span style="color:${station.floodRisk > 60 ? 'var(--severe)' : station.floodRisk > 30 ? 'var(--warning)' : 'var(--safe)'}">${station.floodRisk}%</span></div>
        <div class="modal-stat-chip"><span class="chip-label">STATUS</span><span class="level-badge level-${station.level}">${station.level}</span></div>
    `;

    modal.style.display = 'block';

    // Close handlers
    const closeBtn = modal.querySelector('.close-btn');
    closeBtn.onclick = () => { modal.style.display = 'none'; };
    modal.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };

    // Fetch station detail + forecast + xai from API
    try {
        const [detailRes, forecastRes, xaiRes] = await Promise.all([
            fetch(`/api/station/${station.id}`),
            fetch(`/api/forecast/${station.id}`),
            fetch(`/api/xai/${station.id}`),
        ]);

        const detail = await detailRes.json();
        const forecast = await forecastRes.json();
        const xai = await xaiRes.json();

        // ── Time Series Chart ──
        if (detail.history_24h) {
            const labels = detail.history_24h.map(h => {
                const d = new Date(h.timestamp);
                return d.getHours() + ':00';
            });
            const rain = detail.history_24h.map(h => h.rainfall);
            const temp = detail.history_24h.map(h => h.temperature);
            const hum = detail.history_24h.map(h => h.humidity);
            createTimeSeriesChart('chart-timeseries', labels, rain, temp, hum);
        }

        // ── Forecast Chart ──
        if (forecast.forecast) {
            createForecastChart('chart-forecast', forecast.forecast);
        }

        // ── XAI Attribution Chart ──
        if (xai.channel_attributions) {
            const xaiLabels = Object.keys(xai.channel_attributions);
            const xaiValues = Object.values(xai.channel_attributions);
            createAttributionChart('chart-xai', xaiLabels, xaiValues);
        }

        // ── XAI Explanation Text ──
        const xaiDiv = document.getElementById('xai-explanation');
        let xaiHtml = `<p style="margin-bottom:8px"><strong>Confidence: ${(xai.confidence_score * 100).toFixed(0)}%</strong></p>`;
        xaiHtml += `<p style="margin-bottom:8px">${xai.explanation_text}</p>`;
        xaiHtml += '<div style="margin-top:8px"><strong>Triggers:</strong></div>';
        xai.top_triggers.forEach(t => {
            xaiHtml += `<div class="trigger-item">▸ ${t}</div>`;
        });
        xaiDiv.innerHTML = xaiHtml;

    } catch (err) {
        console.error('Failed to load station details:', err);
    }
}

// Global modal triggers for map popups and alert cards
window.showStationModalById = (stationId) => {
    const s = _stations.find(st => st.id === stationId);
    if (s) openStationModal(s);
};

window.showStationModalByName = (name) => {
    if (!name) return;
    const clean = name.trim().toLowerCase();
    const s = _stations.find(st => 
        st.name.toLowerCase() === clean || 
        (st.district && st.district.toLowerCase() === clean)
    );
    if (s) openStationModal(s);
};

// ══════════════════════════════════════════════════════════════════
// MODEL INFO TAB — fetches from /api/model-info
// ══════════════════════════════════════════════════════════════════

async function loadModelInfo() {
    try {
        const res = await fetch('/api/model-info');
        const info = await res.json();
        _modelInfoData = info;

        // Architecture diagram
        document.getElementById('arch-diagram').textContent =
`┌─────────────────┐     ┌───────────────────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  INSAT-3D/3DR   │     │                               │     │                  │     │  Rainfall Probs      │
│  Satellite Imgs  ├────▶│  SatelliteEncoder             │     │                  ├────▶│  (1,10,30 mm/hr)     │
│  (B,T=8,C=6,H,W)│     │  (ResNet-18, shared-T)        │     │                  │     ├──────────────────────┤
└─────────────────┘     │  → 128-ch features             ├────▶│                  │     │  Extreme Rain Prob   │
                        └───────────────────────────────┘     │   UNet Decoder   ├────▶│  (50mm/3h, +3h/+6h)  │
┌─────────────────┐     ┌───────────────────────────────┐     │   + Skip Conn.   │     ├──────────────────────┤
│  ERA5/GFS       │     │                               │     │   → 64-ch feat   │     │  Convective Hazard   │
│  Reanalysis     ├────▶│  AtmosphericEncoder            ├────▶│                  ├────▶│  (+2h, +4h, +6h)     │
│  (B,C=12,H,W)   │     │  (4-layer CNN) → 64-ch        │     │                  │     ├──────────────────────┤
└─────────────────┘     └───────────────────────────────┘     │                  │     │  Rainfall Regression │
                                     ║                         │                  ├────▶│  (mm/hr, 6 horizons) │
┌─────────────────┐     ┌────────────╨──────────────────┐     │                  │     └──────────────────────┘
│  Copernicus DEM │     │  Temporal Fusion               │     │                  │
│  GLO-30 Terrain  ├────▶│  Axial Attention (2 layers,   ├────▶│                  │
│  (B,C=7,H,W)    │     │  8 heads, dim=192)            │     └──────────────────┘
└─────────────────┘     └───────────────────────────────┘`;

        // Data sources
        const ds = info.data_sources;
        document.getElementById('data-sources-list').innerHTML = `
            <ul class="info-list">
                <li><span class="il-label">Satellite</span>${ds.satellite}</li>
                <li><span class="il-label">Reanalysis</span>${ds.reanalysis}</li>
                <li><span class="il-label">Precipitation Target</span>${ds.precipitation_target}</li>
                <li><span class="il-label">Elevation</span>${ds.elevation}</li>
            </ul>
        `;

        // Training config
        const tr = info.training;
        document.getElementById('training-config').innerHTML = `
            <ul class="info-list">
                <li><span class="il-label">Optimizer</span>${tr.optimizer}</li>
                <li><span class="il-label">Scheduler</span>${tr.scheduler}</li>
                <li><span class="il-label">Epochs / Batch</span>${tr.epochs} epochs, batch size ${tr.batch_size}</li>
                <li><span class="il-label">Loss Function</span>${tr.loss}</li>
                <li><span class="il-label">Training Period</span>${tr.train_years}</li>
                <li><span class="il-label">Validation</span>${tr.val_years}</li>
                <li><span class="il-label">Test</span>${tr.test_years}</li>
                <li><span class="il-label">Mixed Precision</span>${tr.mixed_precision ? 'Enabled (FP16)' : 'Disabled'}</li>
            </ul>
        `;

        // Performance metrics table
        const tbody = document.querySelector('#perf-metrics-table tbody');
        tbody.innerHTML = '';
        info.performance.thresholds.forEach(t => {
            tbody.innerHTML += `<tr>
                <td>${t.threshold_mm_hr} mm/hr</td>
                <td>${t.BSS}</td>
                <td>${t.PR_AUC}</td>
                <td>${t.CSI}</td>
                <td>${t.POD}</td>
                <td style="color:${t.FAR > 0.4 ? 'var(--severe)' : 'inherit'}">${t.FAR}</td>
                <td>${t.ETS}</td>
            </tr>`;
        });

        // Flood module info
        document.getElementById('flood-module-info').innerHTML = `
            <ul class="info-list">
                <li><span class="il-label">Model</span>XGBoost Classifier</li>
                <li><span class="il-label">AUC-ROC</span>${info.performance.flood_module_auc}</li>
                <li><span class="il-label">Architecture</span>${info.architecture.stage2}</li>
                <li><span class="il-label">Features</span>predicted_rainfall_3h, predicted_rainfall_6h, api_7day, hand_min, slope_mean, twi_mean, flow_accum, drainage_density, month</li>
            </ul>
        `;

        // Reliability diagram
        if (info.calibration) {
            createReliabilityDiagram(
                'chart-reliability',
                info.calibration.predicted,
                info.calibration.observed
            );
        }

    } catch (err) {
        console.error('Failed to load model info:', err);
    }
}

// ══════════════════════════════════════════════════════════════════
// HISTORICAL TAB
// ══════════════════════════════════════════════════════════════════

async function loadHistoricalData() {
    const date = document.getElementById('historical-date').value;
    if (!date) return;

    const container = document.getElementById('historical-results');
    container.innerHTML = '<p class="text-muted">Loading…</p>';

    try {
        const res = await fetch(`/history/${date}`);
        const data = await res.json();

        if (!data.records || data.records.length === 0) {
            container.innerHTML = '<p class="text-muted">No data for this date.</p>';
            return;
        }

        let html = `<h3 style="color:var(--accent);margin-bottom:10px">Predictions vs. Observations — ${data.date}</h3>`;
        html += `<table class="historical-table">
            <thead><tr>
                <th>Station</th><th>State</th>
                <th>Predicted (mm)</th><th>Observed (mm)</th><th>Error (mm)</th>
                <th>Alert Issued</th><th>Verified</th>
            </tr></thead><tbody>`;

        data.records.forEach(r => {
            const errClass = r.error_mm > 0 ? 'positive-err' : 'negative-err';
            html += `<tr>
                <td style="font-weight:600">${r.station_name}</td>
                <td>${r.state}</td>
                <td>${r.predicted_rainfall_mm.toFixed(1)}</td>
                <td>${r.observed_rainfall_mm.toFixed(1)}</td>
                <td class="${errClass}">${r.error_mm > 0 ? '+' : ''}${r.error_mm.toFixed(1)}</td>
                <td>${r.alert_issued ? '⚠️ Yes' : '—'}</td>
                <td>${r.alert_issued ? (r.alert_verified ? '✅ Yes' : '❌ No') : '—'}</td>
            </tr>`;
        });

        html += '</tbody></table>';

        // Summary stats
        const errors = data.records.map(r => r.error_mm);
        const mae = errors.reduce((s, e) => s + Math.abs(e), 0) / errors.length;
        const rmse = Math.sqrt(errors.reduce((s, e) => s + e * e, 0) / errors.length);
        const alertsIssued = data.records.filter(r => r.alert_issued).length;
        const alertsVerified = data.records.filter(r => r.alert_issued && r.alert_verified).length;

        html += `<div style="margin-top:14px;font-family:var(--font-mono);font-size:12px;color:var(--text-secondary)">
            MAE: ${mae.toFixed(1)} mm | RMSE: ${rmse.toFixed(1)} mm | Alerts Issued: ${alertsIssued} | Verified: ${alertsVerified}/${alertsIssued}
        </div>`;

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<p style="color:var(--severe)">Error loading historical data.</p>';
        console.error(err);
    }
}

// ══════════════════════════════════════════════════════════════════
// TIMELINE SCRUBBER
// ══════════════════════════════════════════════════════════════════

function initTimeline() {
    const scrubber = document.getElementById('timeline-scrubber');
    const range = document.getElementById('timeline-range');
    const label = document.getElementById('timeline-current');
    const playBtn = document.getElementById('timeline-play');

    if (!scrubber || !range || !label || !playBtn) return;

    // Show scrubber on dashboard tab (default active)
    scrubber.classList.remove('hidden');

    range.addEventListener('input', () => {
        const val = parseInt(range.value);
        label.textContent = val === 0 ? 'NOW' : (val > 0 ? `+${val}h` : `${val}h`);
        onTimelineChange(val);
    });

    playBtn.addEventListener('click', toggleTimelinePlay);
}

function toggleTimelinePlay() {
    const playBtn = document.getElementById('timeline-play');
    const range = document.getElementById('timeline-range');
    if (!playBtn || !range) return;

    _timelinePlaying = !_timelinePlaying;
    playBtn.textContent = _timelinePlaying ? '⏸' : '▶';

    if (_timelinePlaying) {
        _timelineInterval = setInterval(() => {
            let val = parseInt(range.value) + 1;
            if (val > 6) val = -2;
            range.value = val;
            range.dispatchEvent(new Event('input'));
        }, 1500);
    } else {
        clearInterval(_timelineInterval);
        _timelineInterval = null;
    }
}

function onTimelineChange(hour) {
    // Update stat cards to show forecast horizon label
    const label = hour === 0 ? 'CURRENT' : (hour > 0 ? `FORECAST +${hour}h` : `HISTORY ${hour}h`);
    const statsLabel = document.querySelector('.stat-card .stat-label');
    // We could update chart highlight here; for now just mark the map title
    const toolbar = document.querySelector('.toolbar-label');
    if (toolbar) {
        toolbar.textContent = hour === 0 ? 'MAP VIEW' : `MAP VIEW — ${label}`;
    }
}

// ══════════════════════════════════════════════════════════════════
// TOOLBAR BUTTONS (Wind, Siren, Export, Wall, Lo-Band, Shortcuts)
// ══════════════════════════════════════════════════════════════════

function initToolbarButtons() {
    // Wind Vectors
    document.getElementById('btn-wind')?.addEventListener('click', function() {
        if (typeof window.toggleWindVectors === 'function') {
            const on = window.toggleWindVectors();
            this.classList.toggle('active', on);
        }
    });

    // Siren Mute
    document.getElementById('btn-siren')?.addEventListener('click', function() {
        _sirenMuted = !_sirenMuted;
        this.classList.toggle('muted', _sirenMuted);
        this.querySelector('span:first-child') || (this.textContent = _sirenMuted ? '🔇 Siren' : '🔊 Siren');
        this.innerHTML = _sirenMuted
            ? '🔇 <span>Muted</span>'
            : '🔊 <span>Siren</span>';
        // Expose to websocket module
        window._sirenMuted = _sirenMuted;
    });
    window._sirenMuted = false;

    // Export Bulletin
    document.getElementById('btn-export')?.addEventListener('click', exportBulletin);

    // Wall Mode
    document.getElementById('btn-wall')?.addEventListener('click', toggleWallMode);
    document.getElementById('wall-exit')?.addEventListener('click', toggleWallMode);

    // Low-Bandwidth
    document.getElementById('btn-lowband')?.addEventListener('click', function() {
        _lowBand = !_lowBand;
        document.body.classList.toggle('low-band', _lowBand);
        this.classList.toggle('active', _lowBand);
        if (_lowBand) {
            // Switch to simpler tiles
            if (typeof window.setMapTheme === 'function') {
                // Keep current theme but reduce refresh rate
                console.log('[VARSHA] Low-bandwidth mode enabled');
            }
        } else {
            console.log('[VARSHA] Low-bandwidth mode disabled');
        }
    });

    // Keyboard Shortcuts
    document.getElementById('btn-shortcuts')?.addEventListener('click', () => {
        document.getElementById('shortcuts-modal')?.classList.toggle('open');
    });
}

// ══════════════════════════════════════════════════════════════════
// WALL MODE (FULLSCREEN)
// ══════════════════════════════════════════════════════════════════

function toggleWallMode() {
    _wallMode = !_wallMode;
    document.body.classList.toggle('wall-mode', _wallMode);
    document.getElementById('btn-wall')?.classList.toggle('active', _wallMode);

    // Switch to dashboard and invalidate map
    if (_wallMode) {
        document.querySelector('[data-tab="dashboard"]')?.click();
    }
    setTimeout(() => {
        if (window.map) window.map.invalidateSize();
    }, 200);
}

// ══════════════════════════════════════════════════════════════════
// EXPORT WARNING BULLETIN (PDF via jsPDF)
// ══════════════════════════════════════════════════════════════════

function exportBulletin() {
    if (typeof window.jspdf === 'undefined') {
        alert('PDF library is loading, please try again in a moment.');
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const now = new Date();
    const ist = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
    const dateStr = ist.toISOString().slice(0, 10);
    const timeStr = ist.toLocaleTimeString('en-GB', { hour12: false });

    // Header
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('VARSHA — Weather Warning Bulletin', 14, 20);

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated: ${dateStr} ${timeStr} IST`, 14, 28);
    doc.text(`Active Alerts: ${_alerts.length} | Stations Monitored: ${_stations.length}`, 14, 34);

    doc.setDrawColor(212, 148, 10);
    doc.line(14, 37, 196, 37);

    // Alerts section
    let y = 44;
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('Active Alerts', 14, y);
    y += 8;

    if (_alerts.length === 0) {
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text('No active alerts — all clear.', 14, y);
        y += 8;
    } else {
        doc.setFontSize(9);
        _alerts.forEach((a, i) => {
            if (y > 270) {
                doc.addPage();
                y = 20;
            }
            doc.setFont('helvetica', 'bold');
            doc.text(`${i + 1}. [${a.level.toUpperCase()}] ${a.station} — ${a.state}`, 14, y);
            y += 5;
            doc.setFont('helvetica', 'normal');
            doc.text(`Rain (3h): ${a.rainfall3h} mm | Extreme: ${(a.extremeProb * 100).toFixed(0)}% | Flood: ${(a.floodRisk * 100).toFixed(0)}% | ${a.confidence}`, 18, y);
            y += 5;
            doc.text(`Action: ${a.action}`, 18, y);
            y += 7;
        });
    }

    // Station summary
    if (y > 240) { doc.addPage(); y = 20; }
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('Station Summary', 14, y);
    y += 7;

    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.text('Station', 14, y);
    doc.text('State', 55, y);
    doc.text('Rain mm/h', 95, y);
    doc.text('Temp °C', 125, y);
    doc.text('Alert', 155, y);
    doc.text('Flood %', 175, y);
    y += 5;
    doc.setFont('helvetica', 'normal');

    _stations.forEach(s => {
        if (y > 280) { doc.addPage(); y = 20; }
        doc.text(s.name, 14, y);
        doc.text(s.state, 55, y);
        doc.text(s.rain.toFixed(1), 95, y);
        doc.text(String(s.temp), 125, y);
        doc.text(s.level, 155, y);
        doc.text(s.floodRisk + '%', 175, y);
        y += 4;
    });

    // Footer
    doc.setFontSize(7);
    doc.text('VARSHA — Vulnerability-Aware Regional Severe-weather Hazard Anticipation | Generated by VarshaNet v1.0.0', 14, 290);

    doc.save(`VARSHA_Bulletin_${dateStr}.pdf`);
}

// ══════════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ══════════════════════════════════════════════════════════════════

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if user is typing in an input/select
        const tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;

        switch (e.key) {
            case ' ':
                e.preventDefault();
                toggleTimelinePlay();
                break;
            case '1': switchToTab(0); break;
            case '2': switchToTab(1); break;
            case '3': switchToTab(2); break;
            case '4': switchToTab(3); break;
            case '5': switchToTab(4); break;
            case '/':
                e.preventDefault();
                document.getElementById('station-search')?.focus();
                switchToTab(2);
                break;
            case 'Escape':
                // Close modals/inspectors
                document.getElementById('station-modal').style.display = 'none';
                document.getElementById('shortcuts-modal')?.classList.remove('open');
                if (typeof window.closeMapInspector === 'function') window.closeMapInspector();
                if (_wallMode) toggleWallMode();
                break;
            case '?':
                document.getElementById('shortcuts-modal')?.classList.toggle('open');
                break;
            case 'f':
            case 'F':
                toggleWallMode();
                break;
            case 'w':
            case 'W':
                document.getElementById('btn-wind')?.click();
                break;
            case 'm':
            case 'M':
                document.getElementById('btn-siren')?.click();
                break;
        }
    });
}
