class VizGenerator:
    """Generates matplotlib visualization code."""

    def __init__(self, generator):
        self.g = generator

    def generate(self):
        viz_node = next((n for n in self.g.nodes if n["type"] == "visualization"), None)
        if not viz_node:
            return []

        color_mode = viz_node.get("colorMode", "none")
        palette = viz_node.get("colorPalette", [])
        min_color = viz_node.get("continuousMinColor", "#3b82f6")
        max_color = viz_node.get("continuousMaxColor", "#ef4444")

        lines = []
        lines.append("# ========== VISUALIZATION ==========")
        lines.append("def plot_results(train_losses, val_losses):")
        lines.append("    plt.figure(figsize=(10, 6))")
        lines.append("    plt.plot(train_losses, label='Train Loss', linewidth=2)")
        lines.append("    plt.plot(val_losses, label='Validation Loss', linewidth=2)")
        lines.append("    plt.xlabel('Epoch')")
        lines.append("    plt.ylabel('Loss')")
        lines.append("    plt.title('Training Curves')")
        lines.append("    plt.legend()")
        lines.append("    plt.grid(True, alpha=0.3)")

        if color_mode == "discrete" and palette:
            lines.append(f"    # Color palette: {palette}")
        elif color_mode == "continuous":
            lines.append(f"    # Color range: {min_color} → {max_color}")

        lines.append("    plt.show()")
        lines.append("    # Uncomment to save:")
        lines.append(
            "    # plt.savefig('training_curves.png', dpi=150, bbox_inches='tight')"
        )
        lines.append("")
        lines.append("    plot_results(train_losses, val_losses)")

        return lines
