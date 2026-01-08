from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt
from ...core.config import RESEARCHED_LITHOLOGY_DEFAULTS

class ResearchedDefaultsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Researched Lithology Defaults")
        self.setGeometry(200, 200, 600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint) # Remove help button

        self.main_layout = QVBoxLayout(self)

        # Search section
        self.search_layout = QHBoxLayout()
        self.search_label = QLabel("Enter Lithology Code (e.g., CO, SS, ST):")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_layout.addWidget(self.search_label)
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.search_button)
        self.main_layout.addLayout(self.search_layout)

        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.main_layout.addWidget(self.results_display)

        self.search_button.clicked.connect(self._search_defaults)
        self.search_input.returnPressed.connect(self._search_defaults) # Allow searching with Enter key

        self._display_all_defaults() # Display all defaults on startup

    def _search_defaults(self):
        code = self.search_input.text().strip().upper()
        self.results_display.clear()

        if not code:
            self._display_all_defaults()
            return

        if code in RESEARCHED_LITHOLOGY_DEFAULTS:
            defaults = RESEARCHED_LITHOLOGY_DEFAULTS[code]
            result_text = f"<h3>Defaults for {code}:</h3>"
            result_text += f"<b>Gamma:</b> {defaults.get('gamma_min', 'N/A')} - {defaults.get('gamma_max', 'N/A')}<br>"
            result_text += f"<b>Density:</b> {defaults.get('density_min', 'N/A')} - {defaults.get('density_max', 'N/A')}<br>"
            result_text += "<b>Source:</b> General Geological Guidelines (User verification recommended)"
            self.results_display.setHtml(result_text)
        else:
            self.results_display.setText(f"No researched defaults found for code: {code}")

    def _display_all_defaults(self):
        """Displays all available researched defaults."""
        all_defaults_text = "<h3>All Researched Defaults:</h3>"
        if not RESEARCHED_LITHOLOGY_DEFAULTS:
            all_defaults_text += "No defaults defined."
        else:
            for code, defaults in RESEARCHED_LITHOLOGY_DEFAULTS.items():
                all_defaults_text += f"<b>{code}:</b><br>"
                all_defaults_text += f"&nbsp;&nbsp;Gamma: {defaults.get('gamma_min', 'N/A')} - {defaults.get('gamma_max', 'N/A')}<br>"
                all_defaults_text += f"&nbsp;&nbsp;Density: {defaults.get('density_min', 'N/A')} - {defaults.get('density_max', 'N/A')}<br>"
                all_defaults_text += "<br>"
            all_defaults_text += "<b>Source:</b> General Geological Guidelines (User verification recommended)"
        self.results_display.setHtml(all_defaults_text)
