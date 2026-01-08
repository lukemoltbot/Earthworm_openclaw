import os
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPixmap, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QRectF, Qt
import numpy as np # Import numpy
from ...core.config import LITHOLOGY_COLUMN
from .svg_renderer import SvgRenderer

class StratigraphicColumn(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.column_width = 70
        self.depth_scale = 10 # Pixels per depth unit
        self.min_display_height_pixels = 2 # Minimum height for very thin units
        self.litho_svg_path = "../../assets/svg/"
        self.svg_renderer = SvgRenderer()

        self.y_axis_width = 40 # Width reserved for the Y-axis scale
        self.x_axis_height = 60 # Height reserved for X-axis (to match curve plotter)

        # Selection highlighting attributes
        self.selected_unit_index = None
        self.highlight_rect_item = None
        self.units_dataframe = None
        self.min_depth = 0.0
        self.max_depth = 100.0

    def draw_column(self, units_dataframe, min_overall_depth, max_overall_depth, separator_thickness=0.5, draw_separators=True):
        self.scene.clear()

        # Store data for highlighting functionality
        self.units_dataframe = units_dataframe.copy() if units_dataframe is not None else None
        self.min_depth = min_overall_depth
        self.max_depth = max_overall_depth

        # Use the overall min/max depths for scene scaling
        # If units_dataframe is empty, these will be used to set an empty but correctly scaled view
        min_depth_for_scene = min_overall_depth
        max_depth_for_scene = max_overall_depth

        # Adjust scene rect to include space for the Y-axis and X-axis (to match curve plotter height)
        scene_height = (max_depth_for_scene - min_depth_for_scene) * self.depth_scale + self.x_axis_height
        self.scene.setSceneRect(0, min_depth_for_scene * self.depth_scale, self.y_axis_width + self.column_width, scene_height)

        # Draw Y-axis scale
        self._draw_y_axis(min_overall_depth, max_overall_depth)

        # Draw stratigraphic units
        for index, unit in units_dataframe.iterrows():
            from_depth = unit['from_depth']
            to_depth = unit['to_depth']
            thickness = unit['thickness']
            lithology_code = unit[LITHOLOGY_COLUMN]
            lithology_qualifier = unit.get('lithology_qualifier', '')
            svg_file = unit.get('svg_path')
            bg_color = QColor(unit.get('background_color', '#FFFFFF'))

            # print(f"DEBUG (StratigraphicColumn): Drawing unit: Code={lithology_code}, Qual={lithology_qualifier}, SVG={svg_file}, Color={bg_color.name()}")

            y_start = (from_depth - min_overall_depth) * self.depth_scale
            rect_height = thickness * self.depth_scale

            # Apply minimum display height for very thin units
            if rect_height > 0 and rect_height < self.min_display_height_pixels:
                rect_height = self.min_display_height_pixels
            
            # Safety check to prevent drawing zero-height rectangles
            if rect_height <= 0:
                continue

            # Position the column to the right of the Y-axis
            rect_item = QGraphicsRectItem(self.y_axis_width, y_start, self.column_width, rect_height)
            
            # Remove the default border from the rectangle item
            rect_item.setPen(QPen(Qt.PenStyle.NoPen))

            pixmap = self.svg_renderer.render_svg(svg_file, self.column_width, int(rect_height), bg_color)
            if pixmap:
                rect_item.setBrush(QBrush(pixmap))
            else:
                rect_item.setBrush(QBrush(bg_color))
            
            self.scene.addItem(rect_item)

            # Draw a thin grey line at the bottom of each unit to act as a separator
            if draw_separators and separator_thickness > 0:
                separator_pen = QPen(QColor(Qt.GlobalColor.gray))
                separator_pen.setWidthF(separator_thickness)
                line_item = QGraphicsLineItem(self.y_axis_width, y_start + rect_height, self.y_axis_width + self.column_width, y_start + rect_height)
                line_item.setPen(separator_pen)
                self.scene.addItem(line_item)

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()) # Scroll to bottom to show top of log

    def set_zoom_level(self, zoom_factor):
        """Set zoom level (1.0 = 100% = normal fit level)."""
        if self.scene.sceneRect().isEmpty():
            return  # No scene to zoom

        # Store current zoom factor for reference
        self.current_zoom_factor = zoom_factor

        # Calculate the zoom rectangle based on the zoom factor
        # zoom_factor of 1.0 means fit to view (normal), 2.0 means zoom in (show 50% of content), etc.
        original_rect = self.scene.sceneRect()

        # For zoom_factor > 1.0, we want to zoom in (show smaller area)
        # For zoom_factor < 1.0, we want to zoom out (show larger area)
        zoom_rect = original_rect
        if zoom_factor > 1.0:
            # Zoom in: make the rectangle smaller
            new_width = original_rect.width() / zoom_factor
            new_height = original_rect.height() / zoom_factor
            center_x = original_rect.center().x()
            center_y = original_rect.center().y()
            zoom_rect.setRect(center_x - new_width/2, center_y - new_height/2, new_width, new_height)
        elif zoom_factor < 1.0:
            # Zoom out: make the rectangle larger (but still fit in view)
            scale_factor = 1.0 / zoom_factor
            new_width = original_rect.width() * scale_factor
            new_height = original_rect.height() * scale_factor
            center_x = original_rect.center().x()
            center_y = original_rect.center().y()
            zoom_rect.setRect(center_x - new_width/2, center_y - new_height/2, new_width, new_height)

        # Apply the zoom while maintaining aspect ratio
        self.fitInView(zoom_rect, Qt.AspectRatioMode.KeepAspectRatio)


    def _draw_y_axis(self, min_depth, max_depth):
        axis_pen = QPen(Qt.GlobalColor.black)
        axis_font = QFont("Arial", 8)

        # Draw the main axis line
        self.scene.addLine(self.y_axis_width, (min_depth - min_depth) * self.depth_scale, 
                           self.y_axis_width, (max_depth - min_depth) * self.depth_scale, axis_pen)

        # Determine tick intervals
        depth_range = max_depth - min_depth
        major_tick_interval = 10.0
        minor_tick_interval = 1.0

        # Adjust major tick interval for very short or very long sections
        if depth_range < 20:
            major_tick_interval = 5.0
            minor_tick_interval = 0.5
        elif depth_range > 100:
            major_tick_interval = 20.0
            minor_tick_interval = 2.0

        # Draw tick marks and labels
        current_depth = np.floor(min_depth / minor_tick_interval) * minor_tick_interval
        while current_depth <= max_depth:
            y_pos = (current_depth - min_depth) * self.depth_scale
            
            is_major_tick = (current_depth % major_tick_interval == 0)

            if is_major_tick:
                tick_length = 10
                label_offset = -30
                label_text = f"{current_depth:.0f}"
            else:
                tick_length = 5
                label_offset = -15
                label_text = "" # No label for minor ticks

            # Draw tick mark
            self.scene.addLine(self.y_axis_width - tick_length, y_pos, self.y_axis_width, y_pos, axis_pen)

            # Draw label
            if label_text:
                text_item = QGraphicsTextItem(label_text)
                text_item.setFont(axis_font)
                text_item.setPos(self.y_axis_width + label_offset, y_pos - text_item.boundingRect().height() / 2)
                self.scene.addItem(text_item)
            
            current_depth += minor_tick_interval

        # Remove the old depth labels from the units
        # The previous code for from_depth_text and to_depth_text is removed as it's replaced by the Y-axis.

        # Re-highlight the previously selected unit if data is redrawn
        if self.selected_unit_index is not None:
            self._update_highlight()

    def highlight_unit(self, unit_index):
        """Highlight the specified unit by index. Pass None to clear highlighting."""
        self.selected_unit_index = unit_index
        self._update_highlight()

    def _update_highlight(self):
        """Update the highlight rectangle over the selected unit."""
        # Remove existing highlight
        if self.highlight_rect_item is not None:
            self.scene.removeItem(self.highlight_rect_item)
            self.highlight_rect_item = None

        # Add new highlight if a unit is selected
        if self.selected_unit_index is not None and self.units_dataframe is not None:
            if 0 <= self.selected_unit_index < len(self.units_dataframe):
                unit = self.units_dataframe.iloc[self.selected_unit_index]

                from_depth = unit['from_depth']
                to_depth = unit['to_depth']
                thickness = unit['thickness']

                # Calculate position and size
                y_start = (from_depth - self.min_depth) * self.depth_scale
                rect_height = thickness * self.depth_scale

                # Apply minimum display height for very thin units
                if rect_height > 0 and rect_height < self.min_display_height_pixels:
                    rect_height = self.min_display_height_pixels

                if rect_height <= 0:
                    return

                # Create highlight rectangle (slightly larger than unit for visibility)
                highlight_rect = QGraphicsRectItem(
                    self.y_axis_width - 2, y_start - 1,
                    self.column_width + 4, rect_height + 2
                )

                # Set highlight style - thick yellow border
                highlight_pen = QPen(QColor(255, 255, 0))  # Yellow
                highlight_pen.setWidth(3)
                highlight_rect.setPen(highlight_pen)
                highlight_rect.setBrush(QBrush(Qt.BrushStyle.NoBrush))  # No fill

                # Add to scene and store reference
                self.scene.addItem(highlight_rect)
                self.highlight_rect_item = highlight_rect
