"""
2D Matrix Visualization for Gamma/Density Lithology Coverage Analysis
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QToolTip
)
from PyQt6.QtGui import QPainter, QBrush, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize
import numpy as np

class MatrixVisualizer(QWidget):
    """2D Matrix visualization showing gamma/density coverage combinations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lithology_rules = []
        self.gamma_bins = 30  # Number of gamma bins
        self.density_bins = 20  # Number of density bins
        self.gamma_range = (0, 300)
        self.density_range = (0, 4)
        self.cell_size = 15
        self.margin = 5
        self.label_width = 40
        self.label_height = 20
        
        # Coverage matrix: 0=gap, 1=single coverage, 2+=overlap
        self.coverage_matrix = None
        self.coverage_details = {}  # (gamma_idx, density_idx) -> list of lithology codes
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        title_label = QLabel("2D Gamma/Density Coverage Matrix")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend:"))
        
        # Gap
        gap_label = QLabel("Gap")
        gap_label.setStyleSheet("background-color: #FF6B6B; padding: 2px; border: 1px solid #666;")
        legend_layout.addWidget(gap_label)
        
        # Single coverage
        single_label = QLabel("Single")
        single_label.setStyleSheet("background-color: #4ECDC4; padding: 2px; border: 1px solid #666;")
        legend_layout.addWidget(single_label)
        
        # Overlap
        overlap_label = QLabel("Overlap")
        overlap_label.setStyleSheet("background-color: #FFE66D; padding: 2px; border: 1px solid #666;")
        legend_layout.addWidget(overlap_label)
        
        # Don't care
        dont_care_label = QLabel("Don't Care")
        dont_care_label.setStyleSheet("background-color: #CCCCCC; padding: 2px; border: 1px solid #666;")
        legend_layout.addWidget(dont_care_label)
        
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Matrix frame
        matrix_frame = QFrame()
        matrix_frame.setFrameStyle(QFrame.Shape.Box)
        matrix_layout = QVBoxLayout(matrix_frame)
        
        matrix_title = QLabel("Gamma (x) vs Density (y) Coverage")
        matrix_title.setStyleSheet("font-weight: bold;")
        matrix_layout.addWidget(matrix_title)
        
        self.matrix_canvas = MatrixCanvas(self)
        matrix_layout.addWidget(self.matrix_canvas)
        
        layout.addWidget(matrix_frame)
        layout.addStretch()

    def update_rules(self, lithology_rules):
        """Update with new lithology rules and recalculate coverage"""
        self.lithology_rules = lithology_rules
        self._calculate_coverage_matrix()
        self.matrix_canvas.update_coverage(self.coverage_matrix, self.coverage_details, self.gamma_range, self.density_range)
        self.update()

    def _calculate_coverage_matrix(self):
        """Calculate 2D coverage matrix for all gamma/density combinations"""
        if not self.lithology_rules:
            return

        # Initialize coverage matrix
        self.coverage_matrix = np.zeros((self.density_bins, self.gamma_bins), dtype=int)
        self.coverage_details = {}

        gamma_step = (self.gamma_range[1] - self.gamma_range[0]) / self.gamma_bins
        density_step = (self.density_range[1] - self.density_range[0]) / self.density_bins

        # Check each lithology rule against all gamma/density combinations
        for rule in self.lithology_rules:
            gamma_min = rule.get('gamma_min')
            gamma_max = rule.get('gamma_max')
            density_min = rule.get('density_min')
            density_max = rule.get('density_max')
            code = rule.get('code', '')

            # Skip NL rule
            if code == 'NL':
                continue

            # Check if this rule has "don't care" for gamma or density
            gamma_dont_care = gamma_min == -999.25 and gamma_max == -999.25
            density_dont_care = density_min == -999.25 and density_max == -999.25

            for density_idx in range(self.density_bins):
                density_val = self.density_range[0] + density_idx * density_step + density_step / 2
                
                for gamma_idx in range(self.gamma_bins):
                    gamma_val = self.gamma_range[0] + gamma_idx * gamma_step + gamma_step / 2

                    # Check if this combination is covered by current rule
                    covered = True
                    
                    if not gamma_dont_care:
                        covered &= gamma_min <= gamma_val <= gamma_max
                    if not density_dont_care:
                        covered &= density_min <= density_val <= density_max

                    if covered:
                        # Update coverage matrix
                        if gamma_dont_care or density_dont_care:
                            # Mark as "don't care" coverage (special value)
                            if self.coverage_matrix[density_idx, gamma_idx] == 0:
                                self.coverage_matrix[density_idx, gamma_idx] = -1  # Don't care
                        else:
                            # Normal coverage
                            self.coverage_matrix[density_idx, gamma_idx] += 1

                        # Store coverage details
                        key = (gamma_idx, density_idx)
                        if key not in self.coverage_details:
                            self.coverage_details[key] = []
                        self.coverage_details[key].append(code)

        # Convert "don't care" areas to proper values for visualization
        for density_idx in range(self.density_bins):
            for gamma_idx in range(self.gamma_bins):
                if self.coverage_matrix[density_idx, gamma_idx] == -1:
                    # If don't care but also has normal coverage, use normal coverage
                    key = (gamma_idx, density_idx)
                    if key in self.coverage_details and len(self.coverage_details[key]) > 1:
                        # Count only non-dont-care rules
                        normal_count = sum(1 for rule in self.lithology_rules 
                                         if rule.get('code') in self.coverage_details[key]
                                         and not (rule.get('gamma_min') == -999.25 and rule.get('gamma_max') == -999.25)
                                         and not (rule.get('density_min') == -999.25 and rule.get('density_max') == -999.25))
                        self.coverage_matrix[density_idx, gamma_idx] = normal_count if normal_count > 0 else -1

    def get_gap_analysis(self):
        """Return analysis of coverage gaps"""
        if self.coverage_matrix is None:
            return "No analysis available"

        total_cells = self.gamma_bins * self.density_bins
        gap_cells = np.sum(self.coverage_matrix == 0)
        single_cells = np.sum(self.coverage_matrix == 1)
        overlap_cells = np.sum(self.coverage_matrix >= 2)
        dont_care_cells = np.sum(self.coverage_matrix == -1)

        analysis = f"Coverage Analysis:\n"
        analysis += f"Total combinations: {total_cells}\n"
        analysis += f"Gaps (no coverage): {gap_cells} ({gap_cells/total_cells:.1%})\n"
        analysis += f"Single coverage: {single_cells} ({single_cells/total_cells:.1%})\n"
        analysis += f"Overlaps: {overlap_cells} ({overlap_cells/total_cells:.1%})\n"
        analysis += f"Don't care areas: {dont_care_cells} ({dont_care_cells/total_cells:.1%})\n"

        # Find largest gap areas
        gap_areas = []
        for density_idx in range(self.density_bins):
            for gamma_idx in range(self.gamma_bins):
                if self.coverage_matrix[density_idx, gamma_idx] == 0:
                    gap_areas.append((gamma_idx, density_idx))

        if gap_areas:
            analysis += "\nMajor Gap Areas:"
            # Group contiguous gaps
            # Simple implementation - just list some representative gaps
            for i, (gamma_idx, density_idx) in enumerate(gap_areas[:5]):  # Show first 5
                gamma_val = self.gamma_range[0] + gamma_idx * (self.gamma_range[1] - self.gamma_range[0]) / self.gamma_bins
                density_val = self.density_range[0] + density_idx * (self.density_range[1] - self.density_range[0]) / self.density_bins
                analysis += f"\n- Gamma ~{gamma_val:.0f}, Density ~{density_val:.1f}"

        return analysis


