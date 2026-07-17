// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Dim the rest of the page while the sidebar search input is focused.
// search.css handles the visual fade. Skipped on touch devices.

(function () {
    if (window.matchMedia("(pointer: coarse)").matches) {
        return;
    }
    const input = document.getElementById("search-input");
    if (!input) {
        return;
    }
    const overlay = document.createElement("div");
    overlay.className = "search-overlay";
    document.body.appendChild(overlay);
    input.addEventListener("focus", () => {
        document.body.classList.add("search-focused");
    });
    input.addEventListener("blur", () => {
        document.body.classList.remove("search-focused");
    });
})();
