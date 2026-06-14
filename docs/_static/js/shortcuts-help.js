// Shows a helper when pressing "?" anywhere outside a form field, listing
// the site's keyboard shortcuts. Esc / click on backdrop / second "?"
// closes it.

(function () {
    const SHORTCUTS = [
        { keys: ["Shift", "D"], desc: "Toggle dark / light mode" },
        { keys: ["Ctrl", "K"], desc: "Focus search" },
        { keys: ["↑", "↓"], desc: "Navigate search results" },
        { keys: ["Enter"], desc: "Open highlighted search result" },
        { keys: ["Esc"], desc: "Close search / dialog" },
        { keys: ["?"], desc: "Show this help" },
    ];

    const flyout = document.createElement("div");
    flyout.className = "shortcut-flyout";
    flyout.setAttribute("aria-hidden", "true");
    flyout.setAttribute("role", "dialog");
    flyout.setAttribute("aria-modal", "true");
    flyout.setAttribute("aria-label", "Keyboard shortcuts");
    flyout.innerHTML =
        '<div class="shortcut-flyout-backdrop"></div>' +
        '<div class="shortcut-flyout-panel" tabindex="-1">' +
        '<div class="shortcut-flyout-title">Keyboard shortcuts</div>' +
        '<dl class="shortcut-flyout-list">' +
        SHORTCUTS.map((s) => {
            return (
                "<dt>" +
                s.keys
                    .map((k) => "<kbd>" + k + "</kbd>")
                    .join(" + ") +
                "</dt>" +
                "<dd>" + s.desc + "</dd>"
            );
        }).join("") +
        "</dl>" +
        "</div>";
    document.body.appendChild(flyout);

    const backdrop = flyout.querySelector(".shortcut-flyout-backdrop");
    const panel = flyout.querySelector(".shortcut-flyout-panel");
    let lastFocused = null;

    function open() {
        lastFocused = document.activeElement;
        flyout.classList.add("is-open");
        flyout.setAttribute("aria-hidden", "false");
        panel.focus();
    }

    function close() {
        flyout.classList.remove("is-open");
        flyout.setAttribute("aria-hidden", "true");
        if (lastFocused && typeof lastFocused.focus === "function") {
            lastFocused.focus();
        }
        lastFocused = null;
    }

    function toggle() {
        if (flyout.classList.contains("is-open")) {
            close();
        } else {
            open();
        }
    }

    backdrop.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
        const tag = document.activeElement && document.activeElement.tagName;
        const isOpen = flyout.classList.contains("is-open");
        if (!isOpen && (tag === "INPUT" || tag === "TEXTAREA")) {
            return;
        }
        if (e.key === "?") {
            e.preventDefault();
            toggle();
        }
        else if (e.key === "Escape" && isOpen) {
            close();
        }
        else if (e.key === "Tab" && isOpen) {
            // Dialog has no focusable children: keep focus on the panel.
            e.preventDefault();
            panel.focus();
        }
    });
})();
