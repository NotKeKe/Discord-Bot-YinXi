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
            fetchData();
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
        console.log("[Stream] Track ended. Fetching next song immediately...");
        fetchData();
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

    async function fetchData() {
        try {
            const response = await fetch(`/player/check_song?guild_id=${GUILD_ID}&session_id=${currentSessionID || ''}&lang=${currentLang}`);
            if (response.ok) {
                const data = await response.json();
                updateSong(data);
            } else if (response.status === 404) {
                // FORCE STOP LOGIC
                // We execute this unconditionally if 404 is returned, to ensure UI is always in sync.
                if (currentSessionID !== null) {
                    console.log("Session ended (404). Stopping playback.");
                }

                // Ensure audio is stopped and source cleared
                if (!audio.paused || audio.getAttribute('src')) {
                    audio.pause();
                    audio.removeAttribute('src');
                    audio.load();
                }

                // Explicitly update UI
                display.showStoppedState();
            }
        } catch (err) {
            // Ignore network errors
        }
    }

    function startPolling() {
        // Poll every 10 seconds
        setInterval(fetchData, 10000);
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

        // CASE A: NEW SONG (SessionID changed)
        if (data.session_id !== currentSessionID) {
            console.log("New song detected:", data.session_id);
            currentSessionID = data.session_id;
            isNewSong = true;
            currentSrtContent = "";
            subtitles = [];

            // Reset Offset on new song
            subtitleOffset = 0.0;
            display.updateOffsetDisplay(0);

            // Reset UI
            display.reset();
            display.updateMetadata(data.title, data.subtitle);

            // Force Reset Language Selector to 'Original'
            if (langSelect) {
                langSelect.innerHTML = '<option value="original" selected>Original</option>';
                langSelect.value = 'original';
                currentLang = 'original';
            }

            if (data.languages) {
                updateLanguageList(data.languages);
            }

            if (data.audio_url) {
                console.log("[Stream] Loading URL:", data.audio_url);
                // Keep audio source logic as requested (Direct URL from provided context)
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
                            } else {
                                console.error("DisplayManager missing showAutoplayRequest.");
                            }
                        }
                    });
                }
            }
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
            const serverTime = data.current_time;
            if (typeof serverTime === 'number') {
                const localTime = audio.currentTime;
                const diff = Math.abs(localTime - serverTime);

                if (diff >= 3) {
                    console.log(`[Sync] Drift ${diff.toFixed(2)}s >= 3s. Seeking to ${serverTime}s.`);
                    if (Number.isFinite(audio.duration) || (audio.seekable && audio.seekable.length > 0)) {
                        audio.currentTime = serverTime;
                    }
                }
            }

            const shouldBePaused = (data.is_paused === true);
            if (shouldBePaused) {
                if (!audio.paused) {
                    audio.pause();
                }
            } else {
                if (audio.paused && audio.readyState >= 2) {
                    const playPromise = audio.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(e => {
                            if (e.name === 'NotAllowedError') {
                                if (typeof display.showAutoplayRequest === 'function') {
                                    display.showAutoplayRequest(() => audio.play());
                                }
                            }
                        });
                    }
                }
            }
        }
    }

    // Start polling immediately
    startPolling();
    // Fetch once on load
    fetchData();
}

// Module scripts are deferred by default, DOM is usually ready.
// If not, we can check readyState, but direct execution is often fine for modules at end of body.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}