/* ═══════════════════════════════════════════════════════════════
   VARSHA — WebSocket module for real-time alert push
   ═══════════════════════════════════════════════════════════════ */

let _ws = null;
let _reconnectDelay = 5000;

function connectAlertWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = location.host || 'localhost:8000';
    const url = `${proto}//${host}/ws/alerts`;

    try {
        _ws = new WebSocket(url);
    } catch (e) {
        console.warn('WebSocket connection failed, will retry:', e);
        setTimeout(connectAlertWebSocket, _reconnectDelay);
        return;
    }

    _ws.onopen = () => {
        console.log('[WS] Connected to', url);
        _reconnectDelay = 5000; // reset backoff

        // Keep-alive ping every 30s
        const keepAlive = setInterval(() => {
            if (_ws && _ws.readyState === WebSocket.OPEN) {
                _ws.send('ping');
            } else {
                clearInterval(keepAlive);
            }
        }, 30000);
    };

    _ws.onmessage = (event) => {
        try {
            const alert = JSON.parse(event.data);
            onNewRealtimeAlert(alert);
        } catch (e) {
            console.warn('[WS] Bad message:', event.data);
        }
    };

    _ws.onclose = () => {
        console.log(`[WS] Disconnected. Reconnecting in ${_reconnectDelay / 1000}s…`);
        setTimeout(connectAlertWebSocket, _reconnectDelay);
        _reconnectDelay = Math.min(_reconnectDelay * 1.5, 30000); // exponential backoff
    };

    _ws.onerror = (err) => {
        console.warn('[WS] Error:', err);
    };
}

/**
 * Handle an incoming real-time alert from the WebSocket.
 */
function onNewRealtimeAlert(alert) {
    console.log('[WS] New alert:', alert.message);

    // Show toast notification
    showToast(alert);

    // Play alert sound
    playAlertBeep(alert.level);

    // Refresh dashboard data
    if (typeof fetchData === 'function') {
        fetchData();
    }
}

/**
 * Show a toast notification for a new alert.
 */
function showToast(alert) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${alert.level}`;
    toast.innerHTML = `
        <div class="toast-title">${alert.level.toUpperCase()} — ${alert.station_name || alert.location?.district || 'Unknown'}</div>
        <div class="toast-body">${alert.message || 'New weather alert issued'}</div>
    `;
    container.appendChild(toast);

    // Auto-remove after 8 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 8000);
}

/**
 * Play an alert beep using Web Audio API.
 */
function playAlertBeep(level) {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.connect(gain);
        gain.connect(ctx.destination);

        // Different tones for different severity
        osc.type = 'sine';
        if (level === 'severe') {
            osc.frequency.value = 900;
            gain.gain.setValueAtTime(0.15, ctx.currentTime);
        } else if (level === 'warning') {
            osc.frequency.value = 700;
            gain.gain.setValueAtTime(0.1, ctx.currentTime);
        } else {
            osc.frequency.value = 550;
            gain.gain.setValueAtTime(0.07, ctx.currentTime);
        }

        osc.start();
        osc.stop(ctx.currentTime + 0.2);
    } catch (e) {
        // Audio API not available — fail silently
    }
}
