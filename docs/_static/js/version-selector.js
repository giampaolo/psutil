// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Closes the topbar version dropdown on an outside click or Esc.

(function () {
    const details = document.getElementById("version-selector");
    if (!details) {
        return;
    }

    document.addEventListener("click", function (event) {
        if (details.open && !details.contains(event.target)) {
            details.removeAttribute("open");
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && details.open) {
            details.removeAttribute("open");
            details.querySelector("summary").focus();
        }
    });

    // Land on the same page in the other version when it exists, else follow
    // the link to that version's home page.
    const page = details.dataset.versionPage;
    if (!page) {
        return;
    }
    for (const link of details.querySelectorAll(".topbar-versions-item")) {
        if (link.classList.contains("is-current")) {
            continue;
        }
        link.addEventListener("click", function (event) {
            if (event.metaKey || event.ctrlKey || event.shiftKey) {
                return;
            }
            const same = new URL(page + "/", link.href).href;
            event.preventDefault();
            fetch(same, { method: "HEAD" })
                .then((resp) => {
                    window.location.href = resp.ok ? same : link.href;
                })
                .catch(() => {
                    window.location.href = link.href;
                });
        });
    }
})();
