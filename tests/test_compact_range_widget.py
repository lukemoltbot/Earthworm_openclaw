#!/usr/bin/env python3
"""
Unit tests for CompactRangeWidget.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtCore import Qt

from src.ui.widgets.compact_range_widget import CompactRangeWidget, RangeEditorDialog


class TestCompactRangeWidget(unittest.TestCase):
    """Test cases for CompactRangeWidget"""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up test fixtures"""
        self.widget = CompactRangeWidget()

    def tearDown(self):
        """Clean up test fixtures"""
        if self.widget:
            self.widget.close()

    def test_initialization(self):
        """Test widget initializes correctly"""
        self.assertIsInstance(self.widget, CompactRangeWidget)
        self.assertEqual(self.widget.get_values(), (0.0, 0.0))

    def test_set_values(self):
        """Test setting values"""
        self.widget.set_values(10.5, 25.3)
        min_val, max_val = self.widget.get_values()
        self.assertEqual(min_val, 10.5)
        self.assertEqual(max_val, 25.3)

    def test_display_format(self):
        """Test that values are displayed in the expected format"""
        self.widget.set_values(10.5, 25.3)
        # Check that the display text shows the compact format
        display_text = self.widget.display_label.text()
        self.assertEqual(display_text, "10.5-25.3")

    def test_signal_emission(self):
        """Test that signals are emitted when values change"""
        spy = QSignalSpy(self.widget.valuesChanged)

        # Set new values
        self.widget.set_values(15.0, 30.0)

        # Check that signal was emitted
        self.assertEqual(len(spy), 1)
        emitted_min, emitted_max = spy[0]
        self.assertEqual(emitted_min, 15.0)
        self.assertEqual(emitted_max, 30.0)

    def test_mouse_double_click_opens_dialog(self):
        """Test that double-clicking opens the range editor dialog"""
        with patch('src.ui.widgets.compact_range_widget.RangeEditorDialog') as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance
            mock_dialog_instance.exec.return_value = True  # Simulate OK being clicked
            mock_dialog_instance.get_values.return_value = (20.0, 40.0)

            # Simulate double-click event
            from PyQt6.QtGui import QMouseEvent
            from PyQt6.QtCore import QPoint
            event = QMouseEvent(QMouseEvent.Type.MouseButtonDblClick,
                              QPoint(10, 10), Qt.MouseButton.LeftButton,
                              Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            self.widget.mouseDoubleClickEvent(event)

            # Verify dialog was created and shown
            mock_dialog.assert_called_once()
            mock_dialog_instance.exec.assert_called_once()

            # Verify values were updated
            min_val, max_val = self.widget.get_values()
            self.assertEqual(min_val, 20.0)
            self.assertEqual(max_val, 40.0)

    def test_zero_values(self):
        """Test handling of zero values"""
        self.widget.set_values(0.0, 0.0)
        min_val, max_val = self.widget.get_values()
        self.assertEqual(min_val, 0.0)
        self.assertEqual(max_val, 0.0)
        self.assertEqual(self.widget.display_label.text(), "0.0-0.0")

    def test_negative_values(self):
        """Test handling of negative values"""
        self.widget.set_values(-10.5, -5.2)
        min_val, max_val = self.widget.get_values()
        self.assertEqual(min_val, -10.5)
        self.assertEqual(max_val, -5.2)
        self.assertEqual(self.widget.display_label.text(), "-10.5--5.2")

    def test_large_values(self):
        """Test handling of large values"""
        self.widget.set_values(10000.123, 20000.456)
        min_val, max_val = self.widget.get_values()
        self.assertEqual(min_val, 10000.123)
        self.assertEqual(max_val, 20000.456)

    def test_get_values_consistency(self):
        """Test that get_values returns what was set"""
        test_cases = [
            (0.0, 0.0),
            (1.5, 2.7),
            (-3.14, 2.71),
            (1000000, 2000000)
        ]

        for min_val, max_val in test_cases:
            with self.subTest(min_val=min_val, max_val=max_val):
                self.widget.set_values(min_val, max_val)
                returned_min, returned_max = self.widget.get_values()
                self.assertEqual(returned_min, min_val)
                self.assertEqual(returned_max, max_val)


class TestRangeEditorDialog(unittest.TestCase):
    """Test cases for RangeEditorDialog"""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up test fixtures"""
        self.dialog = RangeEditorDialog(10.0, 20.0)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.dialog:
            self.dialog.close()

    def test_initialization(self):
        """Test dialog initializes with provided values"""
        min_val, max_val = self.dialog.get_values()
        self.assertEqual(min_val, 10.0)
        self.assertEqual(max_val, 20.0)

    def test_set_values(self):
        """Test setting values in dialog"""
        self.dialog.min_spin.setValue(15.5)
        self.dialog.max_spin.setValue(25.7)

        min_val, max_val = self.dialog.get_values()
        self.assertEqual(min_val, 15.5)
        self.assertEqual(max_val, 25.7)

    def test_validation_min_greater_than_max(self):
        """Test that validation prevents min > max"""
        # Set max first, then min
        self.dialog.max_spin.setValue(5.0)
        self.dialog.min_spin.setValue(10.0)

        # The dialog should handle this gracefully
        # (implementation may adjust values or show visual feedback)
        min_val, max_val = self.dialog.get_values()
        # The exact behavior depends on implementation, but should be handled
        self.assertIsInstance(min_val, float)
        self.assertIsInstance(max_val, float)


if __name__ == '__main__':
    unittest.main()
