import os
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPixmap, QPainter, QColor

class SvgRenderer:
    def __init__(self):
        self.renderer_cache = {}

    def get_renderer(self, svg_path):
        if not svg_path:
            return None
        if svg_path not in self.renderer_cache:
            if os.path.exists(svg_path):
                self.renderer_cache[svg_path] = QSvgRenderer(svg_path)
            else:
                return None
        return self.renderer_cache.get(svg_path)

    def render_svg(self, svg_path, width, height, background_color):
        if not svg_path:
            return None
            
        renderer = self.get_renderer(svg_path)
        if not renderer or not renderer.isValid():
            return None

        pixmap = QPixmap(width, height)
        pixmap.fill(background_color)
        
        painter = QPainter()
        # Explicitly begin painting and check if it was successful
        if painter.begin(pixmap):
            try:
                renderer.render(painter)
            finally:
                painter.end() # Ensure painter is ended even if render fails
        
        return pixmap
