// Mobile sidebar: hamburger button toggles a `.sidebar-open` class on
// <body>, CSS slides the sidebar in from the left. Tapping the
// backdrop or swiping left closes it.

(function () {
    const btn = document.getElementById("sidebar-toggle");
    const sidebar = document.querySelector(".left-sidebar");
    const body = document.body;

    if (!btn || !sidebar) {
        return;
    }

    const backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    backdrop.setAttribute("aria-hidden", "true");
    body.appendChild(backdrop);

    function open() {
        body.classList.add("sidebar-open");
        btn.setAttribute("aria-expanded", "true");
        sidebar.setAttribute("role", "dialog");
        sidebar.setAttribute("aria-modal", "true");
        const firstLink = sidebar.querySelector("a");
        if (firstLink) {
            firstLink.focus();
        }
    }

    function close() {
        body.classList.remove("sidebar-open");
        btn.setAttribute("aria-expanded", "false");
        sidebar.removeAttribute("role");
        sidebar.removeAttribute("aria-modal");
        // Restore focus to the hamburger only if it's still visible
        // (offsetParent is null when display:none, e.g. >1024px).
        if (btn.offsetParent !== null) {
            btn.focus();
        }
    }

    function toggle() {
        if (body.classList.contains("sidebar-open")) {
            close();
        } else {
            open();
        }
    }

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggle();
    });

    backdrop.addEventListener("click", close);

    let startX = null;

    sidebar.addEventListener(
        "touchstart",
        (e) => {
            startX = e.touches[0].clientX;
        },
        { passive: true }
    );

    sidebar.addEventListener(
        "touchend",
        (e) => {
            if (startX === null) {
                return;
            }
            const dx = e.changedTouches[0].clientX - startX;
            startX = null;
            if (dx < -40) {
                close();
            }
        },
        { passive: true }
    );

    sidebar.addEventListener("click", (e) => {
        const link = e.target.closest("a");
        if (link) {
            close();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (!body.classList.contains("sidebar-open")) {
            return;
        }
        if (e.key === "Escape") {
            close();
            return;
        }
        if (e.key === "Tab") {
            const items = sidebar.querySelectorAll("a, button, input");
            if (!items.length) {
                return;
            }
            const first = items[0];
            const last = items[items.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    });

    // Auto-close when transitioning to desktop width.
    const desktop = window.matchMedia("(min-width: 1025px)");
    desktop.addEventListener("change", (e) => {
        if (e.matches && body.classList.contains("sidebar-open")) {
            close();
        }
    });
})();
