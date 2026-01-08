Here is a comprehensive, step-by-step implementation plan designed to guide an AI coding agent to upgrade the Earthworm **Editor Tab** to match the functionality of **1point Desktop**.

This plan is divided into **4 Phases**.

---

# Phase 1: Infrastructure & Layout Upgrade
**Goal:** Replace the static layout with a resizable split view to allow flexible workspace management.

### Step 1.1: Update `src/ui/main_window.py`
**Action:** Modify the `setup_editor_tab` method.
**Logic:** Replace the existing `QHBoxLayout` with a `QSplitter`. This requires organizing the widgets into two container widgets (Left: Graphics, Right: Data).

**Code Requirements:**
```python
# In src/ui/main_window.py

# Add imports
from PyQt6.QtWidgets import QSplitter, QFrame, QSizePolicy

def setup_editor_tab(self):
    self.editor_tab_layout = QVBoxLayout(self.editor_tab)

    # 1. Create the Splitter
    self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
    
    # 2. Left Container (Visuals)
    graphics_container = QWidget()
    graphics_layout = QHBoxLayout(graphics_container)
    graphics_layout.setContentsMargins(0, 0, 0, 0)
    graphics_layout.addWidget(self.curvePlotter, 3) # Weight 3
    graphics_layout.addWidget(self.stratigraphicColumnView, 1) # Weight 1
    
    # 3. Right Container (Data Input)
    # Note: We will replace self.editorTable with the new widget in Phase 2
    data_container = QWidget()
    data_layout = QVBoxLayout(data_container)
    data_layout.setContentsMargins(0, 0, 0, 0)
    data_layout.addWidget(self.editorTable) 
    data_layout.addWidget(self.exportCsvButton)
    
    # 4. Add to Splitter & Set defaults
    self.main_splitter.addWidget(graphics_container)
    self.main_splitter.addWidget(data_container)
    self.main_splitter.setStretchFactor(0, 1) # Graphics area
    self.main_splitter.setStretchFactor(1, 1) # Data area
    
    # 5. Add Splitter to Main Layout
    self.editor_tab_layout.addWidget(self.main_splitter)

    # 6. Re-add Zoom Controls (Keep existing logic)
    # ... existing zoom control code ...
```

---

# Phase 2: The "Smart" Data Grid
**Goal:** Implement a specialized table widget that handles auto-calculations and dropdowns (dictionaries), replacing the generic `QTableWidget`.

### Step 2.1: Create `src/ui/widgets/lithology_table.py`
**Action:** Create a new file. This will contain the `DictionaryDelegate` and `LithologyTableWidget` classes.

**Complex Code Implementation:**
```python
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
```

### Step 2.2: Integrate into `src/ui/main_window.py`
**Action:**
1. Import the new class.
2. Replace `self.editorTable = QTableWidget()` with `self.editorTable = LithologyTableWidget(coallog_data=self.coallog_data)`.
3. Update `analysis_finished`: Call `self.editorTable.load_data(units_dataframe)` instead of `populate_editor_table`.

---

# Phase 3: Two-Way Synchronization
**Goal:** Connecting the Visuals (Left) with the Data (Right).

### Step 3.1: Update `src/ui/widgets/stratigraphic_column.py`
**Action:** Modify `draw_column` to store Row Indices in the graphic items.
**Action:** Add a method `highlight_units`.

**Code Modification:**
```python
# In draw_column loop:
# ... existing drawing code ...
rect_item = QGraphicsRectItem(...)
# STORE THE ROW INDEX
rect_item.setData(Qt.ItemDataRole.UserRole, index) 
# Make it clickable
rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable) 
self.scene.addItem(rect_item)
self.rect_items[index] = rect_item # Cache it
```

**Add Method:**
```python
def highlight_units(self, selected_row_indices):
    """ highlights rects corresponding to table rows """
    # Define Highlight Pen (Blue, thicker)
    pen_highlight = QPen(QColor("blue"), 2)
    pen_normal = QPen(Qt.PenStyle.NoPen)
    
    for row_idx, item in self.rect_items.items():
        if row_idx in selected_row_indices:
            item.setPen(pen_highlight)
            item.setZValue(10) # Bring to front
        else:
            item.setPen(pen_normal)
            item.setZValue(0)
```

