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

        this.activeSubtitleId = null;
    }

    reset() {
        this.activeSubtitleId = null;
        this.timeCurrent.textContent = "00:00";
        this.progressFill.style.width = "0%";
        this.subtitleList.innerHTML = '';
    }

    setWaitingState() {
        this.subtitleList.innerHTML = '<div class="text-slate-500 italic flex items-center justify-center h-full">waiting for lyrics...</div>';
    }

    updateMetadata(title, subtitle) {
        if (title) this.songTitleEl.textContent = title;
        if (subtitle) this.songSubtitleEl.textContent = subtitle;
    }

    renderSubtitles(subtitles) {
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

        // Update Progress Bar Width
        const percentage = Math.min((currentTime / duration) * 100, 100);
        this.progressFill.style.width = `${percentage}%`;
    }

    highlightSubtitle(subtitles, currentTime) {
        const idx = subtitles.findIndex(s => currentTime >= s.startTime && currentTime <= s.endTime);

        if (idx !== -1 && idx !== this.activeSubtitleId) {
            this.updateActiveSubtitle(idx);
        } else if (idx === -1 && this.activeSubtitleId !== null) {
            this.clearActiveSubtitle();
        }
    }

    updateActiveSubtitle(index) {
        this.clearActiveSubtitle();

        this.activeSubtitleId = index;
        const el = document.getElementById(`sub-${index}`);
        if (el) {
            // 1. Container Styles (Active)
            el.classList.add('bg-slate-800/80', 'border-blue-500/30', 'scale-105', 'shadow-xl');

            // 2. Text Styles
            const textEl = el.querySelector('.sub-text');
            textEl.classList.remove('text-slate-500');
            textEl.classList.add('text-transparent', 'bg-clip-text', 'bg-gradient-to-r', 'from-blue-200', 'to-white', 'font-bold');

            // 3. Timestamp Styles
            const timeEl = el.querySelector('.timestamp-badge');
            timeEl.classList.remove('bg-slate-800', 'text-slate-400');
            timeEl.classList.add('bg-blue-500', 'text-white');

            // 4. Indicator
            const indicator = el.querySelector('.active-indicator');
            indicator.classList.remove('hidden');

            // Scroll into view
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    clearActiveSubtitle() {
        if (this.activeSubtitleId !== null) {
            const el = document.getElementById(`sub-${this.activeSubtitleId}`);
            if (el) {
                // 1. Revert Container
                el.classList.remove('bg-slate-800/80', 'border-blue-500/30', 'scale-105', 'shadow-xl');

                // 2. Revert Text
                const textEl = el.querySelector('.sub-text');
                textEl.classList.add('text-slate-500');
                textEl.classList.remove('text-transparent', 'bg-clip-text', 'bg-gradient-to-r', 'from-blue-200', 'to-white', 'font-bold');

                // 3. Revert Timestamp
                const timeEl = el.querySelector('.timestamp-badge');
                timeEl.classList.add('bg-slate-800', 'text-slate-400');
                timeEl.classList.remove('bg-blue-500', 'text-white');

                // 4. Hide Indicator
                const indicator = el.querySelector('.active-indicator');
                indicator.classList.add('hidden');
            }
            this.activeSubtitleId = null;
        }
    }
}