from .base import BaseTranslator


class VisualizationTranslator(BaseTranslator):
    node_type = "visualization"

    def training_code(self, writer):
        viz = self.node
        color_mode = viz.get("colorMode", "none")
        palette = viz.get("colorPalette", [])
        min_c = viz.get("continuousMinColor", "#3b82f6")
        max_c = viz.get("continuousMaxColor", "#ef4444")

        # Count coordinate inputs
        coord_ports = [
            p for p in viz.get("inputPorts", []) if p.get("subType") == "coord"
        ]
        num_coords = len(coord_ports)
        has_color = any(
            p.get("subType") == "color" or p.get("role") == "color"
            for p in viz.get("inputPorts", [])
        )

        writer.line("# ========== VISUALIZATION ==========")
        writer.line("def visualize(X, Y=None, Z=None, colors=None):")
        writer.indent()
        writer.line('"""Visualize model data."""')
        writer.line("")

        if num_coords == 1:
            self._write_1d(writer, has_color, color_mode, palette, min_c, max_c)
        elif num_coords == 2:
            self._write_2d(writer, has_color, color_mode, palette, min_c, max_c)
        else:
            self._write_3d(writer, has_color, color_mode, palette, min_c, max_c)

        writer.dedent()
        writer.line("")
        writer.line("# Call visualization with your data")
        writer.line("# visualize(X_data, Y_data, Z_data, color_data)")
        writer.line("# Uncomment to save:")
        writer.line("# plt.savefig('visualization.png', dpi=150, bbox_inches='tight')")

    def _write_color_logic(
        self,
        writer,
        color_mode,
        palette,
        min_c,
        max_c,
        has_color,
        var_x,
        var_y=None,
        var_z=None,
    ):
        """Write the color mapping logic."""
        if not has_color:
            if var_z:
                writer.line(f"ax.scatter({var_x}, {var_y}, {var_z}, s=15)")
            elif var_y:
                writer.line(f"plt.scatter({var_x}, {var_y}, s=15)")
            else:
                writer.line(f"plt.plot({var_x})")
            return

        if color_mode == "discrete" and palette:
            colors_str = str(palette)
            writer.line(f"# Color palette: {colors_str}")
            writer.line("for i, c in enumerate(palette):")
            writer.indent()
            writer.line("mask = colors == i")
            if var_z:
                writer.line(
                    f"ax.scatter({var_x}[mask], {var_y}[mask], {var_z}[mask], c=c, label=f'Class {{i}}', s=15)"
                )
            elif var_y:
                writer.line(
                    f"plt.scatter({var_x}[mask], {var_y}[mask], c=c, label=f'Class {{i}}', s=15)"
                )
            else:
                writer.line(
                    f"plt.scatter(range(len({var_x}))[mask], {var_x}[mask], c=c, label=f'Class {{i}}', s=10)"
                )
            writer.dedent()
            if var_y or var_z:
                writer.line("plt.legend()")

        elif color_mode == "continuous":
            writer.line(f"# Color range: {min_c} -> {max_c}")
            if var_z:
                writer.line(
                    f"scatter = ax.scatter({var_x}, {var_y}, {var_z}, c=colors, cmap=plt.cm.RdYlGn, s=15)"
                )
                writer.line("fig.colorbar(scatter)")
            elif var_y:
                writer.line(
                    f"scatter = plt.scatter({var_x}, {var_y}, c=colors, cmap=plt.cm.RdYlGn, s=15)"
                )
                writer.line("plt.colorbar(scatter)")
            else:
                writer.line(
                    f"plt.scatter(range(len({var_x})), {var_x}, c=colors, cmap=plt.cm.RdYlGn, s=10)"
                )
                writer.line("plt.colorbar()")

    def _write_1d(self, writer, has_color, color_mode, palette, min_c, max_c):
        writer.line("plt.figure(figsize=(10, 6))")
        self._write_color_logic(
            writer, color_mode, palette, min_c, max_c, has_color, "X"
        )
        writer.line("plt.xlabel('Index')")
        writer.line("plt.ylabel('Value')")
        writer.line("plt.title('1D Visualization')")
        writer.line("plt.show()")

    def _write_2d(self, writer, has_color, color_mode, palette, min_c, max_c):
        writer.line("plt.figure(figsize=(10, 8))")
        self._write_color_logic(
            writer, color_mode, palette, min_c, max_c, has_color, "X", "Y"
        )
        writer.line("plt.xlabel('X')")
        writer.line("plt.ylabel('Y')")
        writer.line("plt.title('2D Visualization')")
        writer.line("plt.show()")

    def _write_3d(self, writer, has_color, color_mode, palette, min_c, max_c):
        writer.line("from mpl_toolkits.mplot3d import Axes3D")
        writer.line("fig = plt.figure(figsize=(12, 10))")
        writer.line("ax = fig.add_subplot(111, projection='3d')")
        self._write_color_logic(
            writer, color_mode, palette, min_c, max_c, has_color, "X", "Y", "Z"
        )
        writer.line("ax.set_xlabel('X')")
        writer.line("ax.set_ylabel('Y')")
        writer.line("ax.set_zlabel('Z')")
        writer.line("plt.title('3D Visualization')")
        writer.line("plt.show()")
