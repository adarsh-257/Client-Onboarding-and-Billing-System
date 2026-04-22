/**
 * Client Onboarding System — Application JavaScript
 * Handles HTMX events, Alpine.js interactions, and micro-animations
 */

// ===== HTMX Configuration =====
document.body.addEventListener('htmx:beforeRequest', function(event) {
    // Add loading indicator
    const target = event.detail.target;
    if (target) {
        target.style.opacity = '0.6';
        target.style.transition = 'opacity 150ms ease';
    }
});

document.body.addEventListener('htmx:afterSwap', function(event) {
    const target = event.detail.target;
    if (target) {
        target.style.opacity = '1';
        // Re-initialize animations on new content
        initAnimations(target);
    }
});

// ===== Animated Counters =====
function animateCounter(element, targetValue) {
    const duration = 1000;
    const start = 0;
    const startTime = performance.now();

    // Handle currency values
    const isCurrency = targetValue.toString().startsWith('$');
    const numericValue = parseFloat(targetValue.toString().replace(/[$,]/g, ''));

    if (isNaN(numericValue)) return;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.floor(easeOut * numericValue);

        if (isCurrency) {
            element.textContent = '$' + currentValue.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } else {
            element.textContent = currentValue.toLocaleString();
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = targetValue;
        }
    }

    requestAnimationFrame(update);
}

// ===== Initialize Animations =====
function initAnimations(container) {
    container = container || document;

    // Animate stat card values
    container.querySelectorAll('.stat-card-value').forEach(el => {
        const value = el.textContent.trim();
        if (value && !isNaN(parseFloat(value.replace(/[$,]/g, '')))) {
            animateCounter(el, value);
        }
    });
}

// ===== Mobile Sidebar Toggle =====
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// ===== Confirm Dangerous Actions =====
document.addEventListener('click', function(e) {
    const btn = e.target.closest('[data-confirm]');
    if (btn) {
        const message = btn.getAttribute('data-confirm') || 'Are you sure?';
        if (!confirm(message)) {
            e.preventDefault();
        }
    }
});

// ===== Auto-dismiss flash messages =====
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
});

// ===== Initialize on DOM Ready =====
document.addEventListener('DOMContentLoaded', function() {
    initAnimations();

    // Mark current page in sidebar
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
