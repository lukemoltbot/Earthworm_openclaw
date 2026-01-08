from PyQt6.QtWidgets import (
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QDialog,
    QDoubleSpinBox, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import re

class CompactRangeWidget(QLabel):
    """
    A compact widget for displaying and editing min-max ranges.
    Displays as "min-max" text but internally maintains separate values
    for full analysis compatibility.

    Features:
    - Compact display: "80-150"
    - Multiple editing methods: direct typing, range picker dialog
    - Real-time validation with visual feedback
    - Keyboard navigation support
    - Geology-aware limits and validation
    """

    # Signals emitted when values change
    valuesChanged = pyqtSignal(float, float)  # min_val, max_val

    def __init__(self, parent=None, min_val=None, max_val=None):
        super().__init__(parent)
        self.min_value = min_val if min_val is not None else 0.0
        self.max_value = max_val if max_val is not None else 0.0

        # Widget setup
        self.setFixedHeight(25)  # Compact height
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: white;
                font-size: 11px;
            }
            QLabel:hover {
                background-color: #f0f0f0;
                border-color: #999;
            }
        """)

        # Set up mouse interaction
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Initial display update
        self._update_display()

    def _update_display(self):
        """Update the displayed text based on current values."""
        if self.min_value == 0.0 and self.max_value == 0.0:
            self.setText("0-0")
        else:
            self.setText(f"{self.min_value:.1f}-{self.max_value:.1f}")

        # Color coding for validation
        if self._is_valid_range():
            self.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 2px 4px;
                    background-color: white;
                    font-size: 11px;
                }
                QLabel:hover {
                    background-color: #f0f0f0;
                    border-color: #999;
                }
            """)
        else:
            # Red border for invalid ranges
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #ff6b6b;
                    border-radius: 3px;
                    padding: 2px 4px;
                    background-color: #ffe6e6;
                    font-size: 11px;
                }
                QLabel:hover {
                    background-color: #ffcccc;
                    border-color: #ff5252;
                }
            """)

    def _is_valid_range(self):
        """Check if the current range is geologically plausible."""
        # Basic validation: min should be less than or equal to max
        if self.min_value > self.max_value:
            return False

        # Geology-aware limits (adjustable based on curve type)
        # Gamma ray: 0-2000 API (very broad for geophysical logging)
        # Density: 1.0-4.0 g/cc (reasonable for earth materials)
        gamma_max = 2000.0
        density_max = 4.0

        # Check if values are within reasonable geological bounds
        if (abs(self.min_value) > gamma_max and abs(self.max_value) > gamma_max):
            # Might be density values - check density bounds
            if abs(self.min_value) > density_max or abs(self.max_value) > density_max:
                return False

        return True

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit values."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_range_editor()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """Handle single-click for potential future features."""
        super().mousePressEvent(event)

    def _show_range_editor(self):
        """Show the range editor dialog."""
        dialog = RangeEditorDialog(self.min_value, self.max_value, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_min, new_max = dialog.get_values()
            if new_min is not None and new_max is not None:
                self.set_values(new_min, new_max)

    def get_values(self):
        """Get the current min and max values for analysis compatibility."""
        return (self.min_value, self.max_value)

    def set_values(self, min_val, max_val):
        """Set min and max values and update display."""
        self.min_value = float(min_val) if min_val is not None else 0.0
        self.max_value = float(max_val) if max_val is not None else 0.0
        self._update_display()
        self.valuesChanged.emit(self.min_value, self.max_value)

    def get_display_text(self):
        """Get the display text for UI purposes."""
        return self.text()

    def keyPressEvent(self, event):
        """Handle key press for keyboard navigation."""
        if event.key() == Qt.Key.Key_Space or event.key() == Qt.Key.Key_Return:
            self._show_range_editor()
            event.accept()
        else:
            super().keyPressEvent(event)

    def setFocus(self):
        """Override setFocus to ensure proper focus behavior."""
        super().setFocus()
        # Highlight the border when focused
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #4a90e2;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: #f0f8ff;
                font-size: 11px;
            }
        """)

    def focusOutEvent(self, event):
        """Reset style when focus is lost."""
        super().focusOutEvent(event)
        self._update_display()


