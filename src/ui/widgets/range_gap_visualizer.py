"""
Widget for visualizing gaps in lithology ranges (GRDE and DENB)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QToolTip, QTabWidget
)
from PyQt6.QtGui import QPainter, QBrush, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize
import sys

# Import the new 2D matrix visualizer
try:
    from .matrix_visualizer import MatrixVisualizer
except ImportError:
    MatrixVisualizer = None

class RangeGapVisualizer(QWidget):
    """Widget that visually displays range coverage and gaps for lithology settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.range_analyzer = None
        self.gamma_covered = []
        self.gamma_gaps = []
        self.density_covered = []
        self.density_gaps = []

        self.gamma_range = (0, 300)  # GRDE range
        self.density_range = (0, 4)  # DENB range

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout with tabs for 1D and 2D visualization"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        title_label = QLabel("Lithology Range Coverage Analysis")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tab 1: 1D Range Visualization (original)
        tab_1d = QWidget()
        tab_1d_layout = QVBoxLayout(tab_1d)
        
        # Gamma ray section
        gamma_frame = QFrame()
        gamma_frame.setFrameStyle(QFrame.Shape.Box)
        gamma_layout = QVBoxLayout(gamma_frame)

        gamma_title = QLabel("Gamma Ray (GRDE) Coverage")
        gamma_title.setStyleSheet("font-weight: bold;")
        gamma_layout.addWidget(gamma_title)

        self.gamma_canvas = RangeCanvas(self, "GRDE")
        gamma_layout.addWidget(self.gamma_canvas)

        tab_1d_layout.addWidget(gamma_frame)

        # Density section
        density_frame = QFrame()
        density_frame.setFrameStyle(QFrame.Shape.Box)
        density_layout = QVBoxLayout(density_frame)

        density_title = QLabel("Density (DENB) Coverage")
        density_title.setStyleSheet("font-weight: bold;")
        density_layout.addWidget(density_title)

        self.density_canvas = RangeCanvas(self, "DENB")
        density_layout.addWidget(self.density_canvas)

        tab_1d_layout.addWidget(density_frame)
        tab_1d_layout.addStretch()

        self.tab_widget.addTab(tab_1d, "1D Ranges")

        # Tab 2: 2D Matrix Visualization (new)
        if MatrixVisualizer is not None:
            self.matrix_visualizer = MatrixVisualizer()
            self.tab_widget.addTab(self.matrix_visualizer, "2D Matrix")
        else:
            # Fallback if matrix visualizer not available
            fallback_tab = QWidget()
            fallback_layout = QVBoxLayout(fallback_tab)
            fallback_label = QLabel("2D Matrix visualization not available")
            fallback_layout.addWidget(fallback_label)
            self.tab_widget.addTab(fallback_tab, "2D Matrix")

        layout.addStretch()

    def set_range_analyzer(self, analyzer):
        """Set the range analyzer instance"""
        self.range_analyzer = analyzer

    def update_ranges(self, gamma_covered, gamma_gaps, density_covered, density_gaps, use_overlaps=False, lithology_rules=None):
        """Update the visualization with new range data"""
        self.gamma_covered = gamma_covered
        self.density_covered = density_covered
        self.gamma_gaps = gamma_gaps
        self.density_gaps = density_gaps

        # Update gamma canvas
        self.gamma_canvas.set_ranges(gamma_covered, gamma_gaps,
                                   self.gamma_range[0], self.gamma_range[1], use_overlaps)

        # Update density canvas
        self.density_canvas.set_ranges(density_covered, density_gaps,
                                     self.density_range[0], self.density_range[1], use_overlaps)

        # Update 2D matrix visualizer if available
        if hasattr(self, 'matrix_visualizer') and lithology_rules is not None:
            self.matrix_visualizer.update_rules(lithology_rules)

        # Update display
        self.update()


