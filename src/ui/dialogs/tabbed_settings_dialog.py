"""
Tabbed Settings Dialog for Earthworm Application
Simplified version with 5 tabs for Phase 2 implementation
"""

import json
import os

# PyQt version-agnostic imports
try:
    # Try PyQt6 first
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget,
        QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
        QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QHeaderView, QListWidget, QListWidgetItem
    )
    from PyQt6.QtCore import Qt
    PYQT_VERSION = 6
except ImportError:
    # Fall back to PyQt5
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QTabWidget,
        QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
        QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
        QHeaderView, QListWidget, QListWidgetItem
    )
    from PyQt5.QtCore import Qt
    PYQT_VERSION = 5


class TabbedSettingsDialog(QDialog):
    """Modal dialog with 5 tabs for application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Earthworm Settings")
        self.setMinimumSize(700, 500)
        
        # Default settings
        self.settings = {
            'general': {},
            'lithology': {},
            'geotechnical': {},
            'export': {},
            'advanced': {}
        }
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.general_tab = self.create_general_tab()
        self.lithology_tab = self.create_lithology_tab()
        self.geotechnical_tab = self.create_geotechnical_tab()
        self.export_tab = self.create_export_tab()
        self.advanced_tab = self.create_advanced_tab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.lithology_tab, "Lithology")
        self.tab_widget.addTab(self.geotechnical_tab, "Geotechnical")
        self.tab_widget.addTab(self.export_tab, "Export")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        main_layout.addWidget(self.tab_widget)
        
        # Create button box
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.apply_button = QPushButton("Apply")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.apply_settings)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_layout)
        
    def create_general_tab(self):
        """Create the General settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        theme_layout.addRow("Theme:", self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Unit system
        unit_group = QGroupBox("Units")
        unit_layout = QFormLayout()
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Metric (meters)", "Imperial (feet)"])
        unit_layout.addRow("Unit System:", self.unit_combo)
        
        unit_group.setLayout(unit_layout)
        layout.addWidget(unit_group)
        
        # Auto-save
        autosave_group = QGroupBox("Auto-save")
        autosave_layout = QFormLayout()
        
        self.autosave_checkbox = QCheckBox("Enable auto-save")
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(1, 60)
        self.autosave_interval.setSuffix(" minutes")
        
        autosave_layout.addRow(self.autosave_checkbox)
        autosave_layout.addRow("Interval:", self.autosave_interval)
        
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        layout.addStretch()
        return tab
        
    def create_lithology_tab(self):
        """Create the Lithology settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Default lithology codes
        codes_group = QGroupBox("Default Lithology Codes")
        codes_layout = QVBoxLayout()
        
        self.lithology_table = QTableWidget(5, 3)
        self.lithology_table.setHorizontalHeaderLabels(["Code", "Name", "Color"])
        self.lithology_table.horizontalHeader().setStretchLastSection(True)
        
        # Add some default values
        default_data = [
            ["CO", "Coal", "#000000"],
            ["SS", "Sandstone", "#FFFF00"],
            ["SH", "Shale", "#A9A9A9"],
            ["LS", "Limestone", "#FFFFFF"],
            ["MS", "Mudstone", "#8B4513"]
        ]
        
        for row, data in enumerate(default_data):
            for col, value in enumerate(data):
                self.lithology_table.setItem(row, col, QTableWidgetItem(value))
        
        codes_layout.addWidget(self.lithology_table)
        codes_group.setLayout(codes_layout)
        layout.addWidget(codes_group)
        
        # Dictionary file
        dict_group = QGroupBox("Dictionary Files")
        dict_layout = QFormLayout()
        
        self.dict_path_edit = QLineEdit()
        self.dict_path_edit.setPlaceholderText("Path to lithology dictionary...")
        dict_layout.addRow("Dictionary:", self.dict_path_edit)
        
        dict_group.setLayout(dict_layout)
        layout.addWidget(dict_group)
        
        layout.addStretch()
        return tab
        
    def create_geotechnical_tab(self):
        """Create the Geotechnical settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Strength classification
        strength_group = QGroupBox("Strength Classification")
        strength_layout = QFormLayout()
        
        self.strength_system = QComboBox()
        self.strength_system.addItems(["ISRM", "BSI", "Custom"])
        strength_layout.addRow("System:", self.strength_system)
        
        strength_group.setLayout(strength_layout)
        layout.addWidget(strength_group)
        
        # Weathering grades
        weathering_group = QGroupBox("Weathering Grades")
        weathering_layout = QFormLayout()
        
        self.weathering_system = QComboBox()
        self.weathering_system.addItems(["ISRM", "BSI", "Australian"])
        weathering_layout.addRow("System:", self.weathering_system)
        
        weathering_group.setLayout(weathering_layout)
        layout.addWidget(weathering_group)
        
        # RQD settings
        rqd_group = QGroupBox("RQD Calculation")
        rqd_layout = QFormLayout()
        
        self.rqd_threshold = QDoubleSpinBox()
        self.rqd_threshold.setRange(0.05, 0.5)
        self.rqd_threshold.setValue(0.1)
        self.rqd_threshold.setSuffix(" m")
        rqd_layout.addRow("Threshold:", self.rqd_threshold)
        
        rqd_group.setLayout(rqd_layout)
        layout.addWidget(rqd_group)
        
        layout.addStretch()
        return tab
        
    def create_export_tab(self):
        """Create the Export settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # CoalLog format
        coallog_group = QGroupBox("CoalLog Export")
        coallog_layout = QFormLayout()
        
        self.coallog_format = QComboBox()
        self.coallog_format.addItems(["37-Column", "Extended", "Custom"])
        coallog_layout.addRow("Format:", self.coallog_format)
        
        self.include_header = QCheckBox("Include header")
        coallog_layout.addRow(self.include_header)
        
        coallog_group.setLayout(coallog_layout)
        layout.addWidget(coallog_group)
        
        # File format
        format_group = QGroupBox("File Format")
        format_layout = QFormLayout()
        
        self.file_format = QComboBox()
        self.file_format.addItems(["CSV", "Excel", "LAS", "JSON"])
        format_layout.addRow("Format:", self.file_format)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Column selection
        column_group = QGroupBox("Columns to Export")
        column_layout = QVBoxLayout()
        
        self.column_list = QListWidget()
        columns = ["Depth", "Lithology", "Gamma", "Density", "Strength", "Weathering", "RQD", "Comments"]
        self.column_list.addItems(columns)
        
        # Select all by default
        for i in range(self.column_list.count()):
            self.column_list.item(i).setSelected(True)
        
        column_layout.addWidget(self.column_list)
        column_group.setLayout(column_layout)
        layout.addWidget(column_group)
        
        layout.addStretch()
        return tab
        
    def create_advanced_tab(self):
        """Create the Advanced settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Performance
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()
        
        self.cache_size = QSpinBox()
        self.cache_size.setRange(10, 1000)
        self.cache_size.setValue(100)
        self.cache_size.setSuffix(" MB")
        perf_layout.addRow("Cache Size:", self.cache_size)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # Debug
        debug_group = QGroupBox("Debug")
        debug_layout = QFormLayout()
        
        self.debug_logging = QCheckBox("Enable debug logging")
        debug_layout.addRow(self.debug_logging)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # Experimental features
        exp_group = QGroupBox("Experimental Features")
        exp_layout = QFormLayout()
        
        self.experimental_ai = QCheckBox("Enable AI suggestions")
        exp_layout.addRow(self.experimental_ai)
        
        exp_group.setLayout(exp_layout)
        layout.addWidget(exp_group)
        
        layout.addStretch()
        return tab
        
    def apply_settings(self):
        """Apply current settings."""
        try:
            # Collect settings from UI
            settings = {
                'general': {
                    'theme': self.theme_combo.currentText(),
                    'units': self.unit_combo.currentText(),
                    'autosave': {
                        'enabled': self.autosave_checkbox.isChecked(),
                        'interval': self.autosave_interval.value()
                    }
                },
                'lithology': {
                    'dictionary_path': self.dict_path_edit.text()
                },
                'geotechnical': {
                    'strength_system': self.strength_system.currentText(),
                    'weathering_system': self.weathering_system.currentText(),
                    'rqd_threshold': self.rqd_threshold.value()
                },
                'export': {
                    'coallog_format': self.coallog_format.currentText(),
                    'file_format': self.file_format.currentText(),
                    'include_header': self.include_header.isChecked(),
                    'selected_columns': [self.column_list.item(i).text() 
                                       for i in range(self.column_list.count())
                                       if self.column_list.item(i).isSelected()]
                },
                'advanced': {
                    'cache_size': self.cache_size.value(),
                    'debug_logging': self.debug_logging.isChecked(),
                    'experimental_ai': self.experimental_ai.isChecked()
                }
            }
            
            # Save to file
            settings_file = os.path.expanduser("~/.earthworm_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            QMessageBox.information(self, "Settings Saved", 
                                  "Settings have been saved successfully.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                              f"Failed to save settings: {str(e)}")
            
    def load_settings(self):
        """Load settings from file."""
        try:
            settings_file = os.path.expanduser("~/.earthworm_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    self.settings = json.load(f)
                    
                # Apply settings to UI
                self.apply_settings_to_ui()
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    def apply_settings_to_ui(self):
        """Apply loaded settings to UI controls."""
        # This would populate UI controls with loaded settings
        # Simplified for this implementation
        pass
        
    def accept(self):
        """Handle OK button click."""
        self.apply_settings()
        super().accept()
        
    def reject(self):
        """Handle Cancel button click."""
        super().reject()


if __name__ == "__main__":
    # Simple test
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = TabbedSettingsDialog()
    dialog.show()
    sys.exit(app.exec())