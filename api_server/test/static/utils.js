/**
 * Converts "HH:MM:SS,ms" string to total seconds (float).
 */
export function timeToSeconds(timeString) {
    const parts = timeString.split(':');
    if (parts.length < 3) return 0;
    const hours = parseInt(parts[0], 10);
    const minutes = parseInt(parts[1], 10);
    const secondsParts = parts[2].split(',');
    const seconds = parseInt(secondsParts[0], 10);
    const milliseconds = parseInt(secondsParts[1] || '0', 10);
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
}

/**
 * Formats seconds (float) to "MM:SS" or "HH:MM:SS" string.
 */
export function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const pad = (num) => num.toString().padStart(2, '0');
    if (h > 0) return `${pad(h)}:${pad(m)}:${pad(s)}`;
    return `${pad(m)}:${pad(s)}`;
}

/**
 * Parses SRT content string into an array of subtitle objects.
 * Merges consecutive identical texts within 0.5s gap.
 */
export function parseSRT(data) {
    if (!data) return [];
    const normalizedData = data.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const blocks = normalizedData.trim().split(/\n\n+/);
    const rawSubtitles = [];

    blocks.forEach((block, index) => {
        const lines = block.split('\n');
        if (lines.length >= 2) {
            const timeLineIndex = lines.findIndex(line => line.includes('-->'));
            if (timeLineIndex !== -1) {
                const timeLine = lines[timeLineIndex];
                const [startStr, endStr] = timeLine.split('-->').map(s => s.trim());
                const textLines = lines.slice(timeLineIndex + 1);
                const text = textLines.join('\n');
                if (startStr && endStr) {
                    rawSubtitles.push({
                        id: index + 1,
                        startTime: timeToSeconds(startStr),
                        endTime: timeToSeconds(endStr),
                        text: text
                    });
                }
            }
        }
    });

    // Merge identical consecutive subtitles
    if (rawSubtitles.length === 0) return [];
    const mergedSubtitles = [];
    let currentGroup = rawSubtitles[0];
    let count = 1;

    for (let i = 1; i < rawSubtitles.length; i++) {
        const nextSub = rawSubtitles[i];
        const textMatch = currentGroup.text.trim() === nextSub.text.trim();
        const gap = nextSub.startTime - currentGroup.endTime;
        const isContinuous = gap <= 0.5;
        if (textMatch && isContinuous) {
            count++;
            currentGroup.endTime = nextSub.endTime;
        } else {
            if (count > 1) {
                currentGroup.text = `${currentGroup.text.trim()} (×${count})`;
            } else {
                currentGroup.text = currentGroup.text.trim();
            }
            mergedSubtitles.push(currentGroup);
            currentGroup = nextSub;
            count = 1;
        }
    }
    if (count > 1) {
        currentGroup.text = `${currentGroup.text.trim()} (×${count})`;
    } else {
        currentGroup.text = currentGroup.text.trim();
    }
    mergedSubtitles.push(currentGroup);
    return mergedSubtitles;
}