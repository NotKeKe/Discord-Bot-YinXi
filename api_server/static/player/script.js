import { parseSRT } from './utils.js';
import { DisplayManager } from './ui.js';

function initApp() {
    console.log("[App] Initializing...");

    const audio = document.getElementById('audio-player');
    const langSelect = document.getElementById('language-select');
    const display = new DisplayManager();

    // Context from Backend
    const context = window.SERVER_CONTEXT || {};
    let GUILD_ID = context.guild_id;

    // --- FALLBACK LOGIC ---
    if (!GUILD_ID || GUILD_ID.includes("{{")) {
        console.warn("Context injection missing. Attempting to parse Guild ID from URL...");
        try {
            const pathSegments = window.location.pathname.split('/');
            const lastSegment = pathSegments.pop() || pathSegments.pop();
            if (lastSegment && lastSegment.includes('_')) {
                GUILD_ID = lastSegment.split('_')[0];
                console.log("Successfully recovered Guild ID from URL:", GUILD_ID);
            }
        } catch (e) {
            console.error("Failed to parse URL for Guild ID", e);
        }
    }

    // App State
    let currentSessionID = null;
    let currentSrtContent = "";
    let subtitles = [];
    let currentLang = langSelect ? langSelect.value : 'original';

    // Sync Offset (in seconds). Positive = Delay Subtitles. Negative = Advance Subtitles.
    let subtitleOffset = 0.0;

    if (!GUILD_ID || GUILD_ID.includes("{{")) {
        console.error("No Guild ID found. Polling disabled.");
        display.updateMetadata("Configuration Error", "Missing Guild ID");
        return;
    }

    // --- 2. Event Listeners ---

    // Language Selection
    if (langSelect) {
        langSelect.addEventListener('change', (e) => {
            currentLang = e.target.value;
            console.log("Language changed to:", currentLang);

            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'set_lang', payload: currentLang }));
            }
        });
    }

    // Volume
    if (display.volumeSlider) {
        display.volumeSlider.addEventListener('input', (e) => {
            const vol = parseFloat(e.target.value);
            audio.volume = vol;
        });
    }

    // NEW: Sync Control Listeners via DisplayManager
    display.bindSyncControls(
        () => { // Decrease offset (Minus)
            subtitleOffset -= 0.1;
            subtitleOffset = Math.round(subtitleOffset * 10) / 10;
            console.log("[Sync] Decrease ->", subtitleOffset);
            display.updateOffsetDisplay(subtitleOffset);

            const adjustedTime = audio.currentTime - subtitleOffset;
            display.highlightSubtitle(subtitles, adjustedTime, false);
        },
        () => { // Increase offset (Plus)
            subtitleOffset += 0.1;
            subtitleOffset = Math.round(subtitleOffset * 10) / 10;
            console.log("[Sync] Increase ->", subtitleOffset);
            display.updateOffsetDisplay(subtitleOffset);

            const adjustedTime = audio.currentTime - subtitleOffset;
            display.highlightSubtitle(subtitles, adjustedTime, false);
        }
    );

    // Stream Buffering Handlers
    audio.addEventListener('waiting', () => {
        display.setBuffering(true);
    });

    audio.addEventListener('playing', () => {
        display.setBuffering(false);
        if (typeof display.hideAutoplayRequest === 'function') {
            display.hideAutoplayRequest();
        }
    });

    audio.addEventListener('canplay', () => {
        display.setBuffering(false);
    });

    // GAPLESS PLAYBACK LOGIC: 
    // Just fetch immediately once when the song ends. No loop.
    audio.addEventListener('ended', () => {
        console.log("[Stream] Track ended. Waiting for server update...");
    });

    // Audio Progress & Visuals
    const handleProgress = () => {
        // If stopped, do nothing
        if (currentSessionID === null) return;

        const ct = audio.currentTime;
        let d = audio.duration;

        if (!Number.isFinite(d)) {
            if (subtitles.length > 0) {
                d = subtitles[subtitles.length - 1].endTime + 2;
            } else {
                d = Infinity;
            }
        }

        display.updateProgress(ct, d);

        // Apply Offset logic
        const adjustedTime = ct - subtitleOffset;

        // Normal playback: use default smooth scroll (false)
        display.highlightSubtitle(subtitles, adjustedTime, false);
    };

    audio.addEventListener('timeupdate', handleProgress);
    audio.addEventListener('loadedmetadata', handleProgress);

    // --- 3. Main Logic (Fetch & Update) ---

    // --- 3. Main Logic (WebSocket & Update) ---

    function stopPlayback() {
        if (currentSessionID !== null) {
            console.log("Session ended. Stopping playback.");
        }

        // Ensure audio is stopped and source cleared
        if (!audio.paused || audio.getAttribute('src')) {
            audio.pause();
            audio.removeAttribute('src');
            audio.load();
        }

        // Explicitly update UI
        display.showStoppedState();
        currentSessionID = null;
    }

    let socket = null;
    let reconnectTimeout = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 10;

    function connectWebSocket() {
        if (socket) {
            socket.close();
            socket = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const uuid = context.uuid || '';
        const userId = context.user_id || '';
        const wsUrl = `${protocol}//${window.location.host}/player/${GUILD_ID}_${uuid}?user_id=${userId}`;

        console.log(`[WS] Connecting to ${wsUrl}... (Attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log("[WS] Connected.");
            reconnectAttempts = 0; // Reset attempts on successful connection
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateSong(data);
            } catch (e) {
                console.error("[WS] Message error:", e);
            }
        };

        socket.onclose = () => {
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000); // Exponential backoff
                console.warn(`[WS] Disconnected. Reconnecting in ${delay / 1000}s...`);
                reconnectAttempts++;
                reconnectTimeout = setTimeout(connectWebSocket, delay);
            } else {
                console.error("[WS] Max reconnect attempts reached. Please refresh the page manually.");
                display.updateMetadata("Connection Lost", "Please refresh the page");
            }
        };

        socket.onerror = (err) => {
            console.error("[WS] Error:", err);
            socket.close();
        };
    }

    function syncState(data) {
        if (!data) return;

        // Sync playback state
        const serverTime = data.current_time;
        if (typeof serverTime === 'number') {
            const localTime = audio.currentTime;
            const diff = Math.abs(localTime - serverTime);
            if (diff >= 5) {
                console.log(`[WS-Sync] Drift ${diff.toFixed(2)}s. Seeking to ${serverTime}s.`);
                if (Number.isFinite(audio.duration) || (audio.seekable && audio.seekable.length > 0)) {
                    audio.currentTime = serverTime;
                }
            }
        }

        const shouldBePaused = (data.is_paused === true);
        if (shouldBePaused) {
            if (!audio.paused) audio.pause();
        } else {
            if (audio.paused && audio.readyState >= 2) {
                audio.play().catch(e => {
                    if (e.name === 'NotAllowedError' && typeof display.showAutoplayRequest === 'function') {
                        display.showAutoplayRequest(() => audio.play());
                    }
                });
            }
        }

        // Update language list if provided
        if (data.languages) {
            updateLanguageList(data.languages);
        }
    }

    function updateLanguageList(availableLanguages) {
        if (!langSelect) return;
        if (!availableLanguages || !Array.isArray(availableLanguages)) return;

        const previousSelection = langSelect.value;
        const currentOptions = Array.from(langSelect.options).map(o => o.value);
        const newOptionsSet = new Set(['original', ...availableLanguages]);

        if (currentOptions.length === newOptionsSet.size &&
            currentOptions.every(opt => newOptionsSet.has(opt))) {
            return;
        }

        console.log("Updating language list:", availableLanguages);
        langSelect.innerHTML = '';

        const originalOpt = document.createElement('option');
        originalOpt.value = 'original';
        originalOpt.textContent = 'Original';
        langSelect.appendChild(originalOpt);

        availableLanguages.forEach(lang => {
            if (lang === 'original') return;
            const opt = document.createElement('option');
            opt.value = lang;
            opt.textContent = lang.charAt(0).toUpperCase() + lang.slice(1);
            langSelect.appendChild(opt);
        });

        if (newOptionsSet.has(previousSelection)) {
            langSelect.value = previousSelection;
        } else {
            console.log(`Previous language ${previousSelection} not available, switching to original.`);
            langSelect.value = 'original';
            currentLang = 'original';
        }
    }

    function updateSong(data) {
        if (!data) return;

        let isNewSong = false;

        // CASE A: NEW SONG (audio_url changed)
        const newAudioUrl = data.audio_url ? (window.location.origin + data.audio_url) : null;

        if (newAudioUrl && newAudioUrl !== audio.src) {
            console.log("New song detected via URL change.");
            isNewSong = true;
            currentSessionID = data.uuid || data.session_id; // Still keep tracking uuid
            currentSrtContent = "";
            subtitles = [];

            // Reset Offset on new song
            subtitleOffset = 0.0;
            display.updateOffsetDisplay(0);

            // Reset UI
            display.reset();
            display.updateMetadata(data.title, data.subtitle);

            // Reset Language Selector to 'Original'
            if (langSelect) {
                langSelect.value = 'original';
                currentLang = 'original';
            }

            if (data.languages) {
                updateLanguageList(data.languages);
            }

            if (data.audio_url) {
                // console.log("[Stream] Loading URL:", data.audio_url);
                audio.src = data.audio_url;
                audio.load();

                const playPromise = audio.play();

                if (playPromise !== undefined) {
                    playPromise.catch(e => {
                        console.warn("Auto-play blocked initially:", e.name);
                        if (e.name === 'NotAllowedError' || e.name === 'NotSupportedError') {
                            if (typeof display.showAutoplayRequest === 'function') {
                                display.showAutoplayRequest(() => {
                                    audio.play().catch(err => console.error("Play failed even after click:", err));
                                });
                            }
                        }
                    });
                }
            }
        } else if (!newAudioUrl) {
            // No active session/song
            stopPlayback();
            return;
        } else if (data.languages) {
            updateLanguageList(data.languages);
        }

        // CASE B: Subtitle Content Changed
        if (data.srt_content !== currentSrtContent) {
            console.log("Subtitle content updated.");
            currentSrtContent = data.srt_content;

            if (data.srt_content) {
                subtitles = parseSRT(data.srt_content);
                display.renderSubtitles(subtitles);

                const adjustedTime = audio.currentTime - subtitleOffset;
                display.highlightSubtitle(subtitles, adjustedTime, true);
            } else {
                subtitles = [];
                display.setWaitingState();
            }
        }

        // CASE C: Sync & Playback State
        if (!isNewSong) {
            syncState(data);
        }
    }

    // Start WebSocket connection
    connectWebSocket();
}

// Module scripts are deferred by default, DOM is usually ready.
// If not, we can check readyState, but direct execution is often fine for modules at end of body.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}