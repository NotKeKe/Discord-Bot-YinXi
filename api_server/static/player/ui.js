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

        // Status indicator in header
        this.statusText = document.getElementById('status-text');
        this.statusDot = document.getElementById('status-dot');
        this.statusPing = document.getElementById('status-ping');

        // Autoplay Button (Replaces Overlay)
        this.autoplayBtn = document.getElementById('autoplay-btn');

        this.activeSubtitleId = null;
        console.log("DisplayManager initialized (v3.1 - Instant Scroll Fix)");
    }

    // --- Autoplay Interaction Handling ---
    showAutoplayRequest(onInteractCallback) {
        if (!this.autoplayBtn) {
            console.warn("Autoplay button element missing");
            if (onInteractCallback) onInteractCallback();
            return;
        }

        // Show the button
        this.autoplayBtn.classList.remove('hidden');

        // Handle click
        this.autoplayBtn.onclick = () => {
            console.log("Autoplay button clicked");
            this.autoplayBtn.classList.add('hidden');
            if (onInteractCallback) onInteractCallback();

            // Remove handler to prevent double firing or memory leaks
            this.autoplayBtn.onclick = null;
        };
    }

    hideAutoplayRequest() {
            if (this.autoplayBtn) {
                this.autoplayBtn.classList.add('hidden');
            }
        }
        // ---------------------------------

    reset() {
        this.activeSubtitleId = null;
        this.timeCurrent.textContent = "00:00";
        this.progressFill.style.width = "0%";
        this.subtitleList.innerHTML = '';
        this.setBuffering(false);
    }

    setWaitingState() {
        this.subtitleList.innerHTML = '<div class="text-slate-500 italic flex items-center justify-center h-full">waiting for lyrics...</div>';
    }

    setBuffering(isBuffering) {
        if (isBuffering) {
            this.statusText.textContent = "Buffering...";
            this.statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-yellow-500";
            this.statusPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75";
        } else {
            this.statusText.textContent = "Syncing";
            this.statusDot.className = "relative inline-flex rounded-full h-3 w-3 bg-emerald-500";
            this.statusPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75";
        }
    }

    updateMetadata(title, subtitle) {
        if (title) this.songTitleEl.textContent = title;
        if (subtitle) this.songSubtitleEl.textContent = subtitle;
    }

    renderSubtitles(subtitles) {
        // CRITICAL: Reset active ID so the logic knows to re-apply styles to the new DOM elements
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
        // Update Time Display
        this.timeCurrent.textContent = formatTime(currentTime);
        this.timeTotal.textContent = formatTime(duration);

        // Handle Progress Bar Logic
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

    /**
     * Highlights the current subtitle.
     * @param {Array} subtitles - The subtitle data array.
     * @param {Number} currentTime - Current audio time.
     * @param {Boolean} immediate - If true, scrolls instantly without animation (fix for language switch jump).
     */
    highlightSubtitle(subtitles, currentTime, immediate = false) {
        const idx = subtitles.findIndex(s => currentTime >= s.startTime && currentTime <= s.endTime);

        // Force update if immediate is requested, even if index hasn't changed (because DOM might be new)
        if (idx !== -1 && (idx !== this.activeSubtitleId || immediate)) {
            this.updateActiveSubtitle(idx, immediate);
        } else if (idx === -1 && this.activeSubtitleId !== null) {
            this.clearActiveSubtitle();
        }
    }

    updateActiveSubtitle(index, immediate = false) {
        // If simply switching highlight, clear old one first
        if (!immediate) {
            this.clearActiveSubtitle();
        } else {
            // If immediate (new DOM), just ensure ID logic is clean, 
            // no need to remove classes from old DOM elements that don't exist
            if (this.activeSubtitleId !== index) this.activeSubtitleId = null;
        }

        this.activeSubtitleId = index;
        const el = document.getElementById(`sub-${index}`);
        if (el) {
            // Apply Styles
            el.classList.add('bg-slate-800/80', 'border-blue-500/30', 'scale-105', 'shadow-xl');
            const textEl = el.querySelector('.sub-text');
            textEl.classList.remove('text-slate-500');
            textEl.classList.add('text-transparent', 'bg-clip-text', 'bg-gradient-to-r', 'from-blue-200', 'to-white', 'font-bold');
            const timeEl = el.querySelector('.timestamp-badge');
            timeEl.classList.remove('bg-slate-800', 'text-slate-400');
            timeEl.classList.add('bg-blue-500', 'text-white');
            const indicator = el.querySelector('.active-indicator');
            indicator.classList.remove('hidden');

            // SCROLL LOGIC
            // Use 'auto' behavior for immediate jumps (prevents seeing top of list)
            // Use 'smooth' for normal playback progression
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