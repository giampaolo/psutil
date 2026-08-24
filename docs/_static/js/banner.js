// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Notice above the topbar. Archived releases inject the same markup
// from build_versions.py, and those pages have no .header-stack.

(function () {
    const KEY = "psutil-banner";
    const root = document.documentElement;
    const banner = document.querySelector(".site-banner");
    if (!banner) {
        return;
    }

    // The banner is part of the fixed header and its text wraps, so
    // the offset below it has to be measured, not hardcoded.
    const stack = banner.closest(".header-stack");

    function syncHeight() {
        if (stack) {
            root.style.setProperty(
                "--header-height",
                stack.offsetHeight + "px",
            );
        }
    }

    const close = banner.querySelector(".site-banner-close");
    if (close) {
        close.addEventListener("click", () => {
            root.classList.add("site-banner-dismissed");
            try {
                localStorage.setItem(KEY, banner.dataset.bannerId || "");
            }
            catch (err) {
                console.warn("banner: " + err.message);
            }
            syncHeight();
        });
    }

    if (stack) {
        new ResizeObserver(syncHeight).observe(stack);
        syncHeight();
    }
})();
