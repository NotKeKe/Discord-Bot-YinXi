import { formatTime } from './utils.js';

export class DisplayManager {
    constructor() {
        this.subtitleList = document.getElementById('subtitle-list');
        this.timeCurrent = document.getElementById('time-current');
        this.timeTotal = document.getElementById('time-total');
        this.progressFill = document.getElementById('progress-fill');
        this.songTitleEl = document.getElementById('song-title');
        this.songSubtitleEl = document.getElementById('song-subtitle');
        this.volumeSlider = document.getElementById('volume-slider');

        // Sync Offset Controls
        this.offsetMinus = document.getElementById('offset-minus');
        this.offsetPlus = document.getElementById('offset-plus');
        this.offsetDisplay = document.getElementById('offset-display');

        // Status indicator in header
        this.statusText = document.getElementById('status-text');
        this.statusDot = document.getElementById('status-dot');
        this.statusPing = document.getElementById('status-ping');

        // Autoplay Button (Replaces Overlay)
        this.autoplayBtn = document.getElementById('autoplay-btn');

        this.activeSubtitleId = null;
        console.log("DisplayManager initialized");
    }

    /**
     * Binds click/long-press handlers to the Sync Offset buttons.
     * @param {Function} onMinus - Handler for minus button
     * @param {Function} onPlus - Handler for plus button
     */
    bindSyncControls(onMinus, onPlus) {
        if (!this.offsetMinus || !this.offsetPlus) {
            console.error("Sync controls not found in DOM.");
            return;
        }

        const addLongPressListener = (btn, action) => {
            let timeoutId = null;
            let intervalId = null;

            const stop = (e) => {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }
                if (intervalId) {
                    clearInterval(intervalId);
                    intervalId = null;
                }
            };

            const start = (e) => {
                // Prevent default behavior to stop text selection or context menu on mobile
                if (e.cancelable) e.preventDefault();

                // Clear any existing timers to be safe
                stop();

                // Trigger immediately once
                action();

                // Wait 500ms before starting continuous fire
                timeoutId = setTimeout(() => {
                    // Fire every 100ms
                    intervalId = setInterval(() => {
                        action();
                    }, 100);
                }, 500);
            };

            // Touch events (Mobile)
            btn.addEventListener('touchstart', start, { passive: false });
            btn.addEventListener('touchend', stop);
            btn.addEventListener('touchcancel', stop);

            // Mouse events (Desktop)
            btn.addEventListener('mousedown', start);
            btn.addEventListener('mouseup', stop);
            btn.addEventListener('mouseleave', stop);
        };

        addLongPressListener(this.offsetMinus, onMinus);
        addLongPressListener(this.offsetPlus, onPlus);

