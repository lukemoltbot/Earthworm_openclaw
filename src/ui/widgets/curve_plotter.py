from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsTextItem
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF
import numpy as np

class CurvePlotter(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self.data = None
        self.depth_column = 'DEPT' # Assuming 'DEPT' is the standardized depth column name
        self.curve_configs = [] # List of dictionaries: [{'name': 'gamma', 'min': 0, 'max': 150, 'color': '#00FF00', 'thickness': 1.5, 'inverted': False}]
        self.depth_scale = 10 # Pixels per depth unit (should match StratigraphicColumn)
        self.plot_width = 110 # Width of the plot area (must match strat scene width)

    def set_curve_configs(self, configs):
        self.curve_configs = configs
        self.draw_curves() # Redraw with new configurations

    def set_data(self, dataframe):
        self.data = dataframe
        self.draw_curves()

    def draw_curves(self):
        self.scene.clear()

        if self.data is None or self.data.empty or not self.curve_configs:
            return

        # Use the overall min/max depth for scaling, not the data's own range
        min_depth = self.min_depth if hasattr(self, 'min_depth') else self.data[self.depth_column].min()
        max_depth = self.max_depth if hasattr(self, 'max_depth') else self.data[self.depth_column].max()

        # Set scene rect to match the depth range and plot width
        # Add consistent space for X-axis labels (similar to stratigraphic column Y-axis)
        self.x_axis_height = 60  # Space for curve labels, similar to strat column's y_axis_width
        self.scene.setSceneRect(0, min_depth * self.depth_scale, self.plot_width, (max_depth - min_depth) * self.depth_scale + self.x_axis_height)

        # Draw X-axis (value scale) for each curve
        self._draw_x_axes()

        # Draw each curve
        for config in self.curve_configs:
            curve_name = config['name']
            min_value = config['min']
            max_value = config['max']
            color = config['color']

            if curve_name not in self.data.columns:
                continue

            pen = QPen(QColor(color))
            pen.setWidthF(config.get('thickness', 1.5)) # Use thickness from config, default to 1.5

            # Filter out NaN values for plotting
            plot_data = self.data[[self.depth_column, curve_name]].dropna()

            if plot_data.empty:
                continue

            # Normalize curve values to plot width
            value_range = max_value - min_value
            if value_range == 0: # Avoid division by zero
                value_range = 1.0

            points = []
            for i in range(len(plot_data)):
                depth = plot_data.iloc[i][self.depth_column]
                value = plot_data.iloc[i][curve_name]

                # Map value to x-coordinate within plot_width
                # Apply inversion if specified
                if config.get('inverted', False):
                    # If inverted, low values map to right, high values map to left
                    x_pos = ((value - min_value) / value_range) * self.plot_width
                else:
                    # Default: low values map to left, high values map to right (inverted for typical well log display)
                    x_pos = self.plot_width - ((value - min_value) / value_range) * self.plot_width
                
                y_pos = (depth - min_depth) * self.depth_scale
                points.append(QPointF(x_pos, y_pos))

            # Draw lines between points
            for i in range(len(points) - 1):
                line = QGraphicsLineItem(points[i].x(), points[i].y(), points[i+1].x(), points[i+1].y())
                line.setPen(pen)
                self.scene.addItem(line)

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)

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

    def set_depth_range(self, min_depth, max_depth):
        """Sets the vertical depth range for the plotter's view."""
        self.min_depth = min_depth
        self.max_depth = max_depth
        # Adjust scene rect to match the depth range, using current plot_width
        # The y-coordinate in sceneRect is the top-left corner, and height is positive downwards.
        # So, min_depth corresponds to the top of the view, and max_depth to the bottom.
        # We need to scale depth to scene coordinates.
        # Assuming depth_scale is pixels per depth unit.
        scene_height = (max_depth - min_depth) * self.depth_scale
        self.scene.setSceneRect(0, min_depth * self.depth_scale, self.plot_width, scene_height + self.x_axis_height)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()) # Scroll to bottom to show top of log


    def _draw_x_axes(self):
        axis_pen = QPen(Qt.GlobalColor.black)
        axis_font = QFont("Arial", 8)

        # Draw top line of the plot area (separating curves from X-axis labels)
        # Use current depth range if available, otherwise use data range
        if hasattr(self, 'min_depth') and hasattr(self, 'max_depth'):
            plot_area_top = (self.max_depth - self.min_depth) * self.depth_scale
        elif self.data is not None and not self.data.empty:
            min_depth = self.data[self.depth_column].min()
            max_depth = self.data[self.depth_column].max()
            plot_area_top = (max_depth - min_depth) * self.depth_scale
        else:
            plot_area_top = 0  # Fallback if no depth data available
        
        self.scene.addLine(0, plot_area_top, self.plot_width, plot_area_top, axis_pen)

        # Sort curves to ensure consistent stacking order (e.g., gamma first, then densities)
        # This assumes 'gamma' is always present and should be at the top.
        # If 'density' is also a primary curve, it might need special handling.
        # For now, prioritize gamma, then short_space_density, then long_space_density.
        sorted_configs = sorted(self.curve_configs, key=lambda x: (
            0 if x['name'] == 'gamma' else
            1 if x['name'] == 'short_space_density' else
            2 if x['name'] == 'long_space_density' else
            3 # Fallback for other curves
        ))

        # Position labels in the X-axis area
        if hasattr(self, 'min_depth') and hasattr(self, 'max_depth'):
            current_y_offset = (self.max_depth - self.min_depth) * self.depth_scale + 5
        elif self.data is not None and not self.data.empty:
            min_depth = self.data[self.depth_column].min()
            max_depth = self.data[self.depth_column].max()
            current_y_offset = (max_depth - min_depth) * self.depth_scale + 5
        else:
            current_y_offset = 5  # Fallback if no depth data available
        for config in sorted_configs:
            curve_name = config['name']
            min_value = config['min']
            max_value = config['max']
            color = config['color']

            # Draw min value label
            min_label = QGraphicsTextItem(f"{min_value:.0f}")
            min_label.setFont(axis_font)
            min_label.setDefaultTextColor(QColor(color))
            min_label.setPos(0, current_y_offset)
            self.scene.addItem(min_label)

            # Draw max value label
            max_label = QGraphicsTextItem(f"{max_value:.0f}")
            max_label.setFont(axis_font)
            max_label.setDefaultTextColor(QColor(color))
            max_label.setPos(self.plot_width - max_label.boundingRect().width(), current_y_offset)
            self.scene.addItem(max_label)

            # Add curve name label
            name_label = QGraphicsTextItem(curve_name)
            name_label.setFont(axis_font)
            name_label.setDefaultTextColor(QColor(color))
            name_label.setPos(self.plot_width / 2 - name_label.boundingRect().width() / 2, current_y_offset - name_label.boundingRect().height() - 5)
            self.scene.addItem(name_label)

            # Adjust offset for the next curve's labels
            current_y_offset -= (name_label.boundingRect().height() * 2 + 5)
