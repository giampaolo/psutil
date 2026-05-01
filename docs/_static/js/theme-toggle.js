// Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

(function () {
    var KEY = 'psutil-theme';
    var html = document.documentElement;

    function setTheme(dark) {
        html.setAttribute('data-theme', dark ? 'dark' : 'light');
        localStorage.setItem(KEY, dark ? 'dark' : 'light');

        // clear any inline background styles so CSS variables take over
        ['.wy-nav-content-wrap', '.wy-nav-content', '.wy-body-for-nav']
            .forEach(function (sel) {
                var el = document.querySelector(sel);
                if (el) el.style.background = '';
            });

        var icon = document.getElementById('theme-icon');
        if (icon) icon.className = dark ? 'fa fa-sun-o' : 'fa fa-moon-o';
    }

    // restore saved preference
    setTheme(localStorage.getItem(KEY) === 'dark');

    // wire up the toggle button (DOM is ready because script is deferred)
    var btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.addEventListener('click', function () {
            setTheme(html.getAttribute('data-theme') !== 'dark');
        });
    }

    // Shift+D: toggle dark mode.
    document.addEventListener('keydown', function (e) {
        var tag = document.activeElement && document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA')
            return;
        if (e.shiftKey && e.key === 'D')
            setTheme(html.getAttribute('data-theme') !== 'dark');
    });
})();
