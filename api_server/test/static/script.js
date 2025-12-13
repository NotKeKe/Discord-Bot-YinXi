import { parseSRT } from './utils.js';
import { DisplayManager } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialization
    const audio = document.getElementById('audio-player');
    const display = new DisplayManager();

    // Context from Backend
    const context = window.SERVER_CONTEXT || {};
    let GUILD_ID = context.guild_id;

    // --- FALLBACK LOGIC ---
    if (!GUILD_ID || GUILD_ID.includes("{{")) {
        console.warn("Context injection missing. Attempting to parse Guild ID from URL...");
        try {
            const pathSegment = window.location.pathname.split('/').pop();
            if (pathSegment && pathSegment.includes('_')) {
                GUILD_ID = pathSegment.split('_')[0];
                console.log("Successfully recovered Guild ID from URL:", GUILD_ID);
            }
        } catch (e) {
            console.error("Failed to parse URL for Guild ID", e);
        }
    }

    // App State
    let currentUUID = null;
    let subtitles = [];

    if (!GUILD_ID || GUILD_ID.includes("{{")) {
        console.error("No Guild ID found. Polling disabled.");
        display.updateMetadata("Configuration Error", "Missing Guild ID");
        return;
    }

    // --- 2. Event Listeners ---

    // Volume
    display.volumeSlider.addEventListener('input', (e) => {
        const vol = parseFloat(e.target.value);
        audio.volume = vol;
    });

    // Audio Progress & Visuals
    audio.addEventListener('timeupdate', () => {
        const ct = audio.currentTime;
        const d = audio.duration || (subtitles.length > 0 ? subtitles[subtitles.length - 1].endTime + 2 : 100);

        display.updateProgress(ct, d);
        display.highlightSubtitle(subtitles, ct);
    });

    // Keep duration UI valid
    audio.addEventListener('loadedmetadata', () => {
        const d = audio.duration || 0;
        display.updateProgress(audio.currentTime, d);
    });

    // --- 3. Main Logic (Polling) ---

    function startPolling() {
        // Poll server every 10 seconds
        setInterval(async() => {
            try {
                const response = await fetch(`/check_song?guild_id=${GUILD_ID}`);
                if (response.ok) {
                    const data = await response.json();
                    updateSong(data);
                }
            } catch (err) {
                // Ignore network errors
            }
        }, 10000);
    }

    function updateSong(data) {
        if (!data) return;

        // CASE A: NEW SONG (UUID changed)
        if (data.uuid !== currentUUID) {
            console.log("New song detected:", data.uuid);
            currentUUID = data.uuid;

            // Reset UI
            display.reset();
            display.updateMetadata(data.title, data.subtitle);

            // Parse Subtitles
            if (data.srt_content) {
                subtitles = parseSRT(data.srt_content);
                display.renderSubtitles(subtitles);
            } else {
                subtitles = [];
                display.setWaitingState();
            }

            // Load Audio
            if (data.audio_url) {
                audio.src = data.audio_url;
                audio.load();

                const playPromise = audio.play();
                if (playPromise !== undefined) {
                    playPromise.catch(e => {
                        console.log("Auto-play blocked initially.", e);
                    });
                }
            }
        }
        // CASE B: SAME SONG (Sync & State Check)
        else {
            // 1. Time Sync (Drift >= 5s)
            const serverTime = data.current_time;
            if (typeof serverTime === 'number') {
                const localTime = audio.currentTime;
                const diff = Math.abs(localTime - serverTime);

                if (diff >= 5) {
                    console.log(`[Sync] Drift ${diff.toFixed(2)}s >= 5s. Seeking to ${serverTime}s.`);
                    audio.currentTime = serverTime;
                }
            }

            // 2. Play/Pause Enforcement
            const shouldBePaused = (data.is_paused === true);

            if (shouldBePaused) {
                if (!audio.paused) {
                    console.log("Server requested PAUSE.");
                    audio.pause();
                }
            } else {
                // Server implies PLAY
                if (audio.paused) {
                    console.log("Server implies PLAY. Resuming local playback.");
                    const playPromise = audio.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(e => {
                            // User interaction may be required
                        });
                    }
                }
            }
        }
    }

    // Start
    startPolling();
});