### Step 3.2: Wire Signals in `src/ui/main_window.py`
**Action:** Connect table selection to graphics highlighting.

```python
# In __init__ or connect_signals:
self.editorTable.itemSelectionChanged.connect(self.sync_table_to_graphics)

# Add method:
def sync_table_to_graphics(self):
    selected_rows = {idx.row() for idx in self.editorTable.selectedIndexes()}
    # 1. Highlight Graphics
    self.stratigraphicColumnView.highlight_units(selected_rows)
    
    # 2. Scroll Graphics to match
    if selected_rows:
        first_row = min(selected_rows)
        try:
            # Get depth from Column 0 (From Depth)
            depth_text = self.editorTable.item(first_row, 0).text()
            depth = float(depth_text)
            self.stratigraphicColumnView.center_on_depth(depth)
            # Sync curve plotter too
            self.curvePlotter.centerOn(0, depth * self.curvePlotter.depth_scale)
        except:
            pass
```

---

# Phase 4: Interactive Depth Correction (Advanced)
**Goal:** Allow dragging lines in the graphic log to adjust `to_depth` and `from_depth` in the table.

### Step 4.1: Create Draggable Boundary Item
**Action:** Add a new class to `src/ui/widgets/stratigraphic_column.py`.

**Complex Code Implementation:**
```python
class DraggableBoundaryLine(QGraphicsLineItem):
    def __init__(self, y_pos, width, row_index, depth_scale, parent_view):
        super().__init__(0, 0, width, 0) # Horizontal line
        self.setPos(0, y_pos)
        self.row_index_above = row_index
        self.depth_scale = depth_scale
        self.parent_view = parent_view
        
        # Visual settings
        pen = QPen(QColor("red"))
        pen.setWidth(2)
        pen.setCosmetic(True) # Keeps width constant despite zoom
        self.setPen(pen)
        
        # Interaction settings
        self.setCursor(Qt.CursorShape.SplitVCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Restrict movement to Vertical only
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Value is the new PointF
            new_pos = value
            # Lock X axis
            new_pos.setX(0) 
            
            # Send signal to parent view to update data
            # We use the scene Y to calculate depth
            new_depth = new_pos.y() / self.depth_scale
            self.parent_view.boundary_moved(self.row_index_above, new_depth)
            
            return new_pos
            
        return super().itemChange(change, value)
```

### Step 4.2: Integrate Boundary Logic
**Action:** Update `StratigraphicColumn` to handling the signals from the draggable line.

1.  **Add Signal:** `boundaryChanged = pyqtSignal(int, float)` (row_index, new_depth).
2.  **Draw Lines:** In `draw_column`, instantiate `DraggableBoundaryLine` at the bottom of every unit.
3.  **Handle Move:**
    ```python
    def boundary_moved(self, row_index, new_depth):
        self.boundaryChanged.emit(row_index, new_depth)
    ```

### Step 4.3: Update Main Window to Handle Data Changes
**Action:** In `main_window.py`, connect `stratigraphicColumnView.boundaryChanged` to a handler.

```python
# In MainWindow
def on_boundary_dragged(self, row_index, new_depth):
    # 1. Update "To Depth" of current row
    self.editorTable.item(row_index, 1).setText(f"{new_depth:.3f}")
    
    # 2. Update "From Depth" of next row (if exists)
    if row_index + 1 < self.editorTable.rowCount():
        self.editorTable.item(row_index + 1, 0).setText(f"{new_depth:.3f}")
        
    # Note: The Table's internal logic (Step 2.1) will automatically 
    # re-calculate thickness for both rows via _handle_item_changed
```

---

### Summary of Dependencies

*   **`coallog_utils.py`**: Must correctly load the Excel dictionaries for the Smart Table dropdowns to work.
*   **`lithology_table.py`**: Central to the data entry experience.
*   **`main_window.py`**: Acts as the controller, receiving signals from the Graphics (drag events) and updating the Table, and receiving signals from the Table (text edits) and updating the Graphics.

This plan moves Earthworm from a passive display tool to an interactive editor. Phase 1 & 2 provide the immediate visual and data entry improvements, while Phase 3 & 4 add the professional "power user" features.