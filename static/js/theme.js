document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    const saved = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', saved);
    updateIcon(saved);

    toggle.addEventListener('click', function() {
        const current = html.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateIcon(next);
    });

    function updateIcon(theme) {
        const icon = toggle.querySelector('.theme-icon');
        icon.textContent = theme === 'light' ? '🌙' : '☀️';
    }
});

function showPopup(eventId) {
    const popup = document.getElementById('popup-' + eventId);
    if (popup) popup.classList.add('active');
}

function closePopup(eventId) {
    const popup = document.getElementById('popup-' + eventId);
    if (popup) popup.classList.remove('active');
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('popup-close')) {
        const popup = e.target.closest('.popup');
        if (popup) popup.classList.remove('active');
    }
});