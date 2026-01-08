from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt, QRectF
import os

class EnhancedPatternPreview(QGraphicsView):
    """
    Enhanced SVG pattern preview widget with dynamic scaling,
    better error handling, and consistent sizing.

    Features:
    - 60px width (vs original 50px) for better visibility
    - Aspect ratio preservation during scaling
    - Loading states and error indicators
    - Consistent height across all previews
    - Better SVG rendering with fallback handling
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)  # 60x60 for enhanced visibility
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Remove scroll bars and set interaction flags
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setInteractive(False)  # No user interaction with the preview

        # Set white background initially
        self.scene.setBackgroundBrush(QColor('#FFFFFF'))

        # Cache for SVG renderers to improve performance
        self.svg_cache = {}
        self.current_svg_path = None

    def update_preview(self, svg_path=None, background_color='#FFFFFF', lithology_code=None, lithology_qualifier=None):
        """
        Update the pattern preview with new SVG and background color.

        Args:
            svg_path: Direct path to SVG file (preferred)
            background_color: Hex color string for background
            lithology_code: Alternative - lithology code to find SVG for
            lithology_qualifier: Optional qualifier for combined SVG files
        """
        # Clear current scene
        self.scene.clear()

        # Determine SVG path if not provided directly
        if svg_path is None and lithology_code is not None:
            svg_path = self.find_svg_file(lithology_code, lithology_qualifier)

        self.current_svg_path = svg_path

        # Set background color
        try:
            bg_color = QColor(background_color) if background_color else QColor('#FFFFFF')
            self.scene.setBackgroundBrush(bg_color)
        except Exception:
            # Fallback to white background
            self.scene.setBackgroundBrush(QColor('#FFFFFF'))

        # Render SVG if available
        if svg_path and os.path.exists(svg_path):
            try:
                pixmap = self._render_svg(svg_path, bg_color, self.width(), self.height())
                if pixmap:
                    self.scene.addPixmap(pixmap)
                    # Scale to fit the view while preserving aspect ratio
                    self._fit_pixmap_to_view(pixmap)
                else:
                    self._show_error_indicator("Render failed")
            except Exception as e:
                print(f"SVG rendering error for {svg_path}: {e}")
                self._show_error_indicator("Render error")
        else:
            # No SVG available - show placeholder
            self._show_placeholder()

    def _render_svg(self, svg_path, background_color, width, height):
        """
        Render SVG to pixmap with enhanced error handling and scaling.
        """
        try:
            # Get or create SVG renderer from cache
            if svg_path not in self.svg_cache:
                if os.path.exists(svg_path):
                    renderer = QSvgRenderer(svg_path)
                    if renderer.isValid():
                        self.svg_cache[svg_path] = renderer
                    else:
                        print(f"Invalid SVG file: {svg_path}")
                        return None
                else:
                    print(f"SVG file not found: {svg_path}")
                    return None

            renderer = self.svg_cache[svg_path]
            if not renderer or not renderer.isValid():
                return None

            # Calculate scaling to fit within the widget while preserving aspect ratio
            svg_size = renderer.defaultSize()
            if svg_size.isEmpty():
                # Fallback for SVGs without explicit size
                svg_size = renderer.boundsOnElement("").size().toSize()
                if svg_size.isEmpty():
                    svg_size = self.size()  # Fallback to widget size

            # Calculate scale factor to fit within widget bounds
            scale_x = width / max(svg_size.width(), 1)
            scale_y = height / max(svg_size.height(), 1)
            scale_factor = min(scale_x, scale_y, 1.0)  # Don't upscale beyond original size

            # Create pixmap with proper scaling
            scaled_width = int(svg_size.width() * scale_factor)
            scaled_height = int(svg_size.height() * scale_factor)

            pixmap = QPixmap(max(scaled_width, 1), max(scaled_height, 1))
            pixmap.fill(background_color)

            # Render SVG onto pixmap
            painter = QPainter(pixmap)
            try:
                # Scale the rendering
                painter.scale(scale_factor, scale_factor)
                renderer.render(painter)
            finally:
                painter.end()

            return pixmap

        except Exception as e:
            print(f"Error rendering SVG {svg_path}: {e}")
            return None

    def _fit_pixmap_to_view(self, pixmap):
        """Scale and center the pixmap in the view."""
        if pixmap.isNull():
            return

        # Get scene rect
        scene_rect = QRectF(pixmap.rect())
        self.scene.setSceneRect(scene_rect)

        # Fit in view while preserving aspect ratio
        self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _show_error_indicator(self, error_message="Error"):
        """Display an error indicator in the preview."""
        self.scene.clear()
        self.scene.setBackgroundBrush(QColor('#FFE6E6'))  # Light red background

        # Add error text (simplified - just color change for now)
        # Could be enhanced with text overlay if needed
        print(f"Pattern preview error: {error_message}")

    def _show_placeholder(self):
        """Show a placeholder when no SVG is available."""
        self.scene.clear()
        # Keep the background color that was set
        # Could add subtle pattern or icon here if desired

    def find_svg_file(self, lithology_code, lithology_qualifier=''):
        """
        Find the appropriate SVG file for a lithology code and qualifier.
        Enhanced version of the logic from MainWindow.
        """
        if not isinstance(lithology_code, str) or not lithology_code:
            return None

        svg_dir = os.path.join(os.getcwd(), 'src', 'assets', 'svg')

        # Construct the base prefix for the SVG file
        base_prefix = lithology_code.upper()

        # If a qualifier is provided, try to find a combined SVG first
        if lithology_qualifier and isinstance(lithology_qualifier, str):
            combined_code = (base_prefix + lithology_qualifier.upper()).strip()
            combined_filename_prefix = combined_code + ' '
            try:
                for filename in os.listdir(svg_dir):
                    if filename.upper().startswith(combined_filename_prefix):
                        return os.path.join(svg_dir, filename)
            except OSError:
                return None

        # If no combined SVG found or no qualifier provided, fall back to just the lithology code
        single_filename_prefix = base_prefix + ' '
        try:
            for filename in os.listdir(svg_dir):
                if filename.upper().startswith(single_filename_prefix):
                    return os.path.join(svg_dir, filename)
        except OSError:
            return None

        return None

    def clear_cache(self):
        """Clear the SVG renderer cache to free memory."""
        self.svg_cache.clear()

    def get_current_svg_path(self):
        """Get the currently displayed SVG path."""
        return self.current_svg_path

    def force_redraw(self):
        """Force a redraw of the current preview."""
        if self.current_svg_path:
            # Get the current background color
            bg_brush = self.scene.backgroundBrush()
            bg_color = '#FFFFFF'  # Default
            if hasattr(bg_brush, 'color'):
                bg_color = bg_brush.color().name()

            self.update_preview(self.current_svg_path, bg_color)
