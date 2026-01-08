from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, initial_rules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lithology Rules Settings")
        self.setGeometry(200, 200, 800, 400)

        self.current_rules = initial_rules # Store the rules passed from MainWindow

        self.main_layout = QVBoxLayout(self)

        # Table for lithology rules
        self.rulesTable = QTableWidget()
        self.rulesTable.setColumnCount(6)
        self.rulesTable.setHorizontalHeaderLabels([
            "Lithology Name", "2-Letter Code", "Gamma Min", "Gamma Max", "Density Min", "Density Max"
        ])
        self.rulesTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.rulesTable)

        # Buttons for adding/removing rules
        self.button_layout = QHBoxLayout()
        self.addRuleButton = QPushButton("Add Rule")
        self.removeRuleButton = QPushButton("Remove Rule")
        self.button_layout.addWidget(self.addRuleButton)
        self.button_layout.addWidget(self.removeRuleButton)
        self.main_layout.addLayout(self.button_layout)

        self.connect_signals()
        self.load_rules()

    def connect_signals(self):
        self.addRuleButton.clicked.connect(self.add_rule)
        self.removeRuleButton.clicked.connect(self.remove_rule)

    def load_rules(self):
        self.rulesTable.setRowCount(len(self.current_rules))
        for row_idx, rule in enumerate(self.current_rules):
            self.rulesTable.setItem(row_idx, 0, QTableWidgetItem(str(rule.get('name', ''))))
            self.rulesTable.setItem(row_idx, 1, QTableWidgetItem(str(rule.get('code', ''))))
            self.rulesTable.setItem(row_idx, 2, QTableWidgetItem(str(rule.get('gamma_min', ''))))
            self.rulesTable.setItem(row_idx, 3, QTableWidgetItem(str(rule.get('gamma_max', ''))))
            self.rulesTable.setItem(row_idx, 4, QTableWidgetItem(str(rule.get('density_min', ''))))
            self.rulesTable.setItem(row_idx, 5, QTableWidgetItem(str(rule.get('density_max', ''))))

    def save_rules(self):
        rules = []
        for row_idx in range(self.rulesTable.rowCount()):
            rule = {}
            rule['name'] = self.rulesTable.item(row_idx, 0).text() if self.rulesTable.item(row_idx, 0) else ''
            rule['code'] = self.rulesTable.item(row_idx, 1).text() if self.rulesTable.item(row_idx, 1) else ''
            
            # Convert numeric fields to float/int, handle potential errors
            try:
                rule['gamma_min'] = float(self.rulesTable.item(row_idx, 2).text()) if self.rulesTable.item(row_idx, 2) and self.rulesTable.item(row_idx, 2).text() else 0.0
            except ValueError:
                rule['gamma_min'] = 0.0 # Default or error handling
            try:
                rule['gamma_max'] = float(self.rulesTable.item(row_idx, 3).text()) if self.rulesTable.item(row_idx, 3) and self.rulesTable.item(row_idx, 3).text() else 0.0
            except ValueError:
                rule['gamma_max'] = 0.0
            try:
                rule['density_min'] = float(self.rulesTable.item(row_idx, 4).text()) if self.rulesTable.item(row_idx, 4) and self.rulesTable.item(row_idx, 4).text() else 0.0
            except ValueError:
                rule['density_min'] = 0.0
            try:
                rule['density_max'] = float(self.rulesTable.item(row_idx, 5).text()) if self.rulesTable.item(row_idx, 5) and self.rulesTable.item(row_idx, 5).text() else 0.0
            except ValueError:
                rule['density_max'] = 0.0
            
            rules.append(rule)
        self.current_rules = rules

    def get_rules(self):
        return self.current_rules

    def add_rule(self):
        row_position = self.rulesTable.rowCount()
        self.rulesTable.insertRow(row_position)
        # Optionally pre-fill with empty QTableWidgetItems to make them editable
        for col in range(self.rulesTable.columnCount()):
            self.rulesTable.setItem(row_position, col, QTableWidgetItem(""))

    def remove_rule(self):
        current_row = self.rulesTable.currentRow()
        if current_row >= 0:
            self.rulesTable.removeRow(current_row)

    def accept(self):
        self.save_rules()
        super().accept()

    def reject(self):
        # Optionally reload rules if changes were not saved
        super().reject()