class MatrixCanvas(QWidget):
    """Canvas for drawing the 2D coverage matrix"""

    def __init__(self, parent):
        super().__init__(parent)
        self.coverage_matrix = None
        self.coverage_details = {}
        self.cell_size = 15
        self.margin = 5
        self.label_width = 40
        self.label_height = 20
        self.gamma_range = (0, 300)
        self.density_range = (0, 4)
        
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def update_coverage(self, coverage_matrix, coverage_details, gamma_range=None, density_range=None):
        """Update the coverage data"""
        self.coverage_matrix = coverage_matrix
        self.coverage_details = coverage_details
        if gamma_range:
            self.gamma_range = gamma_range
        if density_range:
            self.density_range = density_range
        self.update()

    def paintEvent(self, event):
        """Paint the 2D matrix"""
        if self.coverage_matrix is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate drawing area
        draw_width = self.width() - self.label_width
        draw_height = self.height() - self.label_height
        
        # Draw axes labels
        self._draw_axes_labels(painter, draw_width, draw_height)
        
        # Draw grid
        rows, cols = self.coverage_matrix.shape
        cell_width = draw_width / cols
        cell_height = draw_height / rows
        
        for row in range(rows):
            for col in range(cols):
                coverage = self.coverage_matrix[row, col]
                
                # Determine cell color based on coverage
                if coverage == 0:
                    color = QColor("#FF6B6B")  # Red for gaps
                elif coverage == 1:
                    color = QColor("#4ECDC4")  # Teal for single coverage
                elif coverage >= 2:
                    color = QColor("#FFE66D")  # Yellow for overlaps
                elif coverage == -1:
                    color = QColor("#CCCCCC")  # Gray for "don't care"
                else:
                    color = QColor("#FFFFFF")
                
                # Draw cell
                x = self.label_width + col * cell_width
                y = self.label_height + row * cell_height
                cell_rect = QRectF(x, y, cell_width, cell_height)
                
                painter.fillRect(cell_rect, QBrush(color))
                painter.setPen(QPen(QColor("#666666"), 0.5))
                painter.drawRect(cell_rect)

    def _draw_axes_labels(self, painter, draw_width, draw_height):
        """Draw axis labels"""
        painter.setPen(QColor("#333333"))
        font = QFont()
        font.setPixelSize(10)
        painter.setFont(font)
        
        # X-axis labels (Gamma)
        cols = self.coverage_matrix.shape[1] if self.coverage_matrix is not None else 10
        for i in range(0, cols + 1, max(1, cols // 5)):
            gamma_val = self.gamma_range[0] + i * (self.gamma_range[1] - self.gamma_range[0]) / cols
            x = self.label_width + i * draw_width / cols
            painter.drawText(int(x - 15), self.label_height - 5, f"{gamma_val:.0f}")
        
        # Y-axis labels (Density)
        rows = self.coverage_matrix.shape[0] if self.coverage_matrix is not None else 10
        for i in range(0, rows + 1, max(1, rows // 5)):
            density_val = self.density_range[0] + i * (self.density_range[1] - self.density_range[0]) / rows
            y = self.label_height + i * draw_height / rows
            painter.drawText(5, int(y + 5), f"{density_val:.1f}")
        
        # Axis titles
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(self.label_width + draw_width / 2 - 30), 15, "Gamma Ray")
        painter.save()
        painter.translate(20, self.label_height + draw_height / 2 + 30)
        painter.rotate(-90)
        painter.drawText(0, 0, "Density")
        painter.restore()

    def mouseMoveEvent(self, event):
        """Show tooltip with coverage details"""
        if self.coverage_matrix is None:
            return

        pos = event.pos()
        draw_width = self.width() - self.label_width
        draw_height = self.height() - self.label_height
        
        rows, cols = self.coverage_matrix.shape
        cell_width = draw_width / cols
        cell_height = draw_height / rows
        
        # Check if mouse is in drawing area
        if (pos.x() > self.label_width and pos.y() > self.label_height and
            pos.x() < self.width() and pos.y() < self.height()):
            
            col = int((pos.x() - self.label_width) / cell_width)
            row = int((pos.y() - self.label_height) / cell_height)
            
            if 0 <= row < rows and 0 <= col < cols:
                coverage = self.coverage_matrix[row, col]
                key = (col, row)
                
                gamma_val = self.gamma_range[0] + col * (self.gamma_range[1] - self.gamma_range[0]) / cols
                density_val = self.density_range[0] + row * (self.density_range[1] - self.density_range[0]) / rows
                
                tooltip = f"Gamma: {gamma_val:.1f}, Density: {density_val:.2f}\n"
                
                if coverage == 0:
                    tooltip += "Status: GAP (No coverage)"
                elif coverage == 1:
                    lithos = self.coverage_details.get(key, [])
                    tooltip += f"Status: Single coverage\nLithology: {', '.join(lithos)}"
                elif coverage >= 2:
                    lithos = self.coverage_details.get(key, [])
                    tooltip += f"Status: Overlap ({coverage} lithologies)\nLithologies: {', '.join(lithos)}"
                elif coverage == -1:
                    lithos = self.coverage_details.get(key, [])
                    tooltip += f"Status: Don't care coverage\nLithologies: {', '.join(lithos)}"
                
                QToolTip.showText(event.globalPosition().toPoint(), tooltip)
                return
        
        QToolTip.hideText()