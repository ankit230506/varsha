/* ═══════════════════════════════════════════════════════════════
   VARSHA — Leaflet map module
   - Esri Dark / Light tiles with theme switching
   - Station markers with rich popups
   - Heatmap layer toggle
   - Wind vector overlay (animated canvas particles)
   - Click-anywhere map inspector (nearest station)
   ═══════════════════════════════════════════════════════════════ */

let map;
let markersLayer;
let heatmapVisible = false;

const MARKER_COLORS = {
    severe:  '#c62828',
    warning: '#d4690a',
    watch:   '#a68a0a',
    safe:    '#1a8a50',
};

const REGION_BOUNDS = {
    north:     [[26, 72], [36, 82]],
    south:     [[8, 74], [18, 82]],
    east:      [[20, 82], [28, 97]],
    west:      [[18, 68], [26, 76]],
    central:   [[18, 74], [26, 82]],
    northeast: [[22, 88], [28, 97]],
};

let darkTileGroup;
let lightTileGroup;
let currentMapTheme = 'dark';

// Wind vector state
let _windLayer = null;
let _windVisible = false;
let _windAnimFrame = null;
let _cachedStations = [];

function initMap() {
    // Esri Dark Gray Canvas
    const darkBase = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri | VARSHA', maxZoom: 16 }
    );
    const darkRef = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 16 }
    );
    darkTileGroup = L.layerGroup([darkBase, darkRef]);

    // Esri Light Gray Canvas
    const lightBase = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri | VARSHA', maxZoom: 16 }
    );
    const lightRef = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 16 }
    );
    lightTileGroup = L.layerGroup([lightBase, lightRef]);

    const activeTiles = currentMapTheme === 'light' ? lightTileGroup : darkTileGroup;
    markersLayer = L.layerGroup();

    map = L.map('map', {
        center: [22.5, 80.0],
        zoom: 5,
        layers: [activeTiles, markersLayer],
        zoomControl: false,
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Make map globally accessible for tab resize fix
    window.map = map;
    window.setMapTheme = setMapTheme;

    // Region buttons
    document.querySelectorAll('.map-btn[data-region]').forEach(btn => {
        btn.addEventListener('click', () => zoomToRegion(btn.dataset.region));
    });

    // Heatmap toggle
    document.getElementById('toggle-heatmap')?.addEventListener('click', function() {
        heatmapVisible = !heatmapVisible;
        this.classList.toggle('active-layer', heatmapVisible);
        if (markersLayer) {
            markersLayer.eachLayer(marker => {
                if (marker._heatCircle) {
                    if (heatmapVisible) {
                        marker._heatCircle.addTo(map);
                    } else {
                        map.removeLayer(marker._heatCircle);
                    }
                }
            });
        }
    });

    // ── Map click → Inspector ──
    map.on('click', function(e) {
        if (_cachedStations.length === 0) return;
        const nearest = findNearestStation(e.latlng.lat, e.latlng.lng);
        if (nearest) {
            openMapInspector(nearest, e.latlng);
        }
    });
}

// ── Station markers ──

function addStationMarkers(stations) {
    if (!markersLayer) return;
    markersLayer.clearLayers();
    _cachedStations = stations;

    // Remove old heat circles
    if (map) {
        map.eachLayer(layer => {
            if (layer._isHeatCircle) map.removeLayer(layer);
        });
    }

    stations.forEach(st => {
        const color = MARKER_COLORS[st.level] || MARKER_COLORS.safe;
        const isAlert = st.level === 'severe' || st.level === 'warning';
        const radius = st.level === 'severe' ? 9 : st.level === 'warning' ? 7 : 5;

        const marker = L.circleMarker([st.lat, st.lon], {
            radius: radius,
            fillColor: color,
            color: isAlert ? color : '#333',
            weight: isAlert ? 2 : 1,
            opacity: 1,
            fillOpacity: 0.85,
        });

        // Rainfall heatmap circle (hidden by default)
        if (st.rain > 2) {
            const heatRadius = Math.min(50000, st.rain * 1500);
            const heatCircle = L.circle([st.lat, st.lon], {
                radius: heatRadius,
                fillColor: color,
                fillOpacity: 0.12,
                color: 'transparent',
                interactive: false,
            });
            heatCircle._isHeatCircle = true;
            marker._heatCircle = heatCircle;
            if (heatmapVisible) heatCircle.addTo(map);
        }

        // Rich popup
        const floodBar = Math.min(100, st.floodRisk);
        const floodColor = floodBar > 60 ? MARKER_COLORS.severe : floodBar > 30 ? MARKER_COLORS.warning : MARKER_COLORS.safe;

        marker.bindPopup(`
            <div style="min-width:200px">
                <div style="font-weight:700;font-size:14px;color:#d4940a;margin-bottom:4px">${st.name}</div>
                <div style="font-size:11px;color:#6b6b6b;margin-bottom:6px">${st.state} — ${st.district || ''}</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.7">
                    <div>🌧 Rain: <b>${st.rain.toFixed(1)} mm/h</b></div>
                    <div>🌡 Temp: ${st.temp}°C | 💧 Humidity: ${st.humidity}%</div>
                    <div>💨 Wind: ${st.wind} km/h | ⛅ Pressure: ${st.pressure} hPa</div>
                    <div>⚡ CAPE: ${st.cape} J/kg</div>
                </div>
                <div style="margin-top:6px">
                    <div style="font-size:10px;color:#6b6b6b;margin-bottom:2px">FLOOD RISK: ${st.floodRisk}%</div>
                    <div style="background:#2a2a35;height:6px;width:100%">
                        <div style="background:${floodColor};height:100%;width:${floodBar}%"></div>
                    </div>
                </div>
                <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;">
                    <span style="display:inline-block;padding:2px 8px;background:${color};color:${st.level === 'watch' ? '#111' : '#fff'};font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">${st.level}</span>
                    <button onclick="window.showStationModalById('${st.id}')" style="background:#2a2a35;border:1px solid #3a3a48;color:#d4940a;font-size:10px;padding:3px 8px;cursor:pointer;font-family:'Inter',sans-serif;font-weight:600;">Analytics & XAI →</button>
                </div>
            </div>
        `, { className: 'custom-popup', maxWidth: 280 });

        markersLayer.addLayer(marker);
    });

    // Refresh wind vectors if visible
    if (_windVisible) {
        _drawWindOverlay();
    }
}

function zoomToStation(lat, lon) {
    if (map) {
        map.flyTo([lat, lon], 10, { duration: 1.2 });
    }
}

function zoomToRegion(region) {
    if (!map || !REGION_BOUNDS[region]) return;
    map.flyToBounds(REGION_BOUNDS[region], { duration: 0.8, padding: [20, 20] });
}

function setMapTheme(theme) {
    currentMapTheme = theme;
    if (!map || !darkTileGroup || !lightTileGroup) return;
    if (theme === 'light') {
        if (map.hasLayer(darkTileGroup)) map.removeLayer(darkTileGroup);
        if (!map.hasLayer(lightTileGroup)) map.addLayer(lightTileGroup);
    } else {
        if (map.hasLayer(lightTileGroup)) map.removeLayer(lightTileGroup);
        if (!map.hasLayer(darkTileGroup)) map.addLayer(darkTileGroup);
    }
}

// ═══════════════════════════════════════════════════════════════
// WIND VECTOR OVERLAY — animated particles on a canvas layer
// ═══════════════════════════════════════════════════════════════

const WIND_DIR_MAP = {
    N: 0, NE: 45, E: 90, SE: 135,
    S: 180, SW: 225, W: 270, NW: 315,
};

function toggleWindVectors() {
    _windVisible = !_windVisible;
    if (_windVisible) {
        _drawWindOverlay();
    } else {
        _removeWindOverlay();
    }
    return _windVisible;
}

function _removeWindOverlay() {
    if (_windAnimFrame) {
        cancelAnimationFrame(_windAnimFrame);
        _windAnimFrame = null;
    }
    if (_windLayer && map) {
        map.removeLayer(_windLayer);
        _windLayer = null;
    }
}

function _drawWindOverlay() {
    _removeWindOverlay();
    if (!map || _cachedStations.length === 0) return;

    // Create a simple SVG-based wind arrow overlay using Leaflet markers
    const arrows = [];
    _cachedStations.forEach(st => {
        const deg = WIND_DIR_MAP[st.windDir] || 0;
        const speed = st.wind || 0;
        const scale = Math.min(1.6, 0.4 + speed / 40);
        const opacity = Math.min(0.9, 0.3 + speed / 60);

        // SVG arrow pointing up (north=0°), rotated by wind direction
        const svgIcon = L.divIcon({
            className: 'wind-arrow-icon',
            html: `<div style="transform:rotate(${deg}deg);opacity:${opacity};pointer-events:none;">
                <svg width="24" height="24" viewBox="0 0 24 24" style="transform:scale(${scale})">
                    <path d="M12 2 L15 10 L12 8 L9 10 Z" fill="${currentMapTheme === 'light' ? '#334155' : '#94a3b8'}" stroke="none"/>
                    <line x1="12" y1="8" x2="12" y2="20" stroke="${currentMapTheme === 'light' ? '#334155' : '#94a3b8'}" stroke-width="1.5" opacity="0.6"/>
                </svg>
            </div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        });

        arrows.push(L.marker([st.lat, st.lon], {
            icon: svgIcon,
            interactive: false,
            zIndexOffset: -100,
        }));
    });

    _windLayer = L.layerGroup(arrows);
    _windLayer.addTo(map);
}

window.toggleWindVectors = toggleWindVectors;

// ═══════════════════════════════════════════════════════════════
// MAP CLICK INSPECTOR — find nearest station
// ═══════════════════════════════════════════════════════════════

function findNearestStation(lat, lng) {
    if (_cachedStations.length === 0) return null;
    let best = null;
    let bestDist = Infinity;
    _cachedStations.forEach(st => {
        const d = haversine(lat, lng, st.lat, st.lon);
        if (d < bestDist) {
            bestDist = d;
            best = st;
        }
    });
    return best;
}

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371; // km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function openMapInspector(station, clickLatLng) {
    const panel = document.getElementById('map-inspector');
    const title = document.getElementById('inspector-title');
    const body = document.getElementById('inspector-body');
    if (!panel || !title || !body) return;

    title.textContent = `📍 ${station.name}`;

    const floodColor = station.floodRisk > 60 ? 'var(--severe)' : station.floodRisk > 30 ? 'var(--warning)' : 'var(--safe)';

    body.innerHTML = `
        <div class="inspector-grid">
            <div><span class="ig-label">CLICKED</span><br>${clickLatLng.lat.toFixed(4)}, ${clickLatLng.lng.toFixed(4)}</div>
            <div><span class="ig-label">NEAREST STATION</span><br>${station.name}, ${station.state}</div>
            <div><span class="ig-label">RAINFALL</span><br><span class="ig-value">${station.rain.toFixed(1)} mm/h</span></div>
            <div><span class="ig-label">TEMPERATURE</span><br><span class="ig-value">${station.temp}°C</span></div>
            <div><span class="ig-label">HUMIDITY</span><br><span class="ig-value">${station.humidity}%</span></div>
            <div><span class="ig-label">WIND</span><br><span class="ig-value">${station.wind} km/h ${station.windDir}</span></div>
            <div><span class="ig-label">PRESSURE</span><br><span class="ig-value">${station.pressure} hPa</span></div>
            <div><span class="ig-label">CAPE</span><br><span class="ig-value">${station.cape} J/kg</span></div>
        </div>
        <div class="inspector-section">
            <h4>Risk Assessment</h4>
            <div class="inspector-grid">
                <div><span class="ig-label">STATUS</span><br><span class="level-badge level-${station.level}" style="font-size:10px">${station.level}</span></div>
                <div><span class="ig-label">FLOOD RISK</span><br><span class="ig-value" style="color:${floodColor}">${station.floodRisk}%</span></div>
                <div><span class="ig-label">EXTREME PROB</span><br><span class="ig-value">${(station.extremeProb * 100).toFixed(0)}%</span></div>
                <div><span class="ig-label">RAIN 1H PROB</span><br><span class="ig-value">${(station.rainProb1h * 100).toFixed(0)}%</span></div>
            </div>
        </div>
        <div class="inspector-section">
            <h4>Forecast Probabilities</h4>
            <div class="inspector-grid">
                <div><span class="ig-label">1H</span><br>${(station.rainProb1h * 100).toFixed(0)}%</div>
                <div><span class="ig-label">3H</span><br>${(station.rainProb3h * 100).toFixed(0)}%</div>
                <div><span class="ig-label">6H</span><br>${(station.rainProb6h * 100).toFixed(0)}%</div>
                <div><span class="ig-label">CLOUD</span><br>${station.cloud}%</div>
            </div>
        </div>
        <div style="margin-top:14px">
            <button class="action-btn" style="width:100%;font-size:11px;" onclick="window.showStationModalById('${station.id}')">🔬 Full Analytics & XAI →</button>
        </div>
    `;

    panel.classList.add('open');
}

function closeMapInspector() {
    const panel = document.getElementById('map-inspector');
    if (panel) panel.classList.remove('open');
}

// Close button
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('inspector-close')?.addEventListener('click', closeMapInspector);
});

window.closeMapInspector = closeMapInspector;
