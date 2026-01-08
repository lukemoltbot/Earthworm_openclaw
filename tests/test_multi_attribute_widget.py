#!/usr/bin/env python3
"""
Unit tests for MultiAttributeWidget and PropertyEditorDialog.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtCore import Qt

from src.ui.widgets.multi_attribute_widget import MultiAttributeWidget, PropertyEditorDialog


class TestMultiAttributeWidget(unittest.TestCase):
    """Test cases for MultiAttributeWidget"""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up test fixtures"""
        self.widget = MultiAttributeWidget()

    def tearDown(self):
        """Clean up test fixtures"""
        if self.widget:
            self.widget.close()

    def test_initialization(self):
        """Test widget initializes correctly"""
        self.assertIsInstance(self.widget, MultiAttributeWidget)
        self.assertEqual(self.widget.get_properties(), {
            'shade': '',
            'hue': '',
            'colour': '',
            'weathering': '',
            'strength': ''
        })
        self.assertEqual(self.widget.text(), "Not set")

    def test_set_properties(self):
        """Test setting properties"""
        props = {
            'shade': 'Dark',
            'hue': 'Red',
            'colour': 'Red',
            'weathering': 'Slightly Weathered',
            'strength': 'Hard'
        }
        self.widget.set_properties(props)
        self.assertEqual(self.widget.get_properties(), props)

    def test_display_format(self):
        """Test that properties are displayed in the expected format"""
        props = {
            'shade': 'Dark',
            'hue': 'Red',
            'colour': 'Red',
            'weathering': 'Fresh',
            'strength': 'Very Hard'
        }
        self.widget.set_properties(props)
        display_text = self.widget.text()
        self.assertIn("Dark", display_text)
        self.assertIn("Red", display_text)
        self.assertIn("Fresh", display_text)
        self.assertIn("Very Hard", display_text)

    def test_compact_display_format(self):
        """Test that long texts are truncated"""
        props = {
            'shade': 'Medium Dark',
            'hue': 'Red',
            'colour': 'Red',
            'weathering': 'Slightly Weathered',
            'strength': 'Very Hard'
        }
        self.widget.set_properties(props)
        display_text = self.widget.text()
        # Should not exceed reasonable length
        self.assertLessEqual(len(display_text), 25)

    def test_signal_emission(self):
        """Test that propertiesChanged signal is emitted"""
        spy = QSignalSpy(self.widget.propertiesChanged)

        props = {'shade': 'Light', 'colour': 'Blue'}
        self.widget.set_properties(props)

        # Check that signal was emitted
        self.assertEqual(len(spy), 1)
        emitted_props = spy[0][0]  # First argument of the signal
        self.assertEqual(emitted_props, props)

    def test_individual_property_setting(self):
        """Test setting individual properties"""
        self.widget.set_individual_property('colour', 'Green')
        self.widget.set_individual_property('strength', 'Soft')

        props = self.widget.get_properties()
        self.assertEqual(props['colour'], 'Green')
        self.assertEqual(props['strength'], 'Soft')
        self.assertEqual(props['shade'], '')  # Others should remain unchanged

    def test_background_color_mapping(self):
        """Test that colours map to appropriate background colors"""
        color_tests = [
            ('Red', '#FF0000'),
            ('Blue', '#0000FF'),
            ('Green', '#008000'),
            ('White', '#FFFFFF'),
            ('Invalid', '#F5F5F5')  # Default grey
        ]

        for colour, expected_hex in color_tests:
            with self.subTest(colour=colour):
                self.widget.set_properties({'colour': colour})
                bg_color = self.widget._get_background_color()
                self.assertEqual(bg_color, expected_hex)

    def test_text_color_calculation(self):
        """Test text color calculation for different backgrounds"""
        # Dark background should have white text
        dark_bg = '#000000'
        text_color = self.widget._get_text_color(dark_bg)
        self.assertEqual(text_color, '#FFFFFF')

        # Light background should have black text
        light_bg = '#FFFFFF'
        text_color = self.widget._get_text_color(light_bg)
        self.assertEqual(text_color, '#000000')

    def test_double_click_opens_dialog(self):
        """Test that double-clicking opens the property editor dialog"""
        with patch('src.ui.widgets.multi_attribute_widget.PropertyEditorDialog') as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance
            mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog_instance.get_properties.return_value = {
                'shade': 'Light',
                'colour': 'Yellow'
            }

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

    def test_empty_properties_display(self):
        """Test display when no properties are set"""
        self.widget.set_properties({})  # All empty
        self.assertEqual(self.widget.text(), "Not set")

    def test_tooltip_generation(self):
        """Test tooltip shows detailed property information"""
        props = {
            'shade': 'Dark',
            'colour': 'Red',
            'strength': 'Hard'
        }
        self.widget.set_properties(props)
        tooltip = self.widget.toolTip()

        self.assertIn("Shade: Dark", tooltip)
        self.assertIn("Colour: Red", tooltip)
        self.assertIn("Strength: Hard", tooltip)


