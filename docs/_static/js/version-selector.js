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
})();
