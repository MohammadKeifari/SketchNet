// ===== THEME LOGIC =====
(function () {
    function applyTheme() {
        var html = document.documentElement;
        var theme = html.getAttribute("data-theme");

        // If no theme set or it's "system", detect device preference
        if (!theme || theme === "system" || theme === "") {
            var prefersDark = window.matchMedia(
                "(prefers-color-scheme: dark)",
            ).matches;
            html.setAttribute("data-theme", prefersDark ? "dark" : "light");
        }
    }

    // Apply on load
    applyTheme();

    // Listen for system theme changes
    window
        .matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", function () {
            var userTheme =
                document.documentElement.getAttribute("data-user-theme");
            if (!userTheme || userTheme === "system") {
                applyTheme();
            }
        });
})();
