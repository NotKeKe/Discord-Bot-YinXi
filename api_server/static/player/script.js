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
    // Extract Guild ID from URL if not injected: /player/12345_uuid -> 12345
    if (!GUILD_ID || GUILD_ID.includes("{{")) {
        console.warn("Context injection missing. Attempting to parse Guild ID from URL...");
        try {
            // pathname format expected: /player/12345_abcde
            const pathSegments = window.location.pathname.split('/');
            // Get the last segment (handling potential trailing slash)
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

    // Stream Buffering Handlers
    audio.addEventListener('waiting', () => {
        console.log('[Stream] Buffering...');
        display.setBuffering(true);
    });

    audio.addEventListener('playing', () => {
        console.log('[Stream] Playing');
        display.setBuffering(false);
    });

    audio.addEventListener('canplay', () => {
        display.setBuffering(false);
    });

    // Audio Progress & Visuals
    // This is where "Time Flow" is handled in JS
    const handleProgress = () => {
        const ct = audio.currentTime;

        // Handling Logic for Streams:
        let d = audio.duration;

        if (!Number.isFinite(d)) {
            if (subtitles.length > 0) {
                d = subtitles[subtitles.length - 1].endTime + 2; // Add 2s padding
            } else {
                d = Infinity; // Pure stream, no subtitles
            }
        }

        display.updateProgress(ct, d);
        display.highlightSubtitle(subtitles, ct);
    };

    // The 'timeupdate' event fires repeatedly as the audio plays
    audio.addEventListener('timeupdate', handleProgress);
    audio.addEventListener('loadedmetadata', handleProgress);

    // --- 3. Main Logic (Polling) ---

    function startPolling() {
        // Poll server every 10 seconds
        setInterval(async() => {
            try {
                const response = await fetch(`/player/check_song?guild_id=${GUILD_ID}`);

                if (response.ok) {
                    const data = await response.json();
                    updateSong(data);
                } else if (response.status === 404) {
                    console.log("Waiting for session to be created...");
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

            // Load Audio Stream
            if (data.audio_url) {
                console.log("[Stream] Loading URL:", data.audio_url);
                audio.src = data.audio_url;
                audio.load();

                // Try to auto-play when new song loads
                const playPromise = audio.play();
                if (playPromise !== undefined) {
                    playPromise.catch(e => {
                        console.log("Auto-play blocked initially. Waiting for user interaction.", e);
                    });
                }
            }
        }
        // CASE B: SAME SONG (Sync & State Check)
        else {
            // 1. Time Sync (Drift >= 5s)
            // Logic restored: Check if local time has drifted too far from server time
            const serverTime = data.current_time;
            if (typeof serverTime === 'number') {
                const localTime = audio.currentTime;
                const diff = Math.abs(localTime - serverTime);

                // If drift is significant (> 5s), align local player to server time.
                if (diff >= 5) {
                    console.log(`[Sync] Drift ${diff.toFixed(2)}s >= 5s. Seeking to ${serverTime}s.`);
                    if (Number.isFinite(audio.duration) || (audio.seekable && audio.seekable.length > 0)) {
                        audio.currentTime = serverTime;
                    }
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
                if (audio.paused && audio.readyState >= 2) {
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