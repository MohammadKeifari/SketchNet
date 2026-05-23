/**
 * Left toolbar management
 */

document.addEventListener("DOMContentLoaded", () => {
    const toolButtons = document.querySelectorAll(".tool-btn[data-tool]");

    toolButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            // Remove active from all
            toolButtons.forEach((b) => b.classList.remove("active"));
            // Add to clicked
            btn.classList.add("active");

            // Set tool
            const tool = btn.dataset.tool;
            SketchMod.setTool(tool);
        });
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
        // Don't trigger if typing in an input
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")
            return;

        switch (e.key.toLowerCase()) {
            case "s":
                activateTool("select");
                break;
            case "m":
                activateTool("move");
                break;
            case "d":
                activateTool("delete");
                break;
            case "h":
                activateTool("pan");
                break;
        }
    });

    function activateTool(toolName) {
        toolButtons.forEach((b) => b.classList.remove("active"));
        const btn = document.querySelector(
            `.tool-btn[data-tool="${toolName}"]`,
        );
        if (btn) {
            btn.classList.add("active");
            SketchMod.setTool(toolName);
        }
    }
});