        console.log("Sync controls bound successfully with long-press support.");
    }

    // --- Autoplay Interaction Handling ---
    showAutoplayRequest(onInteractCallback) {
        if (!this.autoplayBtn) {
            console.warn("Autoplay button element missing");
            if (onInteractCallback) onInteractCallback();
            return;
        }

        this.autoplayBtn.classList.remove('hidden');

        this.autoplayBtn.onclick = () => {
            console.log("Autoplay button clicked");
            this.autoplayBtn.classList.add('hidden');
            if (onInteractCallback) onInteractCallback();
            this.autoplayBtn.onclick = null;
        };
    }

    hideAutoplayRequest() {
        if (this.autoplayBtn) {
            this.autoplayBtn.classList.add('hidden');
        }
    }

    reset() {
        this.activeSubtitleId = null;
        this.timeCurrent.textContent = "00:00";
        this.progressFill.style.width = "0%";
        this.subtitleList.innerHTML = '';
        this.updateOffsetDisplay(0); // Reset offset display
        this.setBuffering(false);
    }

    // NEW: Handle 404 / Stopped state
    showStoppedState() {
        console.log("[UI] Showing Stopped State");
        this.activeSubtitleId = null;
        this.timeCurrent.textContent = "--:--";
        this.timeTotal.textContent = "--:--";
        this.progressFill.style.width = "0%";

        // Force update Metadata
        this.songTitleEl.textContent = "Waiting for Signal...";
        this.songSubtitleEl.textContent = "System Idle";

        // Visual indicator in list area
        this.subtitleList.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-50">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                <p>Waiting for music to start...</p>
            </div>
        `;

        // Update Header Status to Disconnected/Idle
        if (this.statusText) this.statusText.textContent = "Idle";
        if (this.statusDot) this.statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-slate-600";
        if (this.statusPing) this.statusPing.classList.add('hidden');
    }

    updateOffsetDisplay(seconds) {
        if (!this.offsetDisplay) return;

        const sign = seconds > 0 ? '+' : '';
        this.offsetDisplay.textContent = `${sign}${seconds.toFixed(1)}s`;

        if (seconds === 0) {
            this.offsetDisplay.classList.remove('text-yellow-400', 'text-emerald-400');
            this.offsetDisplay.classList.add('text-blue-300');
        } else {
            this.offsetDisplay.classList.remove('text-blue-300');
            this.offsetDisplay.classList.add('text-yellow-400');
        }
    }

    setWaitingState() {
        this.subtitleList.innerHTML = '<div class="text-slate-500 italic flex items-center justify-center h-full">waiting for lyrics...</div>';
    }

    setBuffering(isBuffering) {
        if (isBuffering) {
            this.statusText.textContent = "Buffering...";
            this.statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-yellow-500";
            this.statusPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75";
            this.statusPing.classList.remove('hidden');
        } else {
            this.statusText.textContent = "Syncing";
            this.statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-emerald-500";
            this.statusPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75";
            this.statusPing.classList.remove('hidden');
        }
    }

    updateMetadata(title, subtitle) {
        if (title) this.songTitleEl.textContent = title;
        if (subtitle) this.songSubtitleEl.textContent = subtitle;
    }

    renderSubtitles(subtitles) {
        this.activeSubtitleId = null;

        this.subtitleList.innerHTML = subtitles.map((sub, index) => `
            <div id="sub-${index}" 
                 class="group w-full max-w-2xl p-6 rounded-2xl transition-all duration-500 border border-transparent pointer-events-none select-none"
                 data-start="${sub.startTime}">
                
                <div class="flex justify-between items-center mb-2">
                    <span class="timestamp-badge text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 transition-colors duration-300">
                        ${formatTime(sub.startTime)}
                    </span>
                    
                    <span class="active-indicator hidden flex h-2 w-2 relative">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                </div>
                
                <p class="text-2xl md:text-3xl font-medium leading-relaxed whitespace-pre-wrap text-slate-500 sub-text transition-colors duration-300">${sub.text}</p>
            </div>
        `).join('');
    }

    updateProgress(currentTime, duration) {
        this.timeCurrent.textContent = formatTime(currentTime);
        this.timeTotal.textContent = formatTime(duration);

        let percentage = 0;
        if (duration === Infinity) {
            percentage = 100;
            this.progressFill.classList.add('animate-pulse');
        } else {
            this.progressFill.classList.remove('animate-pulse');
            if (duration > 0) {
                percentage = Math.min((currentTime / duration) * 100, 100);
            }
        }

        this.progressFill.style.width = `${percentage}%`;
    }

    highlightSubtitle(subtitles, currentTime, immediate = false) {
        const idx = subtitles.findIndex(s => currentTime >= s.startTime && currentTime <= s.endTime);

        if (idx !== -1 && (idx !== this.activeSubtitleId || immediate)) {
            this.updateActiveSubtitle(idx, immediate);
        } else if (idx === -1 && this.activeSubtitleId !== null) {
            this.clearActiveSubtitle();
        }
    }

    updateActiveSubtitle(index, immediate = false) {
        if (!immediate) {
            this.clearActiveSubtitle();
        } else {
            if (this.activeSubtitleId !== index) this.activeSubtitleId = null;
        }

        this.activeSubtitleId = index;
        const el = document.getElementById(`sub-${index}`);
        if (el) {
            el.classList.add('bg-slate-800/80', 'border-blue-500/30', 'scale-105', 'shadow-xl');
            const textEl = el.querySelector('.sub-text');
            textEl.classList.remove('text-slate-500');
            textEl.classList.add('text-transparent', 'bg-clip-text', 'bg-gradient-to-r', 'from-blue-200', 'to-white', 'font-bold');
            const timeEl = el.querySelector('.timestamp-badge');
            timeEl.classList.remove('bg-slate-800', 'text-slate-400');
            timeEl.classList.add('bg-blue-500', 'text-white');
            const indicator = el.querySelector('.active-indicator');
            indicator.classList.remove('hidden');

            el.scrollIntoView({
                behavior: immediate ? 'auto' : 'smooth',
                block: 'center'
            });
        }
    }

    clearActiveSubtitle() {
        if (this.activeSubtitleId !== null) {
            const el = document.getElementById(`sub-${this.activeSubtitleId}`);
            if (el) {
                el.classList.remove('bg-slate-800/80', 'border-blue-500/30', 'scale-105', 'shadow-xl');
                const textEl = el.querySelector('.sub-text');
                textEl.classList.add('text-slate-500');
                textEl.classList.remove('text-transparent', 'bg-clip-text', 'bg-gradient-to-r', 'from-blue-200', 'to-white', 'font-bold');
                const timeEl = el.querySelector('.timestamp-badge');
                timeEl.classList.add('bg-slate-800', 'text-slate-400');
                timeEl.classList.remove('bg-blue-500', 'text-white');
                const indicator = el.querySelector('.active-indicator');
                indicator.classList.add('hidden');
            }
            this.activeSubtitleId = null;
        }
    }
}