class RangeCanvas(QWidget):
    """Canvas widget for drawing range visualization"""

    def __init__(self, parent, range_type):
        super().__init__(parent)
        self.range_type = range_type  # "GRDE" or "DENB"
        self.covered_ranges = []
        self.gap_ranges = []
        self.global_min = 0
        self.global_max = 100
        self.margin = 5
        self.bar_height = 30
        self.text_margin = 5
        self.label_width = 60

        # Set minimum size
        self.setMinimumHeight(self.bar_height + 2 * self.margin)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_ranges(self, covered_ranges, gap_ranges, global_min, global_max, use_overlaps=False):
        """Update the ranges to display"""
        self.covered_ranges = covered_ranges
        self.gap_ranges = gap_ranges
        self.global_min = global_min
        self.global_max = global_max
        self.use_overlaps = use_overlaps
        self.update()

    def sizeHint(self):
        """Provide size hint for layout manager"""
        return QSize(600, self.bar_height + 2 * self.margin)

    def minimumSizeHint(self):
        """Provide minimum size hint"""
        return QSize(300, self.bar_height + 2 * self.margin)

    def paintEvent(self, event):
        """Paint the range visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate drawing area
        draw_width = self.width() - self.label_width
        draw_height = self.bar_height

        # Draw background (global range)
        background_rect = QRectF(self.label_width, self.margin, draw_width, draw_height)
        painter.fillRect(background_rect, QBrush(QColor("#E0E0E0")))  # Light gray background

        # Draw range boundaries
        boundary_pen = QPen(QColor("#666666"), 1)
        painter.setPen(boundary_pen)
        painter.drawRect(background_rect)

        # Draw covered ranges - handle overlapping ranges differently
        if self.use_overlaps and self.covered_ranges:
            self._draw_overlapping_ranges(painter, draw_width, draw_height)
        else:
            for range_info in self.covered_ranges:
                self._draw_range_segment(painter, range_info, "covered", draw_width, draw_height)

        # Draw gap ranges
        for gap in self.gap_ranges:
            self._draw_range_segment(painter, gap, "gap", draw_width, draw_height)

        # Draw scale labels
        painter.setPen(QColor("#333333"))
        font = QFont()
        font.setPixelSize(10)
        painter.setFont(font)

        # Min value label
        min_text = "0"
        if self.range_type == "DENB":
            min_text = "0"
        painter.drawText(self.label_width - self.text_margin - painter.fontMetrics().horizontalAdvance(min_text),
                        int(self.margin + draw_height + 12), min_text)

        # Max value label
        max_text = "300"
        if self.range_type == "DENB":
            max_text = "4"

        painter.drawText(self.label_width + draw_width + self.text_margin,
                        int(self.margin + draw_height + 12), max_text)

    def _calculate_contrast_text_color(self, bg_color):
        """Calculate high contrast text color based on background brightness"""
        bg_qcolor = QColor(bg_color)
        # Calculate perceived brightness using WCAG formula
        r = bg_qcolor.red()
        g = bg_qcolor.green()
        b = bg_qcolor.blue()
        # Convert to linear color space approximation
        r_linear = r / 255.0
        g_linear = g / 255.0
        b_linear = b / 255.0

        # For newer standards use: 0.2126*R + 0.7152*G + 0.0722*B
        # For older standards use: 0.299*R + 0.587*G + 0.114*B
        brightness = 0.299 * r_linear + 0.587 * g_linear + 0.114 * b_linear

        # Return white text for dark backgrounds, black for light
        return "#FFFFFF" if brightness < 0.5 else "#000000"

    def _draw_overlapping_ranges(self, painter, draw_width, draw_height):
        """Draw overlapping ranges with layered transparency"""
        # Create a list to track which areas have been drawn to identify overlaps
        pixel_list = []

        # First pass: collect all segments and check for overlaps
        for range_info in self.covered_ranges:
            pixels_per_unit = draw_width / (self.global_max - self.global_min)
            x_start = self.label_width + (range_info['min'] - self.global_min) * pixels_per_unit
            x_end = self.label_width + (range_info['max'] - self.global_min) * pixels_per_unit

            pixel_list.append({
                'x_start': x_start,
                'x_end': x_end,
                'color': QColor(range_info.get('background_color', '#FFFFFF')),
                'code': range_info.get('code', ''),
                'name': range_info.get('name', 'Unknown'),
                'z_index': 0,  # Layer index for drawing order
                'overlaps': []  # List of overlapping segments
            })

        # Second pass: identify overlapping segments
        for i, segment in enumerate(pixel_list):
            for j, other_segment in enumerate(pixel_list):
                if i != j:
                    # Check if segments overlap
                    if (segment['x_start'] < other_segment['x_end'] and
                        segment['x_end'] > other_segment['x_start']):
                        segment['z_index'] = 1  # Mark as overlapping
                        segment['overlaps'].append(other_segment)
                        other_segment['z_index'] = 1

        # Third pass: draw segments in layers (background first, then foreground)
        for layer in [0, 1]:  # Layer 0: non-overlapping, Layer 1: overlapping
            layer_segments = [s for s in pixel_list if s['z_index'] == layer]

            for segment in layer_segments:
                # Calculate segment rectangle
                segment_width = segment['x_end'] - segment['x_start']
                if segment_width <= 0:
                    continue

                segment_rect = QRectF(segment['x_start'], self.margin, segment_width, draw_height)

                # Apply transparency if this segment overlaps
                alpha = 0.7 if segment['z_index'] > 0 else 1.0
                color_with_alpha = QColor(segment['color'])
                color_with_alpha.setAlphaF(alpha)

                # Draw the segment with appropriate alpha
                painter.fillRect(segment_rect, QBrush(color_with_alpha))

                # Draw border
                border_pen = QPen(QColor("#666666"), 1)
                painter.setPen(border_pen)
                painter.drawRect(segment_rect)

                # Draw label if segment is wide enough and this is the top layer
                if segment_width > 40:
                    font = QFont()
                    font.setPixelSize(9)
                    painter.setFont(font)

                    # Calculate the best text color based on the blended color
                    base_color = segment['color']
                    background_color = QColor(base_color)
                    if segment['z_index'] > 0:
                        # For overlapping segments, blend with gray to approximate visual effect
                        background_color.setRgbF(
                            min(1.0, background_color.redF() + alpha * 0.2),
                            min(1.0, background_color.greenF() + alpha * 0.2),
                            min(1.0, background_color.blueF() + alpha * 0.2),
                        )

                    contrasting_color = self._calculate_contrast_text_color(background_color.name())
                    painter.setPen(QColor(contrasting_color))

                    # Show code or overlapping indicator
                    if segment['z_index'] > 0:
                        # For overlapping segments, show a special marker
                        all_codes = [segment['code']] + [overlap['code'] for overlap in segment['overlaps']]
                        all_codes = [code for code in all_codes if code]  # Remove empty codes
                        if all_codes:
                            label = "+".join(set(all_codes[:3]))  # Show up to 3 codes
                        else:
                            label = "*"
                    else:
                        label = segment['code'] if segment['code'] else "-"

                    text_width = painter.fontMetrics().horizontalAdvance(label)

                    # Center the label in the segment
                    if text_width < segment_width - 4:
                        text_x = segment['x_start'] + (segment_width - text_width) / 2
                        text_y = int(self.margin + draw_height/2 + 3)
                        painter.drawText(int(text_x), text_y, label)

        # Fourth pass: draw gaps on top
        for gap in self.gap_ranges:
            self._draw_range_segment(painter, gap, "gap", draw_width, draw_height)

    def _draw_range_segment(self, painter, range_info, segment_type, draw_width, draw_height):
        """Draw a single range segment"""
        if segment_type == "covered":
            # range_info is a dict with min, max, name, code, background_color
            min_val = range_info['min']
            max_val = range_info['max']
            color = QColor(range_info.get('background_color', '#FFFFFF'))
            name = range_info.get('name', 'Unknown')
            code = range_info.get('code', '')
        else:
            # range_info is a tuple (min, max)
            min_val = range_info[0]
            max_val = range_info[1]
            color = QColor("#FF6B6B")  # Red for gaps
            name = f"Gap {min_val:.1f}-{max_val:.1f}"

        # Calculate pixel positions
        pixels_per_unit = draw_width / (self.global_max - self.global_min)
        x_start = self.label_width + (min_val - self.global_min) * pixels_per_unit
        x_end = self.label_width + (max_val - self.global_min) * pixels_per_unit

        segment_width = x_end - x_start
        segment_rect = QRectF(x_start, self.margin, segment_width, draw_height)

        # Draw the segment
        painter.fillRect(segment_rect, QBrush(color))

        # Draw border
        border_pen = QPen(QColor("#666666"), 1)
        painter.setPen(border_pen)
        painter.drawRect(segment_rect)

        # Draw label if segment is wide enough
        if segment_width > 40:
            font = QFont()
            font.setPixelSize(9)
            painter.setFont(font)

            # Use contrasting color for text based on background
            if segment_type == "covered":
                contrasting_color = self._calculate_contrast_text_color(range_info.get('background_color', '#FFFFFF'))
                painter.setPen(QColor(contrasting_color))
            else:
                # For gaps, use white text since gap background is red
                painter.setPen(QColor("#FFFFFF"))

            if segment_type == "covered":
                label = f"{code}" if code else "-"
            else:
                label = "-"  # Show dash for gaps

            text_width = painter.fontMetrics().horizontalAdvance(label)

            # Center the label in the segment
            if text_width < segment_width - 4:
                text_x = x_start + (segment_width - text_width) / 2
                text_y = int(self.margin + draw_height/2 + 3)
                painter.drawText(int(text_x), text_y, label)

        # Store rectangle for tooltip
        self._store_tooltip_rect(segment_rect, name)

    def _store_tooltip_rect(self, rect, text):
        """Store rectangle for tooltip handling - simplified for now"""

    def mouseMoveEvent(self, event):
        """Handle mouse movement for tooltips"""
        # Find which segment the mouse is over
        mouse_pos = event.pos()

        if self.use_overlaps and self.covered_ranges:
            # Handle overlapping ranges - find all segments at this position
            overlapping_segments = []

            for i, range_info in enumerate(self.covered_ranges):
                segment_rect = self._get_segment_rect(range_info)
                if segment_rect.contains(QPointF(mouse_pos)):
                    overlapping_segments.append({
                        'index': i,
                        'range_info': range_info,
                        'rect': segment_rect
                    })

            if overlapping_segments:
                tooltip = self._format_overlapping_tooltip(overlapping_segments)
                QToolTip.showText(event.globalPosition().toPoint(), tooltip)
                return

        else:
            # Handle non-overlapping ranges normally
            for range_info in self.covered_ranges:
                segment_rect = self._get_segment_rect(range_info)
                if segment_rect.contains(QPointF(mouse_pos)):
                    tooltip = self._format_covered_tooltip(range_info)
                    QToolTip.showText(event.globalPosition().toPoint(), tooltip)
                    return

        # Check gaps
        for gap in self.gap_ranges:
            segment_rect = self._get_gap_rect(gap)
            if segment_rect.contains(QPointF(mouse_pos)):
                tooltip = self._format_gap_tooltip(gap)
                QToolTip.showText(event.globalPosition().toPoint(), tooltip)
                return

        # Hide tooltip if not over any segment
        QToolTip.hideText()

    def _get_segment_rect(self, range_info):
        """Get rectangle for a covered range segment"""
        pixels_per_unit = (self.width() - self.label_width) / (self.global_max - self.global_min)
        x_start = self.label_width + (range_info['min'] - self.global_min) * pixels_per_unit
        x_end = self.label_width + (range_info['max'] - self.global_min) * pixels_per_unit
        return QRectF(x_start, self.margin, x_end - x_start, self.bar_height)

    def _get_gap_rect(self, gap):
        """Get rectangle for a gap segment"""
        pixels_per_unit = (self.width() - self.label_width) / (self.global_max - self.global_min)
        x_start = self.label_width + (gap[0] - self.global_min) * pixels_per_unit
        x_end = self.label_width + (gap[1] - self.global_min) * pixels_per_unit
        return QRectF(x_start, self.margin, x_end - x_start, self.bar_height)

    def _format_covered_tooltip(self, range_info):
        """Format tooltip for covered range"""
        return f"{range_info.get('name', 'Unknown')} ({range_info.get('code', '')})\n" \
               f"Range: {range_info['min']:.1f} - {range_info['max']:.1f}"

    def _format_overlapping_tooltip(self, overlapping_segments):
        """Format tooltip for overlapping range segments"""
        if not overlapping_segments:
            return ""

        # Sort segments by min value for consistent display
        sorted_segments = sorted(overlapping_segments, key=lambda s: s['range_info']['min'])

        tooltip_lines = ["Overlapping Lithologies:"]
        tooltip_lines.append("=" * 25)

        for segment in sorted_segments:
            range_info = segment['range_info']
            name = range_info.get('name', 'Unknown')
            code = range_info.get('code', '')
            min_val = range_info['min']
            max_val = range_info['max']

            tooltip_lines.append(f"{name} ({code})")
            tooltip_lines.append(f"  Range: {min_val:.1f} - {max_val:.1f}")

        # Add gap information if any gaps exist
        if self.gap_ranges:
            active_gaps = []
            # Find gaps in the overlapping area
            min_overlap = min(s['range_info']['min'] for s in sorted_segments)
            max_overlap = max(s['range_info']['max'] for s in sorted_segments)

            for gap in self.gap_ranges:
                if gap[0] >= min_overlap and gap[1] <= max_overlap:
                    active_gaps.append(gap)

            if active_gaps:
                tooltip_lines.append("")
                tooltip_lines.append("Gaps in overlap area:")
                for gap in active_gaps:
                    tooltip_lines.append(f"  Gap: {gap[0]:.1f} - {gap[1]:.1f}")

        return "\n".join(tooltip_lines)

    def _format_gap_tooltip(self, gap):
        """Format tooltip for gap"""
        return f"Gap: No lithology covers\n" \
               f"Range: {gap[0]:.1f} - {gap[1]:.1f}"
