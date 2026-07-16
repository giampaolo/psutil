// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Floating "back to top" button. Appears when the user has scrolled
// down and is moving back up; hidden again at the top of the page.

(function () {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "back-to-top";
    btn.setAttribute("aria-label", "Back to top");
    btn.title = "Back to top";
    // Hidden at rest via opacity, which doesn't remove it from the tab
    // order; keep it unfocusable until the scroll handler shows it.
    btn.tabIndex = -1;
    btn.innerHTML = '<i class="fa-solid fa-chevron-up" aria-hidden="true"></i>';
    // Faster than the browser's default smooth scroll (which can take
    // ~1s on long pages). Custom 300ms ease-out animation.
    btn.addEventListener("click", () => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            window.scrollTo(0, 0);
            return;
        }
        const start = window.scrollY;
        const t0 = performance.now();
        function step(now) {
            const t = Math.min((now - t0) / 300, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            window.scrollTo(0, start * (1 - eased));
            if (t < 1) {
                requestAnimationFrame(step);
            }
        }
        requestAnimationFrame(step);
    });
    document.body.appendChild(btn);

    // Show only while scrolling UP (and past the threshold); hide
    // again on any downward scroll.
    const SHOW_AFTER_PX = 400;
    let lastY = window.scrollY;
    window.addEventListener("scroll", () => {
        const y = window.scrollY;
        const goingUp = y < lastY;
        const visible = goingUp && y > SHOW_AFTER_PX;
        btn.classList.toggle("is-visible", visible);
        btn.tabIndex = visible ? 0 : -1;
        lastY = y;
    }, { passive: true });
})();
