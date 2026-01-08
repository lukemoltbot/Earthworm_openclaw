from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QStyledItemDelegate,
    QComboBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

class DictionaryDelegate(QStyledItemDelegate):
    """
    Renders a ComboBox for cells using CoalLog dictionary data.
    Displays: "Description (Code)"
    Saves: "Code"
    """
    def __init__(self, dictionary_df, parent=None):
        super().__init__(parent)
        self.items = []
        self.code_to_desc = {}

        if dictionary_df is not None and not dictionary_df.empty:
            for _, row in dictionary_df.iterrows():
                # Assumes Col 0 is Code, Col 1 is Description
                code = str(row.iloc[0]).strip()
                desc = str(row.iloc[1]).strip()
                display_text = f"{desc} ({code})"
                self.items.append(display_text)
                self.code_to_desc[code] = display_text
            self.items.insert(0, "")

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.setEditable(True) # Allow typing to search
        return editor

    def setEditorData(self, editor, index):
        current_code = index.model().data(index, Qt.ItemDataRole.EditRole)
        if current_code and current_code in self.code_to_desc:
            full_text = self.code_to_desc[current_code]
            idx = editor.findText(full_text)
            if idx >= 0: editor.setCurrentIndex(idx)
        else:
            editor.setCurrentText(str(current_code))

    def setModelData(self, editor, model, index):
        # Parse "Description (Code)" back to just "Code"
        text = editor.currentText()
        if "(" in text and text.endswith(")"):
            code = text.split("(")[-1].replace(")", "").strip()
            model.setData(index, code, Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, text, Qt.ItemDataRole.EditRole)

class LithologyTableWidget(QTableWidget):
    dataChangedSignal = pyqtSignal(object) # Signal to notify main window to redraw graphics
    rowSelectionChangedSignal = pyqtSignal(int) # Signal emitted when row selection changes (passes row index or -1 if none)

    def __init__(self, coallog_data=None, parent=None):
        super().__init__(parent)
        self.coallog_data = coallog_data

        # 1point Desktop standard column layout
        self.headers = [
            'From', 'To', 'Thick', 'Litho', 'Qual',
            'Shade', 'Hue', 'Colour', 'Weath', 'Str'
        ]

        # Map internal DF columns to Table Indices
        self.col_map = {
            'from_depth': 0, 'to_depth': 1, 'thickness': 2,
            'LITHOLOGY_CODE': 3, 'lithology_qualifier': 4,
            'shade': 5, 'hue': 6, 'colour': 7,
            'weathering': 8, 'estimated_strength': 9
        }

        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.verticalHeader().setVisible(True) # Show Row Numbers
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Apply Delegates
        if self.coallog_data:
            # Map specific columns to specific dictionary sheets
            mappings = {
                3: 'Litho_Type', 4: 'Litho_Qual', 5: 'Shade',
                6: 'Hue', 7: 'Colour', 8: 'Weathering', 9: 'Est_Strength'
            }
            for col_idx, sheet_name in mappings.items():
                if sheet_name in self.coallog_data:
                    self.setItemDelegateForColumn(col_idx,
                        DictionaryDelegate(self.coallog_data[sheet_name], self))

        self.itemChanged.connect(self._handle_item_changed)
        self.itemSelectionChanged.connect(self._handle_selection_changed)

    def load_data(self, dataframe):
        self.blockSignals(True)
        self.setRowCount(0)
        self.setRowCount(len(dataframe))

        for row_idx, row_data in dataframe.iterrows():
            for col_name, col_idx in self.col_map.items():
                if col_name in dataframe.columns:
                    val = row_data[col_name]
                    # Format floats to 3 decimals
                    if isinstance(val, (float, int)) and col_idx <= 2:
                        val = f"{val:.3f}"
                    self.setItem(row_idx, col_idx, QTableWidgetItem(str(val) if val is not None else ""))

        self.blockSignals(False)

    def _handle_item_changed(self, item):
        """Auto-calc thickness and emit update signal"""
        row = item.row()
        col = item.column()

        # If From (0) or To (1) changes -> Recalculate Thickness (2)
        if col in [0, 1]:
            try:
                from_item = self.item(row, 0)
                to_item = self.item(row, 1)
                if from_item and to_item and from_item.text() and to_item.text():
                    start = float(from_item.text())
                    end = float(to_item.text())
                    thickness = end - start

                    self.blockSignals(True)
                    self.setItem(row, 2, QTableWidgetItem(f"{thickness:.3f}"))
                    self.blockSignals(False)
            except ValueError:
                pass

        # Notify Main Window that data changed so it can redraw graphics
        self.dataChangedSignal.emit(None)

    def _handle_selection_changed(self):
        """Handle row selection changes and emit signal with selected row index."""
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            # Get the first selected row index
            selected_row_index = selected_rows[0].row()
            self.rowSelectionChangedSignal.emit(selected_row_index)
        else:
            # No selection
            self.rowSelectionChangedSignal.emit(-1)
