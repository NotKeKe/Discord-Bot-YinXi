import { parseSRT } from './utils.js';
import { DisplayManager } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialization
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
    let currentUUID = null;
    let currentSrtContent = "";
    let subtitles = [];
    let currentLang = langSelect ? langSelect.value : 'original';

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
            // Immediately fetch with new language
            fetchData();
        });
    }

    // Volume
    display.volumeSlider.addEventListener('input', (e) => {
        const vol = parseFloat(e.target.value);
        audio.volume = vol;
    });

    // Stream Buffering Handlers
    audio.addEventListener('waiting', () => {
        console.log('[Stream] Buffering...');
        display.setBuffering(true);
    });

    audio.addEventListener('playing', () => {
        console.log('[Stream] Playing');
        display.setBuffering(false);
        // Ensure overlay is hidden if it started playing naturally
        if (typeof display.hideAutoplayRequest === 'function') {
            display.hideAutoplayRequest();
        }
    });

    audio.addEventListener('canplay', () => {
        display.setBuffering(false);
    });

    // Audio Progress & Visuals
    const handleProgress = () => {
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
        // Normal playback: use default smooth scroll (false)
        display.highlightSubtitle(subtitles, ct, false);
    };

    audio.addEventListener('timeupdate', handleProgress);
    audio.addEventListener('loadedmetadata', handleProgress);

    // --- 3. Main Logic (Fetch & Update) ---

    async function fetchData() {
        try {
            // Append language parameter
            const response = await fetch(`/player/check_song?guild_id=${GUILD_ID}&lang=${currentLang}`);

            if (response.ok) {
                const data = await response.json();
                updateSong(data);
            } else if (response.status === 404) {
                console.log("Waiting for session to be created...");
            }
        } catch (err) {
            // Ignore network errors
        }
    }

    function startPolling() {
        // Poll server every 5 seconds
        setInterval(fetchData, 5000);
    }

    // Helper to update dropdown options without losing selection if possible
    function updateLanguageList(availableLanguages) {
        if (!langSelect) return;
        if (!availableLanguages || !Array.isArray(availableLanguages)) return;

        // Current selection
        const previousSelection = langSelect.value;

        // Check if options are already correct (simple optimization)
        const currentOptions = Array.from(langSelect.options).map(o => o.value);
        const newOptionsSet = new Set(['original', ...availableLanguages]);

        // If length matches and every option matches, skip DOM update
        if (currentOptions.length === newOptionsSet.size &&
            currentOptions.every(opt => newOptionsSet.has(opt))) {
            return;
        }

        console.log("Updating language list:", availableLanguages);
        langSelect.innerHTML = '';

        // Always add Original first
        const originalOpt = document.createElement('option');
        originalOpt.value = 'original';
        originalOpt.textContent = 'Original';
        langSelect.appendChild(originalOpt);

        // Add others
        availableLanguages.forEach(lang => {
            if (lang === 'original') return; // Skip duplicate
            const opt = document.createElement('option');
            opt.value = lang;
            // Capitalize first letter for display
            opt.textContent = lang.charAt(0).toUpperCase() + lang.slice(1);
            langSelect.appendChild(opt);
        });

        // Restore selection or default to original
        if (newOptionsSet.has(previousSelection)) {
            langSelect.value = previousSelection;
        } else {
            console.log(`Previous language ${previousSelection} not available, switching to original.`);
            langSelect.value = 'original';
            currentLang = 'original'; // Update state
        }
    }

    function updateSong(data) {
        if (!data) return;

        let isNewSong = false;

        // CASE A: NEW SONG (UUID changed)
        if (data.uuid !== currentUUID) {
            console.log("New song detected:", data.uuid);
            currentUUID = data.uuid;
            isNewSong = true; // Mark as new so we skip sync logic this turn
            currentSrtContent = ""; // Reset SRT cache to force render

            // Reset UI
            display.reset();
            display.updateMetadata(data.title, data.subtitle);

            // Update Language Dropdown if provided by backend
            if (data.languages) {
                updateLanguageList(data.languages);
            }

            // Load Audio Stream
            if (data.audio_url) {
                console.log("[Stream] Loading URL:", data.audio_url);
                audio.src = data.audio_url;
                audio.load();

                // Attempt play immediately
                const playPromise = audio.play();

                if (playPromise !== undefined) {
                    playPromise.catch(e => {
                        console.warn("Auto-play blocked initially:", e.name);
                        // If blocked by browser policy, show overlay
                        if (e.name === 'NotAllowedError' || e.name === 'NotSupportedError') {
                            if (typeof display.showAutoplayRequest === 'function') {
                                display.showAutoplayRequest(() => {
                                    // On user click
                                    audio.play().catch(err => console.error("Play failed even after click:", err));
                                });
                            } else {
                                // Fallback if JS cache is stale and method missing
                                console.error("DisplayManager missing showAutoplayRequest. Please hard refresh.");
                                alert("Please tap the screen to enable audio playback.");
                                const unlockAudio = () => {
                                    audio.play();
                                    document.removeEventListener('click', unlockAudio);
                                };
                                document.addEventListener('click', unlockAudio);
                            }
                        }
                    });
                }
            }
        }
        // If same song, still check if languages list updated
        else if (data.languages) {
            updateLanguageList(data.languages);
        }

        // CASE B: Subtitle Content Changed
        if (data.srt_content !== currentSrtContent) {
            console.log("Subtitle content updated.");
            currentSrtContent = data.srt_content;

            if (data.srt_content) {
                subtitles = parseSRT(data.srt_content);
                display.renderSubtitles(subtitles);

                // CRITICAL FIX: Pass 'true' (immediate) because we just replaced the DOM.
                // This prevents the "scroll from top" animation which looks like a jump back in time.
                display.highlightSubtitle(subtitles, audio.currentTime, true);
            } else {
                subtitles = [];
                display.setWaitingState();
            }
        }

        // CASE C: Sync & Playback State
        // CRITICAL FIX: Do NOT run this if we just initialized a new song (isNewSong = true).
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
                // If server implies PLAY, and we are paused, try to resume
                if (audio.paused && audio.readyState >= 2) {
                    const playPromise = audio.play();
                    // Catch errors here too
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

    // Start
    startPolling();
});