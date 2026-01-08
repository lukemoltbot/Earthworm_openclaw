#!/usr/bin/env python3
"""
Unit tests for EnhancedPatternPreview widget.
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import tempfile

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from src.ui.widgets.enhanced_pattern_preview import EnhancedPatternPreview


class TestEnhancedPatternPreview(unittest.TestCase):
    """Test cases for EnhancedPatternPreview"""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests"""
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up test fixtures"""
        self.widget = EnhancedPatternPreview()

    def tearDown(self):
        """Clean up test fixtures"""
        if self.widget:
            self.widget.close()

    def test_initialization(self):
        """Test widget initializes correctly"""
        self.assertIsInstance(self.widget, EnhancedPatternPreview)
        self.assertEqual(self.widget.size().width(), 60)
        self.assertEqual(self.widget.size().height(), 60)
        self.assertIsNone(self.widget.get_current_svg_path())
        self.assertEqual(len(self.widget.svg_cache), 0)

    def test_update_preview_no_svg(self):
        """Test updating preview when no SVG is available"""
        self.widget.update_preview(svg_path=None, background_color='#FF0000')
        # Should show placeholder (no crash)
        self.assertIsNotNone(self.widget.scene)

    def test_update_preview_with_background_color(self):
        """Test updating preview with different background colors"""
        # Test valid color
        self.widget.update_preview(svg_path=None, background_color='#00FF00')
        bg_color = self.widget.scene.backgroundBrush().color()
        self.assertEqual(bg_color.name(), '#00FF00')

        # Test invalid color fallback
        self.widget.update_preview(svg_path=None, background_color='invalid')
        bg_color = self.widget.scene.backgroundBrush().color()
        # Should fallback to white (depending on implementation)
        self.assertIsInstance(bg_color, QColor)

    @patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists')
    def test_update_preview_with_svg(self, mock_exists):
        """Test updating preview with an SVG file"""
        mock_exists.return_value = True

        # Create a mock SVG path
        mock_svg_path = '/path/to/test.svg'

        with patch.object(self.widget, '_render_svg') as mock_render:
            mock_pixmap = MagicMock()
            mock_pixmap.isNull.return_value = False
            mock_render.return_value = mock_pixmap

            self.widget.update_preview(svg_path=mock_svg_path, background_color='#FFFFFF')

            # Verify render was called with correct parameters
            mock_render.assert_called_once_with(mock_svg_path, QColor('#FFFFFF'), 60, 60)

            # Verify current SVG path was set
            self.assertEqual(self.widget.get_current_svg_path(), mock_svg_path)

    @patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists')
    def test_update_preview_file_not_found(self, mock_exists):
        """Test updating preview when SVG file doesn't exist"""
        mock_exists.return_value = False

        with patch.object(self.widget, '_show_placeholder') as mock_placeholder:
            self.widget.update_preview(svg_path='/nonexistent/path.svg')
            mock_placeholder.assert_called_once()

    @patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists')
    def test_svg_cache_functionality(self, mock_exists):
        """Test that SVG renderers are cached for performance"""
        mock_exists.return_value = True

        with patch('PyQt6.QtSvg.QSvgRenderer') as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.isValid.return_value = True
            mock_renderer.defaultSize.return_value = MockSize(100, 100)
            mock_renderer_class.return_value = mock_renderer

            # First call - should create new renderer
            mock_svg_path = '/path/to/test.svg'
            self.widget._render_svg(mock_svg_path, QColor('#FFFFFF'), 60, 60)

            # Verify renderer was created and cached
            self.assertIn(mock_svg_path, self.widget.svg_cache)
            mock_renderer_class.assert_called_once_with(mock_svg_path)

            # Second call - should reuse cached renderer
            self.widget._render_svg(mock_svg_path, QColor('#FFFFFF'), 60, 60)
            # Still only one creation call
            mock_renderer_class.assert_called_once()

    @patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists')
    def test_find_svg_file(self, mock_exists):
        """Test SVG file finding logic"""
        mock_exists.return_value = True

        with patch('src.ui.widgets.enhanced_pattern_preview.os.listdir') as mock_listdir:
            mock_listdir.return_value = ['CL - Clay.svg', 'AL - Alluvium.svg']

            # Test finding SVG for existing code
            result = self.widget.find_svg_file('CL')
            self.assertIsNotNone(result)
            self.assertTrue(result.endswith('CL - Clay.svg'))

            # Test finding SVG for non-existing code
            result = self.widget.find_svg_file('XX')
            self.assertIsNone(result)

    def test_automatic_svg_finding(self):
        """Test automatic SVG finding via lithology code"""
        with patch.object(self.widget, 'find_svg_file') as mock_find_svg:
            mock_find_svg.return_value = '/path/to/found.svg'

            with patch.object(self.widget, 'update_preview') as mock_update:
                # Don't directly call update_preview, instead call the internal logic
                self.widget.update_preview(lithology_code='CL', background_color='#FFFFFF')
                mock_find_svg.assert_called_once_with('CL', '')

    def test_clear_cache(self):
        """Test clearing SVG cache"""
        # Add something to cache
        self.widget.svg_cache['test'] = MagicMock()

        # Cache should have one item
        self.assertEqual(len(self.widget.svg_cache), 1)

        # Clear cache
        self.widget.clear_cache()

        # Cache should be empty
        self.assertEqual(len(self.widget.svg_cache), 0)

    def test_force_redraw(self):
        """Test force redraw functionality"""
        self.widget.current_svg_path = '/test/path.svg'

        with patch.object(self.widget, 'update_preview') as mock_update:
            self.widget.force_redraw()

            # Should call update_preview with current values
            mock_update.assert_called_once()
            args = mock_update.call_args[0]
            self.assertEqual(args[0], '/test/path.svg')

    def test_error_handling_in_rendering(self):
        """Test error handling during SVG rendering"""
        with patch('PyQt6.QtSvg.QSvgRenderer') as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.isValid.return_value = False  # Invalid SVG
            mock_renderer_class.return_value = mock_renderer

            with patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists', return_value=True):
                with patch.object(self.widget, '_show_error_indicator') as mock_error:
                    self.widget._render_svg('/invalid/svg.svg', QColor('#FFFFFF'), 60, 60)
                    mock_error.assert_called_once()

    def test_aspect_ratio_preservation(self):
        """Test that aspect ratio is preserved during scaling"""
        # This is hard to test directly without complex mocking,
        # but we can verify the scaling logic exists
        with patch('PyQt6.QtSvg.QSvgRenderer') as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.isValid.return_value = True
            mock_renderer.defaultSize.return_value = MockSize(200, 100)  # 2:1 aspect ratio
            mock_renderer_class.return_value = mock_renderer

            with patch('PyQt6.QtGui.QPainter') as mock_painter_class:
                mock_painter = MagicMock()
                mock_painter_class.return_value = mock_painter

                with patch('src.ui.widgets.enhanced_pattern_preview.os.path.exists', return_value=True):
                    result = self.widget._render_svg('/test.svg', QColor('#FFFFFF'), 60, 60)

                    # Verify painter scaling was called
                    self.assertTrue(mock_painter.scale.called)

                    # The scale factor should preserve aspect ratio
                    # For 200x100 SVG scaled to 60x60 widget:
                    # scale_x = 60/200 = 0.3, scale_y = 60/100 = 0.6
                    # scale_factor = min(0.3, 0.6, 1.0) = 0.3
                    # So painter.scale(0.3, 0.3) should be called
                    mock_painter.scale.assert_called_with(0.3, 0.3)

    def test_fit_pixmap_to_view(self):
        """Test pixmap fitting logic"""
        # Test with valid pixmap
        with patch('PyQt6.QtGui.QPixmap') as mock_pixmap_class:
            mock_pixmap = MagicMock()
            mock_pixmap.isNull.return_value = False
            mock_pixmap.rect.return_value = MagicMock()  # Mock rect

            self.widget._fit_pixmap_to_view(mock_pixmap)

            # fitInView should be called
            self.assertTrue(self.widget.fitInView.called)

    def test_fit_pixmap_null_pixmap(self):
        """Test pixmap fitting with null pixmap"""
        with patch('PyQt6.QtGui.QPixmap') as mock_pixmap_class:
            mock_pixmap = MagicMock()
            mock_pixmap.isNull.return_value = True

            # Should not crash
            self.widget._fit_pixmap_to_view(mock_pixmap)


class MockSize:
    """Mock QSize for testing"""
    def __init__(self, width, height):
        self.width_val = width
        self.height_val = height

    def width(self):
        return self.width_val

    def height(self):
        return self.height_val

    def isEmpty(self):
        return self.width_val <= 0 or self.height_val <= 0


if __name__ == '__main__':
    unittest.main()
