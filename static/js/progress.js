/**
 * تتبع تقدم قراءة المحاضرة
 * Lecture reading progress tracker
 */

function initLectureProgress(config) {
    const contentEl = document.getElementById('lecture-content');
    const progressBar = document.getElementById('progress-bar');
    const progressLabel = document.getElementById('progress-label');

    if (!contentEl || !progressBar) return;

    let lastSavedProgress = config.initialProgress || 0;
    let saveTimeout = null;

    function calculateProgress() {
        const rect = contentEl.getBoundingClientRect();
        const windowHeight = window.innerHeight;
        const contentHeight = contentEl.scrollHeight;

        if (contentHeight <= windowHeight) return 100;

        const scrolled = window.scrollY + windowHeight - contentEl.offsetTop;
        const percent = Math.min(100, Math.max(0, Math.round((scrolled / contentHeight) * 100)));
        return percent;
    }

    function updateUI(percent) {
        progressBar.style.width = percent + '%';
        progressLabel.textContent = percent + '%';
    }

    async function saveProgress(percent) {
        if (Math.abs(percent - lastSavedProgress) < 5 && percent < 100) return;

        lastSavedProgress = percent;
        const status = percent >= 95 ? 'completed' : 'in_progress';

        try {
            await fetch('/api/v1/progress/save/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    year_slug: config.yearSlug,
                    subject_slug: config.subjectSlug,
                    lecture_slug: config.lectureSlug,
                    progress_percent: percent,
                    status: status,
                }),
            });
        } catch (err) {
            console.warn('فشل حفظ التقدم:', err);
        }
    }

    function getCsrfToken() {
        const name = 'csrftoken=';
        for (let cookie of document.cookie.split(';')) {
            cookie = cookie.trim();
            if (cookie.startsWith(name)) {
                return decodeURIComponent(cookie.substring(name.length));
            }
        }
        return '';
    }

    function onScroll() {
        const percent = calculateProgress();
        updateUI(percent);

        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => saveProgress(percent), 1000);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}
