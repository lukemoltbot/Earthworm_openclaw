from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QGroupBox,
    QTextEdit, QMessageBox, QHeaderView, QAbstractItemView,
    QSplitter, QWidget, QFrame
)
from PyQt6.QtCore import Qt
import pandas as pd

class SmartInterbeddingSuggestionsDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.candidates = candidates  # List of interbedding candidate dictionaries
        self.selected_candidates = []  # Will store indices of selected candidates

        self.setWindowTitle("Smart Interbedding Suggestions")
        self.setModal(True)
        self.resize(1000, 700)

        self.setup_ui()
        self.populate_candidates_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "The following interbedding candidates were automatically detected. "
            "Review and select which suggestions to apply to your lithology data."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Candidates table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        candidates_label = QLabel("Detected Interbedding Candidates:")
        left_layout.addWidget(candidates_label)

        self.candidates_table = QTableWidget()
        self.candidates_table.setColumnCount(6)
        self.candidates_table.setHorizontalHeaderLabels([
            "Apply", "Depth Range", "Lithologies", "Avg Layer Thick", "Inter Code", "Details"
        ])
        self.candidates_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.candidates_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.candidates_table.setAlternatingRowColors(True)
        left_layout.addWidget(self.candidates_table)

        # Right side: Details panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        details_label = QLabel("Candidate Details:")
        right_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        right_layout.addWidget(self.details_text)

        # Preview of interbedded structure
        preview_group = QGroupBox("Proposed Interbedded Structure")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels([
            "Lithology", "Thickness (m)", "Percentage", "Record Seq"
        ])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setMaximumHeight(250)
        preview_layout.addWidget(self.preview_table)

        right_layout.addWidget(preview_group)

        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])  # Equal split initially

        layout.addWidget(splitter)

        # Connect table selection to update details
        self.candidates_table.itemSelectionChanged.connect(self.update_details)

        # Buttons
        button_layout = QHBoxLayout()

        # Select All / Clear All buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_candidates)
        button_layout.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_candidates)
        button_layout.addWidget(self.clear_all_btn)

        button_layout.addStretch()

        # Main action buttons
        self.apply_btn = QPushButton("Apply Selected")
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setDefault(True)

        self.skip_btn = QPushButton("Skip All")
        self.skip_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.apply_btn)

        layout.addLayout(button_layout)

    def populate_candidates_table(self):
        """Populate the candidates table with detected interbedding candidates."""
        self.candidates_table.setRowCount(len(self.candidates))

        for row, candidate in enumerate(self.candidates):
            # Checkbox for Apply column
            apply_checkbox = QTableWidgetItem()
            apply_checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            apply_checkbox.setCheckState(Qt.CheckState.Checked)  # Default to selected
            self.candidates_table.setItem(row, 0, apply_checkbox)

            # Depth range
            depth_range = f"{candidate['from_depth']:.3f} - {candidate['to_depth']:.3f}"
            depth_item = QTableWidgetItem(depth_range)
            depth_item.setFlags(depth_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.candidates_table.setItem(row, 1, depth_item)

            # Lithologies involved
            lithologies = ", ".join([f"{comp['code']} ({comp['percentage']:.1f}%)"
                                   for comp in candidate['lithologies']])
            litho_item = QTableWidgetItem(lithologies)
            litho_item.setFlags(litho_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.candidates_table.setItem(row, 2, litho_item)

            # Average layer thickness
            avg_thickness = candidate['average_layer_thickness']
            thickness_item = QTableWidgetItem(f"{avg_thickness:.1f} mm")
            thickness_item.setFlags(thickness_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.candidates_table.setItem(row, 3, thickness_item)

            # Interrelationship code
            inter_code = candidate['interrelationship_code']
            code_item = QTableWidgetItem(inter_code)
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.candidates_table.setItem(row, 4, code_item)

            # Details summary
            num_layers = len(candidate['original_sequence'])
            total_thickness = candidate['to_depth'] - candidate['from_depth']
            details = f"{num_layers} layers, {total_thickness:.3f}m total"
            details_item = QTableWidgetItem(details)
            details_item.setFlags(details_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.candidates_table.setItem(row, 5, details_item)

        # Auto-resize columns to content
        self.candidates_table.resizeColumnsToContents()

    def update_details(self):
        """Update the details panel when a candidate is selected."""
        selected_rows = set()
        for item in self.candidates_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            self.details_text.clear()
            self.preview_table.setRowCount(0)
            return

        # Get the first selected row
        row = list(selected_rows)[0]
        candidate = self.candidates[row]

        # Update details text
        details = f"""
Interbedding Candidate Details:

Depth Range: {candidate['from_depth']:.3f} - {candidate['to_depth']:.3f} m
Total Thickness: {candidate['to_depth'] - candidate['from_depth']:.3f} m
Number of Layers: {len(candidate['original_sequence'])}
Average Layer Thickness: {candidate['average_layer_thickness']:.1f} mm
Interrelationship Code: {candidate['interrelationship_code']}

Lithology Components:
"""

        for comp in candidate['lithologies']:
            details += f"  • {comp['code']}: {comp['percentage']:.1f}% ({comp['thickness']:.3f}m)\n"

        self.details_text.setPlainText(details.strip())

        # Update preview table
        self.preview_table.setRowCount(len(candidate['lithologies']))
        for i, comp in enumerate(candidate['lithologies']):
            # Lithology code
            code_item = QTableWidgetItem(comp['code'])
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.preview_table.setItem(i, 0, code_item)

            # Thickness
            thickness_item = QTableWidgetItem(f"{comp['thickness']:.3f}")
            thickness_item.setFlags(thickness_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.preview_table.setItem(i, 1, thickness_item)

            # Percentage
            percentage_item = QTableWidgetItem(f"{comp['percentage']:.1f}")
            percentage_item.setFlags(percentage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.preview_table.setItem(i, 2, percentage_item)

            # Record sequence
            seq_item = QTableWidgetItem(str(comp['sequence']))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.preview_table.setItem(i, 3, seq_item)

        self.preview_table.resizeColumnsToContents()

    def select_all_candidates(self):
        """Select all candidates."""
        for row in range(self.candidates_table.rowCount()):
            checkbox = self.candidates_table.item(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Checked)

    def clear_all_candidates(self):
        """Clear all candidate selections."""
        for row in range(self.candidates_table.rowCount()):
            checkbox = self.candidates_table.item(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

    def get_selected_candidates(self):
        """Return the indices of selected candidates."""
        selected = []
        for row in range(self.candidates_table.rowCount()):
            checkbox = self.candidates_table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                selected.append(row)
        return selected

    def accept(self):
        """Validate selection before accepting."""
        selected = self.get_selected_candidates()
        if not selected:
            QMessageBox.information(self, "No Selection",
                                  "No interbedding candidates selected. Click 'Skip All' to continue without applying interbedding.")
            return

        self.selected_candidates = selected
        super().accept()
