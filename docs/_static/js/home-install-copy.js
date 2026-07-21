// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Wire the home-page install pill: copy `pip install psutil` to the
// clipboard and flash a "Copied" hint on the button.

(function () {
    const wrapper = document.querySelector(".home-install");
    if (!wrapper) {
        return;
    }
    const btn = wrapper.querySelector(".home-install-copy");
    const cmd = wrapper.querySelector(".home-install-cmd");
    if (!btn || !cmd) {
        return;
    }

    let resetTimer = null;

    function flashCopied() {
        wrapper.classList.add("copied");
        const label = btn.getAttribute("aria-label") || "";
        if (!btn.dataset.origLabel) {
            btn.dataset.origLabel = label;
        }
        btn.setAttribute("aria-label", "Copied");
        if (resetTimer) {
            clearTimeout(resetTimer);
        }
        resetTimer = setTimeout(() => {
            wrapper.classList.remove("copied");
            btn.setAttribute("aria-label", btn.dataset.origLabel);
        }, 1400);
    }

    function legacyCopy(text) {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        let ok = false;
        try {
            ok = document.execCommand("copy");
        }
        finally {
            document.body.removeChild(ta);
        }
        return ok;
    }

    btn.addEventListener("click", () => {
        const text = cmd.textContent.trim();
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(flashCopied)
                .catch(() => {
                    if (legacyCopy(text)) {
                        flashCopied();
                    }
                });
        }
        else if (legacyCopy(text)) {
            flashCopied();
        }
    });
})();
