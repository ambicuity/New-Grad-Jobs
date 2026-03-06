const MOBILE_MENU_BREAKPOINT = 768;
const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

function initMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    if (!mobileMenuToggle || !mobileMenu) return;

    let isMobileMenuOpen = false;

    function getMobileMenuFocusableElements() {
        return Array.from(mobileMenu.querySelectorAll(FOCUSABLE_SELECTOR));
    }

    function setMobileMenuFocusableState(isOpen) {
        const focusableElements = getMobileMenuFocusableElements();
        focusableElements.forEach((el) => {
            if (isOpen) {
                el.removeAttribute('tabindex');
            } else {
                el.setAttribute('tabindex', '-1');
            }
        });
    }

    function openMobileMenu() {
        isMobileMenuOpen = true;
        mobileMenu.classList.add('open');
        mobileMenuToggle.setAttribute('aria-expanded', 'true');
        mobileMenu.setAttribute('aria-hidden', 'false');
        setMobileMenuFocusableState(true);

        const [firstFocusable] = getMobileMenuFocusableElements();
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }

    function closeMobileMenu(restoreFocus = true) {
        isMobileMenuOpen = false;
        mobileMenu.classList.remove('open');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
        mobileMenu.setAttribute('aria-hidden', 'true');
        setMobileMenuFocusableState(false);

        if (restoreFocus) {
            mobileMenuToggle.focus();
        }
    }

    function toggleMobileMenu() {
        if (isMobileMenuOpen) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }

    function handleMobileMenuKeydown(event) {
        if (!isMobileMenuOpen) return;

        if (event.key === 'Escape') {
            event.preventDefault();
            closeMobileMenu();
            return;
        }

        if (event.key !== 'Tab') return;

        const focusableElements = getMobileMenuFocusableElements();
        if (focusableElements.length === 0) return;

        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements.at(-1);

        if (event.shiftKey && document.activeElement === firstFocusable) {
            event.preventDefault();
            lastFocusable.focus();
        } else if (!event.shiftKey && document.activeElement === lastFocusable) {
            event.preventDefault();
            firstFocusable.focus();
        }
    }

    function handleMobileMenuOutsideClick(event) {
        if (!isMobileMenuOpen) return;

        const clickedInsideMenu = mobileMenu.contains(event.target);
        const clickedToggle = mobileMenuToggle.contains(event.target);

        if (!clickedInsideMenu && !clickedToggle) {
            closeMobileMenu();
        }
    }

    function handleMobileMenuResize() {
        if (window.innerWidth > MOBILE_MENU_BREAKPOINT && isMobileMenuOpen) {
            closeMobileMenu(false);
        }
    }

    setMobileMenuFocusableState(false);
    mobileMenuToggle.setAttribute('aria-expanded', 'false');
    mobileMenu.setAttribute('aria-hidden', 'true');

    mobileMenuToggle.addEventListener('click', toggleMobileMenu);
    mobileMenu.addEventListener('click', (event) => {
        const link = event.target.closest('a');
        if (link) {
            closeMobileMenu();
        }
    });

    document.addEventListener('keydown', handleMobileMenuKeydown);
    document.addEventListener('click', handleMobileMenuOutsideClick);
    window.addEventListener('resize', handleMobileMenuResize, { passive: true });
}

window.initMobileMenu = initMobileMenu;