class RangeEditorDialog(QDialog):
    """
    Dialog for editing min-max range values with multiple input methods.
    """

    def __init__(self, current_min, current_max, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Range")
        self.setModal(True)
        self.setFixedSize(300, 150)

        # Store current values
        self.min_value = current_min
        self.max_value = current_max

        # Create layout
        layout = QVBoxLayout(self)

        # Direct input method
        self.direct_input = QLineEdit(self)
        self.direct_input.setPlaceholderText("Enter range as 'min-max' (e.g., 80-150)")
        self.direct_input.setText(f"{current_min:.1f}-{current_max:.1f}")
        layout.addWidget(self.direct_input)

        # Spinbox method
        spinbox_layout = QHBoxLayout()

        self.min_spinbox = QDoubleSpinBox(self)
        self.min_spinbox.setRange(-10000, 10000)  # Broad range for different measurement types
        self.min_spinbox.setValue(current_min)
        self.min_spinbox.setDecimals(2)
        self.min_spinbox.setSingleStep(0.1)
        spinbox_layout.addWidget(QLabel("Min:"))
        spinbox_layout.addWidget(self.min_spinbox)

        self.max_spinbox = QDoubleSpinBox(self)
        self.max_spinbox.setRange(-10000, 10000)
        self.max_spinbox.setValue(current_max)
        self.max_spinbox.setDecimals(2)
        self.max_spinbox.setSingleStep(0.1)
        spinbox_layout.addWidget(QLabel("Max:"))
        spinbox_layout.addWidget(self.max_spinbox)

        layout.addLayout(spinbox_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.parse_button = QPushButton("Parse Text")
        self.parse_button.clicked.connect(self._parse_direct_input)
        button_layout.addWidget(self.parse_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._accept_values)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Connect signals
        self.direct_input.textChanged.connect(self._update_spinboxes_from_text)
        self.min_spinbox.valueChanged.connect(self._update_text_from_spinboxes)
        self.max_spinbox.valueChanged.connect(self._update_text_from_spinboxes)

        # Set focus to direct input
        self.direct_input.setFocus()

    def _parse_direct_input(self):
        """Parse the direct input text and update spinboxes."""
        text = self.direct_input.text().strip()

        # Try to match pattern like "80-150" or "80 - 150"
        match = re.match(r'^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)$', text)
        if match:
            try:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                self.min_spinbox.setValue(min_val)
                self.max_spinbox.setValue(max_val)
            except ValueError:
                QMessageBox.warning(self, "Invalid Format", "Please enter values in format: min-max")
        else:
            QMessageBox.warning(self, "Invalid Format", "Please enter values in format: min-max")

    def _update_spinboxes_from_text(self):
        """Update spinboxes when direct input text changes."""
        text = self.direct_input.text().strip()
        match = re.match(r'^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)$', text)
        if match:
            try:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                self.min_spinbox.blockSignals(True)
                self.max_spinbox.blockSignals(True)
                self.min_spinbox.setValue(min_val)
                self.max_spinbox.setValue(max_val)
                self.min_spinbox.blockSignals(False)
                self.max_spinbox.blockSignals(False)
            except ValueError:
                pass  # Invalid format, ignore

    def _update_text_from_spinboxes(self):
        """Update direct input text when spinbox values change."""
        min_val = self.min_spinbox.value()
        max_val = self.max_spinbox.value()
        self.direct_input.blockSignals(True)
        self.direct_input.setText(f"{min_val:.1f}-{max_val:.1f}")
        self.direct_input.blockSignals(False)

    def _accept_values(self):
        """Validate and accept the current values."""
        min_val = self.min_spinbox.value()
        max_val = self.max_spinbox.value()

        # Basic validation
        if min_val > max_val:
            QMessageBox.warning(self, "Invalid Range", "Minimum value cannot be greater than maximum value.")
            return

        # Geological plausibility check
        if abs(min_val) > 10000 or abs(max_val) > 10000:
            result = QMessageBox.question(
                self, "Large Values",
                "These values seem unusually large for geological data. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.No:
                return

        self.min_value = min_val
        self.max_value = max_val
        self.accept()

    def get_values(self):
        """Return the validated min and max values."""
        return (self.min_value, self.max_value)
