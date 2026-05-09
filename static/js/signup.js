document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".toggle-password").forEach((button) => {
        button.addEventListener("click", function () {
            const wrapper = this.closest(".password-wrapper");
            const passwordInput = wrapper.querySelector(".password-input");
            const eyeIcon = this.querySelector(".eye-icon");
            const eyeOffIcon = this.querySelector(".eye-off-icon");

            const isPassword = passwordInput.type === "password";

            passwordInput.type = isPassword ? "text" : "password";
            eyeIcon.style.display = isPassword ? "none" : "block";
            eyeOffIcon.style.display = isPassword ? "block" : "none";

            this.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password",
            );
        });
    });
});
