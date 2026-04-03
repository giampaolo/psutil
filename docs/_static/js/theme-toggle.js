(function () {
    var KEY = 'psutil-theme';
    var html = document.documentElement;

    function setTheme(dark) {
        html.setAttribute('data-theme', dark ? 'dark' : 'light');
        localStorage.setItem(KEY, dark ? 'dark' : 'light');

        // set backgrounds directly on all three layers that RTD
        // theme hard-codes to #fcfcfc
        var bg = dark ? '#1e1e1e' : '#fcfcfc';
        ['.wy-nav-content-wrap', '.wy-nav-content', '.wy-body-for-nav']
            .forEach(function (sel) {
                var el = document.querySelector(sel);
                if (el) el.style.background = bg;
            });

        var cb = document.getElementById('theme-toggle');
        if (cb) cb.checked = dark;
    }

    // restore saved preference
    setTheme(localStorage.getItem(KEY) === 'dark');

    // wire up the checkbox (DOM is ready because script is deferred)
    var cb = document.getElementById('theme-toggle');
    if (cb) {
        cb.addEventListener('change', function () {
            setTheme(cb.checked);
        });
    }
})();
