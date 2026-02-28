/* ==========================================================================
   Smart Property Rental System - Main JavaScript
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ------------------------------------------------------------------
       1. Auto-dismiss alerts after 5 seconds
    ------------------------------------------------------------------ */
    const autoDismissAlerts = document.querySelectorAll('.alert-dismissible');

    autoDismissAlerts.forEach(function (alert) {
        setTimeout(function () {
            // Add the fade-out animation class defined in style.css
            alert.classList.add('fade-out');

            // Remove the element from the DOM after the animation completes
            alert.addEventListener('animationend', function () {
                alert.remove();
            });
        }, 5000);
    });


    /* ------------------------------------------------------------------
       2. Bootstrap tooltip initialization
    ------------------------------------------------------------------ */
    const tooltipTriggerList = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
    );

    if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
        tooltipTriggerList.forEach(function (el) {
            new bootstrap.Tooltip(el);
        });
    }


    /* ------------------------------------------------------------------
       3. Image preview for file upload inputs
       Usage: add data-preview-target="#previewImgId" to the file input
    ------------------------------------------------------------------ */
    const fileInputs = document.querySelectorAll(
        'input[type="file"][data-preview-target]'
    );

    fileInputs.forEach(function (input) {
        input.addEventListener('change', function () {
            const targetSelector = this.getAttribute('data-preview-target');
            const previewEl = document.querySelector(targetSelector);

            if (!previewEl) return;

            const file = this.files[0];
            if (!file) return;

            // Only handle image files
            if (!file.type.startsWith('image/')) return;

            const reader = new FileReader();
            reader.onload = function (e) {
                // If the target is an <img>, set its src directly
                if (previewEl.tagName === 'IMG') {
                    previewEl.src = e.target.result;
                    previewEl.style.display = 'block';
                } else {
                    // If it is a container, insert or update the <img> inside it
                    let img = previewEl.querySelector('img');
                    const placeholder = previewEl.querySelector('.placeholder-text');

                    if (!img) {
                        img = document.createElement('img');
                        previewEl.appendChild(img);
                    }

                    img.src = e.target.result;
                    img.alt = 'Preview';

                    // Hide the placeholder text if it exists
                    if (placeholder) {
                        placeholder.style.display = 'none';
                    }
                }
            };
            reader.readAsDataURL(file);
        });
    });


    /* ------------------------------------------------------------------
       4. Confirm delete dialogs
       Usage: add class "confirm-delete" and optional
              data-confirm-message="Custom message?" to a link or button
    ------------------------------------------------------------------ */
    document.addEventListener('click', function (e) {
        const trigger = e.target.closest('.confirm-delete');
        if (!trigger) return;

        const message =
            trigger.getAttribute('data-confirm-message') ||
            'Are you sure you want to delete this item? This action cannot be undone.';

        if (!confirm(message)) {
            e.preventDefault();
            e.stopPropagation();
        }
    });


    /* ------------------------------------------------------------------
       5. Smooth scroll for anchor links
    ------------------------------------------------------------------ */
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#' || targetId === '') return;

            const targetEl = document.querySelector(targetId);
            if (!targetEl) return;

            e.preventDefault();
            targetEl.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });

            // Update the URL hash without jumping
            history.pushState(null, null, targetId);
        });
    });


    /* ------------------------------------------------------------------
       6. Active navbar link highlighting based on current URL
    ------------------------------------------------------------------ */
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-custom .nav-link');

    navLinks.forEach(function (link) {
        const linkPath = link.getAttribute('href');
        if (!linkPath) return;

        // Remove any existing active class first
        link.classList.remove('active');

        // Exact match or starts-with match (for sub-pages)
        if (linkPath === currentPath) {
            link.classList.add('active');
        } else if (
            linkPath !== '/' &&
            currentPath.startsWith(linkPath)
        ) {
            link.classList.add('active');
        }
    });


    /* ------------------------------------------------------------------
       7. Search form submit on filter change
       Usage: add class "auto-submit-filter" to <select> or <input>
              elements inside a form
    ------------------------------------------------------------------ */
    const autoSubmitFilters = document.querySelectorAll('.auto-submit-filter');

    autoSubmitFilters.forEach(function (filter) {
        filter.addEventListener('change', function () {
            const form = this.closest('form');
            if (form) {
                form.submit();
            }
        });
    });


    /* ------------------------------------------------------------------
       8. Character counter for textareas
       Usage: add data-max-length="500" to a <textarea>.
       A counter element will be created automatically below it.
    ------------------------------------------------------------------ */
    const textareasWithLimit = document.querySelectorAll(
        'textarea[data-max-length]'
    );

    textareasWithLimit.forEach(function (textarea) {
        const maxLength = parseInt(textarea.getAttribute('data-max-length'), 10);
        if (isNaN(maxLength) || maxLength <= 0) return;

        // Create the counter element
        const counter = document.createElement('div');
        counter.className = 'char-counter';
        counter.textContent = '0 / ' + maxLength;
        textarea.parentNode.insertBefore(counter, textarea.nextSibling);

        function updateCounter() {
            const currentLength = textarea.value.length;
            counter.textContent = currentLength + ' / ' + maxLength;

            // Remove previous state classes
            counter.classList.remove('near-limit', 'at-limit');

            if (currentLength >= maxLength) {
                counter.classList.add('at-limit');
                // Enforce the character limit
                textarea.value = textarea.value.substring(0, maxLength);
                counter.textContent = maxLength + ' / ' + maxLength;
            } else if (currentLength >= maxLength * 0.85) {
                counter.classList.add('near-limit');
            }
        }

        textarea.addEventListener('input', updateCounter);
        textarea.addEventListener('keyup', updateCounter);

        // Initialise with current content (e.g. when editing an existing form)
        updateCounter();
    });


    /* ------------------------------------------------------------------
       9. Back to Top button visibility toggle
    ------------------------------------------------------------------ */
    const backToTopBtn = document.querySelector('.back-to-top');

    if (backToTopBtn) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 400) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        });

        backToTopBtn.addEventListener('click', function (e) {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }


    /* ------------------------------------------------------------------
       10. Scroll the messages container to the bottom on load
    ------------------------------------------------------------------ */
    const messagesContainer = document.querySelector('.messages-container');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /* ------------------------------------------------------------------
       11. Premium Navbar: scroll → .scrolled class + mobile hamburger
    ------------------------------------------------------------------ */
    const sprsNavbar = document.querySelector('.sprs-navbar');
    if (sprsNavbar) {
        const onScroll = () => {
            if (window.scrollY > 50) {
                sprsNavbar.classList.add('scrolled');
            } else {
                sprsNavbar.classList.remove('scrolled');
            }
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll(); // run once on load
    }

    // Hamburger toggle
    const hamburger = document.querySelector('.sprs-hamburger');
    const mobileMenu = document.querySelector('.sprs-mobile-menu');
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('open');
            mobileMenu.classList.toggle('open');
        });
        // Close when any mobile link is clicked
        mobileMenu.querySelectorAll('.mobile-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('open');
                mobileMenu.classList.remove('open');
            });
        });
    }

    /* ------------------------------------------------------------------
       12. Back-to-top button
    ------------------------------------------------------------------ */
    const btt = document.querySelector('.back-to-top');
    if (btt) {
        window.addEventListener('scroll', () => {
            btt.classList.toggle('visible', window.scrollY > 400);
        }, { passive: true });
        btt.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    /* ------------------------------------------------------------------
       13. Hero scroll indicator smooth scroll
    ------------------------------------------------------------------ */
    const heroScroll = document.querySelector('.hero-scroll-indicator');
    if (heroScroll) {
        heroScroll.addEventListener('click', () => {
            const statsBar = document.querySelector('.sprs-stats-bar');
            if (statsBar) {
                statsBar.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

});

