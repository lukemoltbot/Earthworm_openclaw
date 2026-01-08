from PyQt6.QtWidgets import (
    QLabel, QWidget, QVBoxLayout, QHBoxLayout, QDialog,
    QComboBox, QPushButton, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class MultiAttributeWidget(QLabel):
    """
    A compact widget that displays combined visual lithology properties
    and provides a detailed popup editor.

    Display format: "Dark Red Clay (Medium)"
    Internal storage: separate Shade, Hue, Colour, Weathering, Strength values
    """

    # Signal emitted when any property changes
    propertiesChanged = pyqtSignal(dict)  # Emits complete properties dict

    def __init__(self, parent=None, shade='', hue='', colour='', weathering='', strength='', coallog_data=None):
        super().__init__(parent)

        # Store individual property values
        self.properties = {
            'shade': shade,
            'hue': hue,
            'colour': colour,
            'weathering': weathering,
            'strength': strength
        }

        # Store coallog data reference
        self.coallog_data = coallog_data

        # Widget setup
        self.setFixedHeight(25)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Style with color-coded background based on dominant color
        self._update_display()

        # Tooltip showing full details
        self._update_tooltip()

    def _update_display(self):
        """Update the compact display text and styling."""
        shade = self.properties.get('shade', '')
        hue = self.properties.get('hue', '')
        colour = self.properties.get('colour', '')
        weathering = self.properties.get('weathering', '')
        strength = self.properties.get('strength', '')

        # Create compact display format
        parts = []

        # Shade (Light/Dark intensity)
        if shade:
            parts.append(shade)

        # Hue + Colour combination
        color_part = ""
        if hue:
            color_part = hue
        if colour and colour != hue:
            color_part = f"{color_part} {colour}" if color_part else colour

        if color_part:
            parts.append(color_part)

        # Simplified weathering type
        weathering_short = ""
        if weathering:
            weathering_short = weathering.replace("Weathering", "").strip()
            parts.append(weathering_short)

        # Strength in parentheses
        strength_short = ""
        if strength:
            if "Very" in strength:
                strength_short = "Very " + strength.replace("Very ", "").split()[0]
            else:
                strength_short = strength.split()[0]  # First word only

        # Combine parts
        display_text = " ".join(parts)
        if strength_short:
            display_text = f"{display_text} ({strength_short})"
        elif not display_text:
            display_text = "Not set"

        self.setText(display_text[:20] + "..." if len(display_text) > 20 else display_text)

        # Color-coded background based on Colour property
        bg_color = self._get_background_color()
        self.setStyleSheet(f"""
            QLabel {{
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 4px;
                background-color: {bg_color};
                font-size: 10px;
                font-weight: bold;
                color: {self._get_text_color(bg_color)};
            }}
            QLabel:hover {{
                border-color: #999;
                background-color: {self._darken_color(bg_color)};
            }}
        """)

    def _get_background_color(self):
        """Get background color based on Colour property."""
        colour_mapping = {
            'White': '#FFFFFF',
            'Cream': '#FFF8DC',
            'Yellow': '#FFFF00',
            'Orange': '#FFA500',
            'Red': '#FF0000',
            'Pink': '#FFC0CB',
            'Purple': '#800080',
            'Blue': '#0000FF',
            'Green': '#008000',
            'Grey': '#808080',
            'Black': '#000000',
            'Brown': '#A52A2A'
        }

        colour = self.properties.get('colour', '')
        return colour_mapping.get(colour, '#F5F5F5')  # Light grey default

    def _get_text_color(self, bg_color):
        """Determine text color (black or white) based on background brightness."""
        # Simple brightness calculation
        bg_color = bg_color.lstrip('#')
        r = int(bg_color[0:2], 16)
        g = int(bg_color[2:4], 16)
        b = int(bg_color[4:6], 16)

        # Calculate brightness (YIQ formula)
        brightness = (r * 299 + g * 587 + b * 114) / 1000

        return '#000000' if brightness > 128 else '#FFFFFF'

    def _darken_color(self, hex_color):
        """Darken a hex color for hover effect."""
        hex_color = hex_color.lstrip('#')
        r = max(0, int(hex_color[0:2], 16) - 20)
        g = max(0, int(hex_color[2:4], 16) - 20)
        b = max(0, int(hex_color[4:6], 16) - 20)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_tooltip(self):
        """Update tooltip with full property details."""
        tooltip_parts = []
        for prop_name, prop_value in self.properties.items():
            if prop_value:
                tooltip_parts.append(f"{prop_name.title()}: {prop_value}")

        self.setToolTip("\n".join(tooltip_parts) if tooltip_parts else "No properties set")

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to show detailed editor."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_property_editor()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """Handle single-click - could be used for quick actions."""
        super().mousePressEvent(event)

    def _show_property_editor(self):
        """Show the detailed property editor dialog."""
        dialog = PropertyEditorDialog(self.properties.copy(), self.coallog_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_properties = dialog.get_properties()
            self.set_properties(new_properties)

    def get_properties(self):
        """Get individual property values for analysis compatibility."""
        return self.properties.copy()

    def set_properties(self, properties_dict):
        """Set all properties from a dictionary and update display."""
        self.properties.update(properties_dict)
        self._update_display()
        self._update_tooltip()
        self.propertiesChanged.emit(self.properties.copy())

    def set_individual_property(self, property_name, value):
        """Set a single property and update display."""
        if property_name in self.properties:
            self.properties[property_name] = value
            self._update_display()
            self._update_tooltip()
            self.propertiesChanged.emit(self.properties.copy())


class PropertyEditorDialog(QDialog):
    """
    Dialog for editing all visual lithology properties in detail.
    """

    def __init__(self, current_properties, coallog_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Visual Properties")
        self.setModal(True)
        self.resize(400, 300)

        # Store current properties
        self.properties = current_properties.copy()

        # Store coallog data reference
        self.coallog_data = coallog_data

        # Create layout
        layout = QVBoxLayout(self)

        # Create form layout for properties
        form_layout = QFormLayout()

        # Shade dropdown
        self.shade_combo = QComboBox(self)
        self.shade_combo.addItem("")  # Empty option
        self._populate_dropdown_from_coallog('Shade', self.shade_combo)
        # Set current selection by code value
        current_shade = current_properties.get('shade', '')
        if current_shade:
            for i in range(self.shade_combo.count()):
                if self.shade_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_shade:
                    self.shade_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Shade:", self.shade_combo)

        # Hue dropdown
        self.hue_combo = QComboBox(self)
        self.hue_combo.addItem("")  # Empty option
        self._populate_dropdown_from_coallog('Hue', self.hue_combo)
        # Set current selection by code value
        current_hue = current_properties.get('hue', '')
        if current_hue:
            for i in range(self.hue_combo.count()):
                if self.hue_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_hue:
                    self.hue_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Hue:", self.hue_combo)

        # Colour dropdown
        self.colour_combo = QComboBox(self)
        self.colour_combo.addItem("")  # Empty option
        self._populate_dropdown_from_coallog('Colour', self.colour_combo)
        # Set current selection by code value
        current_colour = current_properties.get('colour', '')
        if current_colour:
            for i in range(self.colour_combo.count()):
                if self.colour_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_colour:
                    self.colour_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Colour:", self.colour_combo)

        # Weathering dropdown
        self.weathering_combo = QComboBox(self)
        self.weathering_combo.addItem("")  # Empty option
        self._populate_dropdown_from_coallog('Weathering', self.weathering_combo)
        # Set current selection by code value
        current_weathering = current_properties.get('weathering', '')
        if current_weathering:
            for i in range(self.weathering_combo.count()):
                if self.weathering_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_weathering:
                    self.weathering_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Weathering:", self.weathering_combo)

        # Strength dropdown - populate from coallog data if available
        self.strength_combo = QComboBox(self)
        self.strength_combo.addItem("")  # Empty option

        # Populate strength options from coallog data
        self._populate_strength_options()

        # Set current selection by code value
        current_strength_code = current_properties.get('strength', '')
        if current_strength_code:
            # Find the index of the code in user data
            for i in range(self.strength_combo.count()):
                if self.strength_combo.itemData(i, Qt.ItemDataRole.UserRole) == current_strength_code:
                    self.strength_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Est. Strength:", self.strength_combo)

        layout.addLayout(form_layout)

        # Preview label
        self.preview_label = QLabel("Preview: Not set")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                margin: 5px 0;
                background-color: #F5F5F5;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.preview_label)

        # Connect signals to update preview
        self.shade_combo.currentTextChanged.connect(self._update_preview)
        self.hue_combo.currentTextChanged.connect(self._update_preview)
        self.colour_combo.currentTextChanged.connect(self._update_preview)
        self.weathering_combo.currentTextChanged.connect(self._update_preview)
        self.strength_combo.currentTextChanged.connect(self._update_preview)

        # Initial preview update
        self._update_preview()

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept_properties)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_preview(self):
        """Update the preview label based on current selections."""
        # Get the selected codes
        shade_code = self.shade_combo.currentData(Qt.ItemDataRole.UserRole) or ""
        hue_code = self.hue_combo.currentData(Qt.ItemDataRole.UserRole) or ""
        colour_code = self.colour_combo.currentData(Qt.ItemDataRole.UserRole) or ""
        weathering_code = self.weathering_combo.currentData(Qt.ItemDataRole.UserRole) or ""
        strength_code = self.strength_combo.currentData(Qt.ItemDataRole.UserRole) or ""

        # For display purposes, get the descriptions from current combo box selections
        # The preview should show the final appearance
        shade_text = self.shade_combo.currentText().split(' (')[0] if self.shade_combo.currentText() else ""
        hue_text = self.hue_combo.currentText().split(' (')[0] if self.hue_combo.currentText() else ""
        colour_text = self.colour_combo.currentText().split(' (')[0] if self.colour_combo.currentText() else ""
        weathering_text = self.weathering_combo.currentText().split(' (')[0] if self.weathering_combo.currentText() else ""
        strength_text = self.strength_combo.currentText().split(' (')[0] if self.strength_combo.currentText() else ""

        temp_widget = MultiAttributeWidget()
        temp_widget.set_properties({
            'shade': shade_text,
            'hue': hue_text,
            'colour': colour_text,
            'weathering': weathering_text,
            'strength': strength_text
        })
        self.preview_label.setText(f"Preview: {temp_widget.text()}")

        # Update preview background color
        bg_color = temp_widget._get_background_color()
        text_color = temp_widget._get_text_color(bg_color)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                margin: 5px 0;
                background-color: {bg_color};
                font-weight: bold;
                color: {text_color};
            }}
        """)

    def _populate_dropdown_from_coallog(self, sheet_name, combo_box):
        """Populate a combo box from coallog data with format 'Description (Code)' """
        if self.coallog_data and sheet_name in self.coallog_data:
            df = self.coallog_data[sheet_name]
            seen_codes = set()  # Track already added codes to avoid duplicates

            for _, row in df.iterrows():
                # Get the first column as code, second as description
                code = str(row.iloc[0]).strip()
                description = str(row.iloc[1]).strip()

                if code and description and code not in seen_codes and code != 'nan':
                    # Format as "description (CODE)"
                    display_text = f"{description} ({code})"
                    combo_box.addItem(display_text, code)
                    seen_codes.add(code)

    def _populate_strength_options(self):
        """Populate strength combo box from coallog data with format 'Description (Code)' """
        if self.coallog_data and 'Est_Strength' in self.coallog_data:
            strength_df = self.coallog_data['Est_Strength']
            seen_codes = set()  # Track already added codes to avoid duplicates

            for _, row in strength_df.iterrows():
                code = str(row['Estimated Strength']).strip()
                description = str(row['Description']).strip()

                if code and description and code not in seen_codes:
                    # Format as "low strength rock (R3)"
                    display_text = f"{description} ({code})"
                    self.strength_combo.addItem(display_text, code)
                    seen_codes.add(code)

    def _accept_properties(self):
        """Collect and validate properties before accepting."""
        # Get codes from combobox user data
        shade_code = self.shade_combo.currentData(Qt.ItemDataRole.UserRole) if self.shade_combo.currentData(Qt.ItemDataRole.UserRole) else ""
        hue_code = self.hue_combo.currentData(Qt.ItemDataRole.UserRole) if self.hue_combo.currentData(Qt.ItemDataRole.UserRole) else ""
        colour_code = self.colour_combo.currentData(Qt.ItemDataRole.UserRole) if self.colour_combo.currentData(Qt.ItemDataRole.UserRole) else ""
        weathering_code = self.weathering_combo.currentData(Qt.ItemDataRole.UserRole) if self.weathering_combo.currentData(Qt.ItemDataRole.UserRole) else ""
        strength_code = self.strength_combo.currentData(Qt.ItemDataRole.UserRole) if self.strength_combo.currentData(Qt.ItemDataRole.UserRole) else ""

        self.properties = {
            'shade': shade_code,
            'hue': hue_code,
            'colour': colour_code,
            'weathering': weathering_code,
            'strength': strength_code  # All properties now store codes, not display text
        }
        self.accept()

    def get_properties(self):
        """Return the collected properties."""
        return self.properties.copy()
