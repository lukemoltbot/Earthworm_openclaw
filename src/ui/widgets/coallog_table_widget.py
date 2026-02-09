"""
CoalLogTableWidget - 37-column table for CoalLog v3.1 standard
"""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QStyledItemDelegate,
    QComboBox, QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from ..core.coallog_schema import get_coallog_schema, get_dictionary_columns
from ..core.coallog_utils import load_coallog_dictionaries

class CoalLogDictionaryDelegate(QStyledItemDelegate):
    """
    Renders a ComboBox for cells using CoalLog dictionary data.
    Displays: "Description (Code)"
    Saves: "Code"
    """
    def __init__(self, dictionary_df, parent=None):
        super().__init__(parent)
        self.items = []
        self.code_to_desc = {}
        self.desc_to_code = {}

        if dictionary_df is not None and not dictionary_df.empty:
            for _, row in dictionary_df.iterrows():
                # Assumes Col 0 is Code, Col 1 is Description
                code = str(row.iloc[0]).strip()
                desc = str(row.iloc[1]).strip()
                display_text = f"{desc} ({code})"
                self.items.append(display_text)
                self.code_to_desc[code] = display_text
                self.desc_to_code[display_text] = code
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
            if idx >= 0: 
                editor.setCurrentIndex(idx)
            else:
                editor.setCurrentText(str(current_code))
        else:
            editor.setCurrentText(str(current_code))

    def setModelData(self, editor, model, index):
        # Parse "Description (Code)" back to just "Code"
        text = editor.currentText()
        if text in self.desc_to_code:
            # Exact match to display text
            code = self.desc_to_code[text]
            model.setData(index, code, Qt.ItemDataRole.EditRole)
        elif "(" in text and text.endswith(")"):
            # Try to parse "Description (Code)" format
            code = text.split("(")[-1].replace(")", "").strip()
            model.setData(index, code, Qt.ItemDataRole.EditRole)
        else:
            # Just use the text as-is
            model.setData(index, text, Qt.ItemDataRole.EditRole)

class SimpleListDelegate(QStyledItemDelegate):
    """Delegate for simple list-based dropdowns"""
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.setEditable(True)
        return editor

    def setEditorData(self, editor, index):
        current_value = index.model().data(index, Qt.ItemDataRole.EditRole)
        if current_value:
            idx = editor.findText(str(current_value))
            if idx >= 0:
                editor.setCurrentIndex(idx)
            else:
                editor.setCurrentText(str(current_value))

