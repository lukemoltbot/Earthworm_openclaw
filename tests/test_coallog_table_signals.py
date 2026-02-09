"""
Test for CoalLogTableWidget signal fixes
Specifically tests the rowSelectionChangedSignal that was missing
"""

import sys
import os
import pytest
from pytestqt.qtbot import QtBot

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set offscreen platform for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from src.ui.widgets.coallog_table_widget import CoalLogTableWidget

@pytest.fixture
def app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

@pytest.fixture
def coallog_table(qtbot):
    """Create CoalLogTableWidget instance for testing"""
    widget = CoalLogTableWidget()
    qtbot.addWidget(widget)
    return widget

def test_row_selection_changed_signal_exists(coallog_table):
    """Test that rowSelectionChangedSignal exists"""
    assert hasattr(coallog_table, 'rowSelectionChangedSignal'), \
        "CoalLogTableWidget should have rowSelectionChangedSignal"
    
    # Verify it's a pyqtSignal (check differently for bound vs unbound)
    from PyQt6.QtCore import pyqtSignal
    signal_type = type(pyqtSignal())
    # Bound signals have different type, check if it has the right attributes
    assert hasattr(coallog_table.rowSelectionChangedSignal, 'connect'), \
        "rowSelectionChangedSignal should have connect method"
    assert hasattr(coallog_table.rowSelectionChangedSignal, 'emit'), \
        "rowSelectionChangedSignal should have emit method"

def test_row_selection_changed_signal_emitted(coallog_table, qtbot):
    """Test that rowSelectionChangedSignal is emitted when selection changes"""
    # Block signals while setting up to avoid recursion
    coallog_table.blockSignals(True)
    
    # Add some test data with actual items (empty to avoid validation errors)
    coallog_table.setRowCount(3)
    coallog_table.setColumnCount(2)
    
    # Fill table with empty items so selection works without validation errors
    for row in range(3):
        for col in range(2):
            item = coallog_table.item(row, col)
            if item is None:
                from PyQt6.QtWidgets import QTableWidgetItem
                item = QTableWidgetItem("")  # Empty item to avoid validation
                coallog_table.setItem(row, col, item)
    
    # Unblock signals
    coallog_table.blockSignals(False)
    
    # Clear any initial selection
    coallog_table.clearSelection()
    qtbot.wait(100)  # Small delay
    
    # Create signal spy
    with qtbot.waitSignal(coallog_table.rowSelectionChangedSignal, timeout=1000) as blocker:
        # Select a row
        coallog_table.selectRow(1)
    
    # Verify signal was emitted with correct row index
    assert blocker.signal_triggered, "rowSelectionChangedSignal should be emitted"
    assert blocker.args == [1], f"Signal should emit row index 1, got {blocker.args}"

def test_row_selection_changed_signal_no_selection(coallog_table, qtbot):
    """Test that rowSelectionChangedSignal emits -1 when no selection"""
    # Add some test data
    coallog_table.setRowCount(3)
    coallog_table.setColumnCount(2)
    
    # First select a row
    coallog_table.selectRow(1)
    
    # Now clear selection and check signal
    with qtbot.waitSignal(coallog_table.rowSelectionChangedSignal, timeout=1000) as blocker:
        coallog_table.clearSelection()
    
    # Verify signal was emitted with -1
    assert blocker.signal_triggered, "rowSelectionChangedSignal should be emitted on clear"
    assert blocker.args == [-1], f"Signal should emit -1 for no selection, got {blocker.args}"

def test_data_changed_signal_exists(coallog_table):
    """Test that dataChangedSignal exists"""
    assert hasattr(coallog_table, 'dataChangedSignal'), \
        "CoallogTableWidget should have dataChangedSignal"

def test_validation_error_signal_exists(coallog_table):
    """Test that validationErrorSignal exists"""
    assert hasattr(coallog_table, 'validationErrorSignal'), \
        "CoallogTableWidget should have validationErrorSignal"

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])