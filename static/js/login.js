document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.querySelector(".toggle-password");
    const passwordInput = document.getElementById("id_password");
    const eyeIcon = document.querySelector(".eye-icon");
    const eyeOffIcon = document.querySelector(".eye-off-icon");

    if (toggleBtn && passwordInput) {
        toggleBtn.addEventListener("click", function () {
            const isPassword = passwordInput.type === "password";

            passwordInput.type = isPassword ? "text" : "password";
            eyeIcon.style.display = isPassword ? "none" : "block";
            eyeOffIcon.style.display = isPassword ? "block" : "none";

            toggleBtn.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password",
            );
        });
    }
});
