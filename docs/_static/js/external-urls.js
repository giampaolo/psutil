// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Open all external URLs in a new tab.

document.addEventListener("DOMContentLoaded", function () {
	document.querySelectorAll("a[href^='http']").forEach(a => {
		if (a.hostname !== location.hostname) {
			a.target = "_blank";
			a.rel = "noopener noreferrer";
		}
	});
});
//
