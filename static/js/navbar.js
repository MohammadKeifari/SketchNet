document.addEventListener("DOMContentLoaded", function () {
    const navLinks = document.querySelectorAll(".nav-link[data-page]");
    const mobileMenuBtn = document.getElementById("mobileMenuBtn");
    const navLinksContainer = document.getElementById("navLinks");

    // ===== ACTIVE LINK =====
    function setActiveLink() {
        const currentPage = document.body
            .getAttribute("data-current-page")
            .replace(/\s/g, "");
        if (!currentPage) return;
        console.log(currentPage);
        navLinks.forEach((link) => {
            console.log(link.getAttribute("data-page"));

            if (link.getAttribute("data-page") === currentPage) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });
    }

    setActiveLink();

    navLinks.forEach((link) => {
        link.addEventListener("click", function () {
            navLinks.forEach((l) => l.classList.remove("active"));
            this.classList.add("active");

            if (navLinksContainer) {
                navLinksContainer.classList.remove("open");
            }
            if (mobileMenuBtn) {
                mobileMenuBtn.classList.remove("open");
            }
        });
    });

    // ===== MOBILE MENU =====
    if (mobileMenuBtn && navLinksContainer) {
        mobileMenuBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = navLinksContainer.classList.toggle("open");
            mobileMenuBtn.classList.toggle("open", isOpen);
        });

        document.addEventListener("click", function (e) {
            if (
                !e.target.closest(".navbar-left") &&
                !e.target.closest(".mobile-menu-btn")
            ) {
                navLinksContainer.classList.remove("open");
                mobileMenuBtn.classList.remove("open");
            }
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                navLinksContainer.classList.remove("open");
                mobileMenuBtn.classList.remove("open");
            }
        });
    }

    // ===== THEME SWITCHER =====
    const savedTheme = localStorage.getItem("sketchmod-theme");
    if (savedTheme) {
        document.documentElement.setAttribute("data-theme", savedTheme);
    }

    window.setTheme = function (theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("sketchmod-theme", theme);
    };

    window.getTheme = function () {
        return document.documentElement.getAttribute("data-theme") || "light";
    };
});
