// On mobile, close the sidebar when tapping on the content
// area or swiping left.

document.addEventListener('DOMContentLoaded', function () {
    var content = document.querySelector(
        'section[data-toggle="wy-nav-shift"]'
    );

    if (!content)
        return;

    function closeSidebar() {
        var shifted = document.querySelectorAll(
            '[data-toggle="wy-nav-shift"].shift'
        );

        if (shifted.length) {
            shifted.forEach(function (el) {
                el.classList.remove('shift');
            });
            var rstVersions = document.querySelector(
                '[data-toggle="rst-versions"]'
            );
            if (rstVersions)
                rstVersions.classList.remove('shift');
        }
    }

    // Close on tap.
    content.addEventListener('click', function (e) {
        if (e.target.closest('.wy-nav-top'))
            return;
        closeSidebar();
    });

    // Close on left swipe (anywhere on the page).
    var touchStartX = null;

    document.addEventListener(
        'touchstart',
        function (e) {
            touchStartX = e.touches[0].clientX;
        },
        { passive: true }
    );

    document.addEventListener(
        'touchend',
        function (e) {
            if (touchStartX === null)
                return;

            var dx = e.changedTouches[0].clientX - touchStartX;
            touchStartX = null;
            if (dx < -40)
                closeSidebar();
        },
        { passive: true }
    );
});
