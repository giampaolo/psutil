// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Flips data-theme on <html> between "light" and "dark" and persists
// the choice in localStorage. Initial application happens inline in
// layout.html (extrahead) so there is no flash on page load. Keep the
// "psutil-sphinx-theme" key in sync with the inline script.
//
// Shortcuts:
//   click on #theme-toggle button (in the topbar)
//   Shift+D anywhere outside an input/textarea
(function () {
    const html = document.documentElement;
    const KEY = "psutil-sphinx-theme";

    function applyTheme(dark) {
        html.setAttribute("data-theme", dark ? "dark" : "light");
        const btn = document.getElementById("theme-toggle");
        if (btn) {
            const icon = btn.querySelector("i");
            if (icon) {
                icon.className = dark
                    ? "fa-solid fa-sun"
                    : "fa-regular fa-moon";
            }
        }
    }

    function setTheme(dark) {
        applyTheme(dark);
        try {
            localStorage.setItem(KEY, dark ? "dark" : "light");
        } catch (e) {
            // private mode / storage disabled: skip persisting
        }
    }

    // Sync the icon with whatever the inline script in <head> set.
    applyTheme(html.getAttribute("data-theme") === "dark");

    const btn = document.getElementById("theme-toggle");
    if (btn) {
        btn.addEventListener("click", () => {
            setTheme(html.getAttribute("data-theme") !== "dark");
        });
    }

    // Shift+D: toggle dark mode (skip when typing in a form field).
    document.addEventListener("keydown", (e) => {
        const tag = document.activeElement && document.activeElement.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") {
            return;
        }
        if (e.shiftKey && e.key === "D") {
            setTheme(html.getAttribute("data-theme") !== "dark");
        }
    });

    // Keep tabs in sync: another tab toggled, mirror it here without
    // re-writing localStorage (would loop the storage event).
    window.addEventListener("storage", (e) => {
        if (e.key === KEY && e.newValue) {
            applyTheme(e.newValue === "dark");
        }
    });
})();