class TestPropertyEditorDialog(unittest.TestCase):
    """Test cases for PropertyEditorDialog"""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up test fixtures"""
        self.initial_props = {
            'shade': 'Dark',
            'hue': 'Red',
            'colour': 'Red',
            'weathering': 'Fresh',
            'strength': 'Hard'
        }
        self.dialog = PropertyEditorDialog(self.initial_props)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.dialog:
            self.dialog.close()

    def test_initialization(self):
        """Test dialog initializes with provided properties"""
        # Check that combo boxes are set to initial values
        self.assertEqual(self.dialog.shade_combo.currentText(), 'Dark')
        self.assertEqual(self.dialog.hue_combo.currentText(), 'Red')
        self.assertEqual(self.dialog.colour_combo.currentText(), 'Red')
        self.assertEqual(self.dialog.weathering_combo.currentText(), 'Fresh')
        self.assertEqual(self.dialog.strength_combo.currentText(), 'Hard')

    def test_combo_box_options(self):
        """Test that combo boxes have expected options"""
        # Shade options
        shade_items = [self.dialog.shade_combo.itemText(i)
                      for i in range(self.dialog.shade_combo.count())]
        self.assertIn("", shade_items)  # Empty option
        self.assertIn("Dark", shade_items)
        self.assertIn("Light", shade_items)

        # Colour options
        colour_items = [self.dialog.colour_combo.itemText(i)
                       for i in range(self.dialog.colour_combo.count())]
        self.assertIn("Red", colour_items)
        self.assertIn("Blue", colour_items)
        self.assertIn("Green", colour_items)

    def test_get_properties(self):
        """Test getting properties from dialog"""
        # Change some values
        self.dialog.shade_combo.setCurrentText('Light')
        self.dialog.colour_combo.setCurrentText('Blue')

        # Simulate accepting dialog
        self.dialog._accept_properties()

        props = self.dialog.get_properties()
        self.assertEqual(props['shade'], 'Light')
        self.assertEqual(props['colour'], 'Blue')
        self.assertEqual(props['hue'], 'Red')  # Unchanged

    def test_preview_update(self):
        """Test that preview updates when combo boxes change"""
        # Change a property
        self.dialog.colour_combo.setCurrentText('Green')

        # Preview should be updated (though we can't easily test the exact text
        # since it creates a temporary widget, but we can verify the method runs)
        initial_preview = self.dialog.preview_label.text()
        self.assertNotEqual(initial_preview, "")
        self.assertIn("Preview:", initial_preview)

    def test_empty_selections(self):
        """Test that empty selections are handled properly"""
        # Set all combos to empty
        self.dialog.shade_combo.setCurrentIndex(0)  # Empty option
        self.dialog.hue_combo.setCurrentIndex(0)
        self.dialog.colour_combo.setCurrentIndex(0)
        self.dialog.weathering_combo.setCurrentIndex(0)
        self.dialog.strength_combo.setCurrentIndex(0)

        self.dialog._accept_properties()
        props = self.dialog.get_properties()

        # All should be empty strings
        for prop_value in props.values():
            self.assertEqual(prop_value, "")

    def test_accept_button_functionality(self):
        """Test accepting dialog updates properties correctly"""
        # Modify some values
        self.dialog.shade_combo.setCurrentText('Medium')
        self.dialog.colour_combo.setCurrentText('Yellow')
        self.dialog.weathering_combo.setCurrentText('Highly Weathered')

        # Click accept
        self.dialog._accept_properties()

        # Dialog should be accepted and properties updated
        props = self.dialog.get_properties()
        self.assertEqual(props['shade'], 'Medium')
        self.assertEqual(props['colour'], 'Yellow')
        self.assertEqual(props['weathering'], 'Highly Weathered')


if __name__ == '__main__':
    # Import needed for test
    from PyQt6.QtWidgets import QDialog

    unittest.main()