class CoalLogTableWidget(QTableWidget):
    """37-column table widget for CoalLog v3.1 standard"""
    
    dataChangedSignal = pyqtSignal(object)  # Signal to notify main window to redraw graphics
    validationErrorSignal = pyqtSignal(str, int, int)  # Signal for validation errors (message, row, col)
    
    def __init__(self, coallog_data=None, parent=None):
        super().__init__(parent)
        self.coallog_data = coallog_data
        self.schema = get_coallog_schema()
        
        # Get 37 column names from schema
        self.headers = [col["name"] for col in self.schema["columns"]]
        
        # Create column mapping
        self.col_map = {col["name"]: idx for idx, col in enumerate(self.schema["columns"])}
        
        # Set up table
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.verticalHeader().setVisible(True)  # Show Row Numbers
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Set column widths based on content
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Apply delegates for dictionary columns
        self._setup_delegates()
        
        # Connect signals
        self.itemChanged.connect(self._handle_item_changed)
        
        # Track validation errors
        self.validation_errors = {}
        
    def _setup_delegates(self):
        """Set up dictionary delegates for appropriate columns"""
        if not self.coallog_data:
            return
            
        # Get dictionary columns from schema
        dict_columns = get_dictionary_columns()
        
        for col_name in dict_columns:
            if col_name in self.col_map:
                col_idx = self.col_map[col_name]
                
                # Check if this column uses CoalLog dictionaries
                if col_name in self.schema["dictionaries"]:
                    dict_name = self.schema["dictionaries"][col_name]
                    
                    if isinstance(dict_name, str) and dict_name in self.coallog_data:
                        # Use CoalLog dictionary
                        delegate = CoalLogDictionaryDelegate(self.coallog_data[dict_name], self)
                        self.setItemDelegateForColumn(col_idx, delegate)
                    elif isinstance(dict_name, list):
                        # Use simple list
                        delegate = SimpleListDelegate(dict_name, self)
                        self.setItemDelegateForColumn(col_idx, delegate)
    
    def load_data(self, dataframe):
        """Load data from pandas DataFrame"""
        self.blockSignals(True)
        self.setRowCount(0)
        
        if dataframe is not None and not dataframe.empty:
            self.setRowCount(len(dataframe))
            
            for row_idx, row_data in dataframe.iterrows():
                for col_name, col_idx in self.col_map.items():
                    if col_name in dataframe.columns:
                        val = row_data[col_name]
                        
                        # Format based on column type
                        item = QTableWidgetItem()
                        
                        if pd.isna(val):
                            item.setText("")
                        else:
                            # Apply formatting for numeric columns
                            col_def = self.schema["columns"][col_idx]
                            if col_def["type"] == "float" and isinstance(val, (float, int)):
                                precision = col_def.get("precision", 3)
                                item.setText(f"{val:.{precision}f}")
                            else:
                                item.setText(str(val))
                        
                        # Set item properties
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                        self.setItem(row_idx, col_idx, item)
        
        self.blockSignals(False)
        self._validate_all()
    
    def get_dataframe(self):
        """Convert table data to pandas DataFrame"""
        import pandas as pd
        
        data = {}
        for col_name, col_idx in self.col_map.items():
            column_data = []
            for row in range(self.rowCount()):
                item = self.item(row, col_idx)
                if item and item.text():
                    column_data.append(item.text())
                else:
                    column_data.append(None)
            data[col_name] = column_data
        
        df = pd.DataFrame(data)
        
        # Convert data types based on schema
        for col_def in self.schema["columns"]:
            col_name = col_def["name"]
            if col_name in df.columns:
                if col_def["type"] == "float":
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                elif col_def["type"] == "int":
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
        
        return df
    
    def _handle_item_changed(self, item):
        """Handle item changes with validation and auto-calculation"""
        row = item.row()
        col = item.column()
        col_name = self.headers[col] if col < len(self.headers) else ""
        
        # Auto-calculate thickness if FROM or TO changed
        if col_name in ["FROM", "TO"]:
            self._calculate_thickness(row)
        
        # Validate the changed cell
        self._validate_cell(row, col)
        
        # Emit data changed signal
        self.dataChangedSignal.emit(None)
    
    def _calculate_thickness(self, row):
        """Calculate thickness from FROM and TO values"""
        from_col = self.col_map.get("FROM")
        to_col = self.col_map.get("TO")
        thick_col = self.col_map.get("THICKNESS")
        
        if from_col is not None and to_col is not None and thick_col is not None:
            from_item = self.item(row, from_col)
            to_item = self.item(row, to_col)
            
            if from_item and to_item and from_item.text() and to_item.text():
                try:
                    from_val = float(from_item.text())
                    to_val = float(to_item.text())
                    thickness = to_val - from_val
                    
                    if thickness >= 0:
                        self.blockSignals(True)
                        thick_item = QTableWidgetItem(f"{thickness:.3f}")
                        thick_item.setFlags(thick_item.flags() | Qt.ItemFlag.ItemIsEditable)
                        self.setItem(row, thick_col, thick_item)
                        self.blockSignals(False)
                except ValueError:
                    pass
    
    def _validate_cell(self, row, col):
        """Validate a single cell"""
        col_name = self.headers[col] if col < len(self.headers) else ""
        item = self.item(row, col)
        
        if not item or not col_name:
            return
            
        value = item.text()
        
        # Clear previous error for this cell
        error_key = (row, col)
        if error_key in self.validation_errors:
            del self.validation_errors[error_key]
            item.setBackground(QBrush(QColor(255, 255, 255)))  # White background
        
        # Skip validation for empty cells (except required columns)
        if not value:
            # Check if column is required
            col_def = next((c for c in self.schema["columns"] if c["name"] == col_name), None)
            if col_def and col_def.get("required", False):
                self.validation_errors[error_key] = f"Required field '{col_name}' is empty"
                item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
                self.validationErrorSignal.emit(f"Required field '{col_name}' is empty", row, col)
            return
        
        # Type validation
        col_def = next((c for c in self.schema["columns"] if c["name"] == col_name), None)
        if col_def:
            if col_def["type"] == "float":
                try:
                    float_val = float(value)
                    # Range validation
                    if col_name in self.schema["validation"]:
                        rules = self.schema["validation"][col_name]
                        if "min" in rules and float_val < rules["min"]:
                            self.validation_errors[error_key] = f"{col_name} must be >= {rules['min']}"
                            item.setBackground(QBrush(QColor(255, 200, 200)))
                        elif "max" in rules and float_val > rules["max"]:
                            self.validation_errors[error_key] = f"{col_name} must be <= {rules['max']}"
                            item.setBackground(QBrush(QColor(255, 200, 200)))
                except ValueError:
                    self.validation_errors[error_key] = f"{col_name} must be a number"
                    item.setBackground(QBrush(QColor(255, 200, 200)))
                    self.validationErrorSignal.emit(f"{col_name} must be a number", row, col)
            
            elif col_def["type"] == "int":
                try:
                    int(value)
                except ValueError:
                    self.validation_errors[error_key] = f"{col_name} must be an integer"
                    item.setBackground(QBrush(QColor(255, 200, 200)))
                    self.validationErrorSignal.emit(f"{col_name} must be an integer", row, col)
    
    def _validate_all(self):
        """Validate all cells in the table"""
        self.validation_errors.clear()
        
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                self._validate_cell(row, col)
    
    def get_validation_errors(self):
        """Get all validation errors"""
        return self.validation_errors
    
    def has_validation_errors(self):
        """Check if there are any validation errors"""
        return len(self.validation_errors) > 0
    
    def add_row(self):
        """Add a new empty row to the table"""
        row_position = self.rowCount()
        self.insertRow(row_position)
        
        # Initialize cells with empty editable items
        for col in range(self.columnCount()):
            item = QTableWidgetItem("")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.setItem(row_position, col, item)
        
        return row_position
    
    def remove_selected_rows(self):
        """Remove selected rows from the table"""
        selected_rows = set()
        for item in self.selectedItems():
            selected_rows.add(item.row())
        
        # Remove rows in reverse order to maintain indices
        for row in sorted(selected_rows, reverse=True):
            self.removeRow(row)
    
    def clear_table(self):
        """Clear all data from the table"""
        self.setRowCount(0)
        self.validation_errors.clear()

# Import pandas here to avoid circular imports
import pandas as pd