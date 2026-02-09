# PyQt version-agnostic imports
try:
    # Try PyQt6 first
    from PyQt6.QtWidgets import (
        QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QPushButton, QComboBox, QLabel, QGraphicsView, QFileDialog, QMessageBox,
        QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QColorDialog, QGraphicsScene, QDoubleSpinBox, QCheckBox, QSlider, QSpinBox, QFrame, QSplitter, QAbstractItemView, QMdiArea, QMdiSubWindow, QDockWidget, QTreeView)
    # Import QAction separately to avoid Windows import issues
    try:
        from PyQt6.QtWidgets import QAction
    except ImportError:
        # Some PyQt6 installations have QAction in QtGui
        from PyQt6.QtGui import QAction
    from PyQt6.QtGui import QPainter, QPixmap, QColor, QFont, QBrush
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtSvgWidgets import QGraphicsSvgItem
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QPointF, QTimer, QDir
    # QFileSystemModel is in QtCore in PyQt6
    from PyQt6.QtCore import QFileSystemModel
    PYQT_VERSION = 6
except ImportError:
    # Fall back to PyQt5
    from PyQt5.QtWidgets import (
        QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QPushButton, QComboBox, QLabel, QGraphicsView, QFileDialog, QMessageBox,
        QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QColorDialog, QGraphicsScene, QDoubleSpinBox, QCheckBox, QSlider, QSpinBox, QFrame, QSplitter, QAbstractItemView, QMdiArea, QMdiSubWindow, QDockWidget, QTreeView,  QFileSystemModel)
    # Import QAction separately to avoid Windows import issues
    from PyQt5.QtWidgets import QAction
    from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont, QBrush
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtSvgWidgets import QGraphicsSvgItem
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QPointF, QTimer, QDir
    PYQT_VERSION = 5
import pandas as pd
import numpy as np
import os
import json
import traceback

from ..core.data_processor import DataProcessor
from ..core.analyzer import Analyzer
from ..core.config import DEFAULT_LITHOLOGY_RULES, DEPTH_COLUMN, DEFAULT_SEPARATOR_THICKNESS, DRAW_SEPARATOR_LINES, CURVE_RANGES, INVALID_DATA_VALUE
from ..core.coallog_utils import load_coallog_dictionaries
from ..core.coallog_schema import get_coallog_schema
from .widgets.stratigraphic_column import StratigraphicColumn
from .widgets.svg_renderer import SvgRenderer
from .widgets.curve_plotter import CurvePlotter # Import CurvePlotter
from .widgets.enhanced_range_gap_visualizer import EnhancedRangeGapVisualizer # Import enhanced widget
from ..core.settings_manager import load_settings, save_settings
from .dialogs.researched_defaults_dialog import ResearchedDefaultsDialog # Import new dialog
from ..utils.range_analyzer import RangeAnalyzer # Import range analyzer
from .widgets.compact_range_widget import CompactRangeWidget # Import compact widgets
from .widgets.multi_attribute_widget import MultiAttributeWidget
from .widgets.enhanced_pattern_preview import EnhancedPatternPreview
from .widgets.lithology_table import LithologyTableWidget
from .widgets.coallog_table_widget import CoalLogTableWidget
from .dialogs.tabbed_settings_dialog import TabbedSettingsDialog

class SvgPreviewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.svg_renderer = SvgRenderer()

    def update_preview(self, svg_path, color):
        self.scene.clear()
        # Safety check to prevent drawing on a zero-size widget
        if self.width() <= 0 or self.height() <= 0:
            return
        pixmap = self.svg_renderer.render_svg(svg_path, self.width(), self.height(), color)
        if pixmap is not None:
            self.scene.addPixmap(pixmap)
        else:
            self.scene.setBackgroundBrush(QColor(color))
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class Worker(QObject):
    finished = pyqtSignal(pd.DataFrame, pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, file_path, mnemonic_map, lithology_rules, use_researched_defaults, merge_thin_units=False, merge_threshold=0.05, smart_interbedding=False, smart_interbedding_max_sequence_length=10, smart_interbedding_thick_unit_threshold=0.5, use_fallback_classification=False):
        super().__init__()
        self.file_path = file_path
        self.mnemonic_map = mnemonic_map
        self.lithology_rules = lithology_rules
        self.use_researched_defaults = use_researched_defaults
        self.merge_thin_units = merge_thin_units
        self.merge_threshold = merge_threshold
        self.smart_interbedding = smart_interbedding
        self.smart_interbedding_max_sequence_length = smart_interbedding_max_sequence_length
        self.smart_interbedding_thick_unit_threshold = smart_interbedding_thick_unit_threshold
        self.use_fallback_classification = use_fallback_classification

    def run(self):
        try:
            data_processor = DataProcessor()
            analyzer = Analyzer()
            dataframe, _ = data_processor.load_las_file(self.file_path)
            
            # Ensure all required curve mnemonics are in the map for preprocessing
            # Add default mappings if not already present in mnemonic_map
            full_mnemonic_map = self.mnemonic_map.copy()
            if 'short_space_density' not in full_mnemonic_map:
                full_mnemonic_map['short_space_density'] = 'DENS' # Common mnemonic for short space density
            if 'long_space_density' not in full_mnemonic_map:
                full_mnemonic_map['long_space_density'] = 'LSD' # Common mnemonic for long space density

            processed_dataframe = data_processor.preprocess_data(dataframe, full_mnemonic_map)
            # Use appropriate classification method based on settings
            if hasattr(self, 'analysis_method') and self.analysis_method == "simple":
                classified_dataframe = analyzer.classify_rows_simple(processed_dataframe, self.lithology_rules, full_mnemonic_map)
            else:
                classified_dataframe = analyzer.classify_rows(processed_dataframe, self.lithology_rules, full_mnemonic_map, self.use_researched_defaults, self.use_fallback_classification)
            units_dataframe = analyzer.group_into_units(classified_dataframe, self.lithology_rules, self.smart_interbedding, self.smart_interbedding_max_sequence_length, self.smart_interbedding_thick_unit_threshold)
            if self.merge_thin_units:
                units_dataframe = analyzer.merge_thin_units(units_dataframe, self.merge_threshold)
            template_path = os.path.join(os.getcwd(), 'src', 'assets', 'TEMPLATE.xlsx')
            output_path = os.path.join(os.path.dirname(self.file_path), "output_lithology.xlsx")
            def log_progress(message):
                print(f"Worker Log: {message}")
            success = analyzer.save_to_template(classified_dataframe, template_path, output_path, callback=log_progress, units=units_dataframe)
            if not success:
                raise Exception("Failed to save results to Excel template.")
            self.finished.emit(units_dataframe, classified_dataframe)
        except Exception as e:
            full_traceback = traceback.format_exc()
            self.error.emit(f"Analysis failed: {str(e)}\n\nTraceback:\n{full_traceback}")



# ====== MDI SUB-WINDOW CLASS ======
class HoleEditorSubWindow(QMdiSubWindow):
    """
    MDI Sub-window for individual drill hole editing.
    Contains the Earthworm editing interface for one drill hole.
    """
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.main_window = parent  # Reference to main window
        self.setWindowTitle(f"Hole Editor - {os.path.basename(file_path) if file_path else 'Untitled'}")
        
        # Placeholder widget - will be replaced with actual Earthworm interface
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel(f"Drill Hole: {file_path or 'New Hole'}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        self.setWidget(placeholder)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    
    def load_file(self, file_path):
        """Load a drill hole file into this editor"""
        self.file_path = file_path
        self.setWindowTitle(f"Hole Editor - {os.path.basename(file_path)}")
        # TODO: Implement actual file loading



# ====== PROJECT INDEXER SIDEBAR ======
class ProjectIndexerSidebar(QDockWidget):
    """
    Persistent project indexer sidebar for Earthworm.
    Provides a file browser for quick access to drill hole files.
    """
    
    def __init__(self, parent=None):
        super().__init__("Project Indexer", parent)
        self.setObjectName("ProjectIndexerSidebar")
        
        # Create main widget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        # Header
        header = QLabel("Project Files")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(header)
        
        # Create file system model
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.homePath())
        
        # Set filters for geological file types
        self.file_model.setNameFilters(["*.csv", "*.xlsx", "*.las", "*.txt"])
        self.file_model.setNameFilterDisables(False)
        
        # Create tree view
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(QDir.homePath()))
        
        # Configure tree view
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        
        # Hide unnecessary columns
        self.tree_view.hideColumn(1)  # Size
        self.tree_view.hideColumn(2)  # Type
        self.tree_view.hideColumn(3)  # Date Modified
        
        # Set column width
        self.tree_view.setColumnWidth(0, 250)
        
        # Connect double-click signal
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        
        layout.addWidget(self.tree_view)
        
        # Status label
        self.status_label = QLabel(f"Browsing: {QDir.homePath()}")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 3px;")
        layout.addWidget(self.status_label)
        
        self.setWidget(main_widget)
        
        # Set dock widget properties
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                        QDockWidget.DockWidgetFeature.DockWidgetFloatable)
    
    
    def on_file_double_clicked(self, index):
        """Handle file double-click in sidebar"""
        if index.isValid():
            file_path = self.file_model.filePath(index)
            if os.path.isfile(file_path) and file_path.lower().endswith(('.csv', '.xlsx', '.las')):
                # Call parent method to open file
                if self.parent():
                    self.parent().open_hole_with_path(file_path)
    def set_root_path(self, path):
        """Set the root path for the file browser"""
        if os.path.exists(path):
            self.tree_view.setRootIndex(self.file_model.index(path))
            self.status_label.setText(f"Browsing: {os.path.basename(path)}")
    
    def get_selected_file(self):
        """Get the currently selected file path"""
        index = self.tree_view.currentIndex()
        if index.isValid():
            return self.file_model.filePath(index)
        return None
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Earthworm Borehole Logger")

        # Load window geometry from settings or use defaults
        self.load_window_geometry()
        self.las_file_path = None
        
        # Create menu bar
        self.create_menus()
    
    def create_menus(self):
        """Create menu bar with MDI Window menu"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Hole", self)
        new_action.triggered.connect(self.new_hole)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Hole", self)
        open_action.triggered.connect(self.open_hole)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Settings action
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        edit_menu.addAction(settings_action)
        
        edit_menu.addSeparator()
        # TODO: Add other edit actions
        
        # View menu (placeholder)
        view_menu = menubar.addMenu("&View")
        # TODO: Add view actions
        
        # Window menu (MDI specific)
        self.window_menu = menubar.addMenu("&Window")
        
        tile_action = QAction("&Tile", self)
        tile_action.triggered.connect(self.mdi_area.tileSubWindows)
        self.window_menu.addAction(tile_action)
        
        cascade_action = QAction("&Cascade", self)
        cascade_action.triggered.connect(self.mdi_area.cascadeSubWindows)
        self.window_menu.addAction(cascade_action)
        
        self.window_menu.addSeparator()
        
        close_action = QAction("&Close Active", self)
        close_action.triggered.connect(self.close_active_window)
        self.window_menu.addAction(close_action)
        
        close_all_action = QAction("Close &All", self)
        close_all_action.triggered.connect(self.close_all_windows)
        self.window_menu.addAction(close_all_action)
        
        # Connect window updates
        self.mdi_area.subWindowActivated.connect(self.update_window_menu)
        
        # Help menu (placeholder)
        help_menu = menubar.addMenu("&Help")
        # TODO: Add help actions


    def load_window_geometry(self):
        """Load window size and position from settings or set reasonable defaults based on screen size."""
        try:
            from PyQt6.QtGui import QGuiApplication
        except ImportError:
            from PyQt5.QtGui import QGuiApplication
        try:
            from PyQt6.QtCore import QRect
        except ImportError:
            from PyQt5.QtCore import QRect

        # Get the primary screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            # Set reasonable default size (80% of screen size, but not larger than 1400x900)
            default_width = min(int(screen_width * 0.8), 1400)
            default_height = min(int(screen_height * 0.8), 900)

            # Try to load saved geometry from settings
            app_settings = load_settings()
            saved_geometry = app_settings.get("window_geometry")

            if saved_geometry and isinstance(saved_geometry, dict):
                # Restore saved geometry if it exists
                x = saved_geometry.get('x', 50)
                y = saved_geometry.get('y', 50)
                width = saved_geometry.get('width', default_width)
                height = saved_geometry.get('height', default_height)
                maximized = saved_geometry.get('maximized', False)

                # Ensure the window fits within the current screen
                if width > screen_width:
                    width = screen_width - 100
                if height > screen_height:
                    height = screen_height - 100
                if x + width > screen_width:
                    x = max(0, screen_width - width - 50)
                if y + height > screen_height:
                    y = max(0, screen_height - height - 50)

                self.setGeometry(x, y, width, height)

                if maximized:
                    self.showMaximized()
            else:
                # Use default geometry centered on screen
                x = (screen_width - default_width) // 2
                y = (screen_height - default_height) // 2
                self.setGeometry(x, y, default_width, default_height)

        # Set minimum size to prevent the window from becoming unusable
        self.setMinimumSize(800, 600)

        # Load settings on startup
        app_settings = load_settings()
        self.lithology_rules = app_settings["lithology_rules"]
        self.initial_separator_thickness = app_settings["separator_thickness"]
        self.initial_draw_separators = app_settings["draw_separator_lines"]
        self.initial_curve_inversion_settings = app_settings["curve_inversion_settings"]
        self.initial_curve_thickness = app_settings["curve_thickness"] # Load new setting
        self.use_researched_defaults = app_settings["use_researched_defaults"]
        self.analysis_method = app_settings.get("analysis_method", "standard")  # Load analysis method
        self.merge_thin_units = app_settings.get("merge_thin_units", False)
        self.merge_threshold = app_settings.get("merge_threshold", 0.05)
        self.smart_interbedding = app_settings.get("smart_interbedding", False)
        self.smart_interbedding_max_sequence_length = app_settings.get("smart_interbedding_max_sequence_length", 10)
        self.smart_interbedding_thick_unit_threshold = app_settings.get("smart_interbedding_thick_unit_threshold", 0.5)

        self.lithology_qualifier_map = self.load_lithology_qualifier_map()
        self.coallog_data = self.load_coallog_data()

        # Store most recent analysis results for reporting
        self.last_classified_dataframe = None
        self.last_units_dataframe = None
        self.last_analysis_file = None
        self.last_analysis_timestamp = None

        # Initialize range analyzer and visualizer
        self.range_analyzer = RangeAnalyzer()
        self.range_visualizer = EnhancedRangeGapVisualizer()
        self.range_visualizer.set_range_analyzer(self.range_analyzer)

        # Initialize debouncing timer for gap visualization updates
        self.gap_update_timer = QTimer(self)
        self.gap_update_timer.setSingleShot(True)
        self.gap_update_timer.timeout.connect(self._perform_gap_visualization_update)

        self.mdi_area = QMdiArea()
        self.mdi_area.setViewMode(QMdiArea.ViewMode.SubWindowView)
        
        # Initialize window counter for new windows
        self.window_counter = 1
        
        # Create main tab widget for settings and editor
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create project indexer sidebar
        self.project_sidebar = ProjectIndexerSidebar(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_sidebar)
        
        # Set initial path to user's Documents folder
        docs_path = os.path.expanduser("~/Documents")
        if os.path.exists(docs_path):
            self.project_sidebar.set_root_path(docs_path)
        else:
            self.project_sidebar.set_root_path(QDir.homePath())
        
        self.control_panel_layout = QHBoxLayout()
        self.loadLasButton = QPushButton("Load LAS File")
        self.control_panel_layout.addWidget(self.loadLasButton)
        self.control_panel_layout.addWidget(QLabel("Gamma Ray Curve:"))
        self.gammaRayComboBox = QComboBox()
        self.control_panel_layout.addWidget(self.gammaRayComboBox)

        # Add density curves (Short Space Density maps to both density fields)
        self.control_panel_layout.addWidget(QLabel("Short Space Density:"))
        self.shortSpaceDensityComboBox = QComboBox()
        self.control_panel_layout.addWidget(self.shortSpaceDensityComboBox)
        # Hidden combo box for backward compatibility with density field mapping
        self.densityComboBox = QComboBox()
        self.control_panel_layout.addWidget(QLabel("Long Space Density:"))
        self.longSpaceDensityComboBox = QComboBox()
        self.control_panel_layout.addWidget(self.longSpaceDensityComboBox)

        self.runAnalysisButton = QPushButton("Run Analysis")
        self.control_panel_layout.addWidget(self.runAnalysisButton)
        self.settings_tab = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_tab)
        self.tab_widget.addTab(self.settings_tab, "Settings")

        self.editor_tab = QWidget()

        # Create a single CurvePlotter widget
        self.curvePlotter = CurvePlotter()

        self.stratigraphicColumnView = StratigraphicColumn()
        
        # Initialize table based on settings (default to 37-column CoalLog table)
        app_settings = load_settings()
        use_coallog_table = app_settings.get("use_coallog_table", True)
        
        if use_coallog_table:
            self.editorTable = CoalLogTableWidget(coallog_data=self.coallog_data)
            print("Using 37-column CoalLog table")
        else:
            self.editorTable = LithologyTableWidget(coallog_data=self.coallog_data)
            print("Using 13-column lithology table")
        
        self.exportCsvButton = QPushButton("Export to CSV")

        # Connect table row selection to stratigraphic column highlighting
        self.editorTable.rowSelectionChangedSignal.connect(self._on_table_row_selected)

        self.tab_widget.addTab(self.editor_tab, "Editor")
        self.connect_signals()
        self.load_default_lithology_rules()
        self.setup_settings_tab()
        self.setup_editor_tab()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self._synchronize_views()

    def _synchronize_views(self):
        """Connects the two views to scroll in sync with perfect 1:1 depth alignment."""
        self._is_syncing = False # A flag to prevent recursive sync

        def sync_from(source_view, target_view, include_table=False):
            def on_scroll():
                if self._is_syncing:
                    return
                self._is_syncing = True

                # Get the visible depth range from the source view
                source_viewport = source_view.viewport()
                source_scene_rect = source_view.scene.sceneRect()

                # Map viewport corners to scene coordinates
                top_left = source_view.mapToScene(source_viewport.rect().topLeft())
                bottom_left = source_view.mapToScene(source_viewport.rect().bottomLeft())

                # Calculate visible depth range in scene coordinates
                source_min_depth = source_scene_rect.top() / source_view.depth_scale
                visible_top_depth = top_left.y() / source_view.depth_scale + source_min_depth
                visible_bottom_depth = bottom_left.y() / source_view.depth_scale + source_min_depth

                # Calculate the center depth
                center_depth = (visible_top_depth + visible_bottom_depth) / 2

                # Get target view's scene information
                target_scene_rect = target_view.scene.sceneRect()
                target_min_depth = target_scene_rect.top() / target_view.depth_scale

                # Calculate target scene position for the center depth
                target_center_y = (center_depth - target_min_depth) * target_view.depth_scale

                # Center the target view on the same depth
                target_view.centerOn(QPointF(target_view.viewport().width() / 2, target_center_y))

                # If requested, also sync table to show corresponding rows
                if include_table and self.last_units_dataframe is not None and not self.last_units_dataframe.empty:
                    self._sync_table_to_depth(center_depth)

                self._is_syncing = False
            return on_scroll

        # Connect curve plotter and strat column for mutual scrolling with table sync
        self.curvePlotter.verticalScrollBar().valueChanged.connect(
            sync_from(self.curvePlotter, self.stratigraphicColumnView, include_table=True)
        )
        self.stratigraphicColumnView.verticalScrollBar().valueChanged.connect(
            sync_from(self.stratigraphicColumnView, self.curvePlotter, include_table=True)
        )

    def _sync_table_to_depth(self, center_depth):
        """Scroll the lithology table to show rows near the given depth."""
        if self.last_units_dataframe is None or self.last_units_dataframe.empty:
            return

        # Find the row in units dataframe closest to center_depth
        units_df = self.last_units_dataframe
        if 'from_depth' not in units_df.columns or 'to_depth' not in units_df.columns:
            return

        # Find units that contain the center depth
        containing_units = units_df[
            (units_df['from_depth'] <= center_depth) &
            (units_df['to_depth'] >= center_depth)
        ]

        if not containing_units.empty:
            # Get the index of the first matching unit
            row_index = containing_units.index[0]
            # Scroll to make this row visible
            self.editorTable.scrollToItem(
                self.editorTable.item(row_index, 0),
                QAbstractItemView.ScrollHint.PositionAtCenter
            )

    def _on_table_row_selected(self, row_index):
        """Handle table row selection and highlight corresponding stratigraphic unit."""
        if row_index == -1:
            # No selection - clear highlight
            self.stratigraphicColumnView.highlight_unit(None)
        else:
            # Highlight the corresponding unit in stratigraphic column
            self.stratigraphicColumnView.highlight_unit(row_index)
    
    def _on_table_data_changed(self, data):
        """Handle table data changes and update graphics."""
        # When table data changes, we should update the stratigraphic column
        # For now, just print a debug message
        print(f"Table data changed, should update graphics. Data: {data}")
        # TODO: Implement graphics update when table data changes
    
    def _on_table_validation_error(self, message, row, col):
        """Handle table validation errors."""
        QMessageBox.warning(self, "Validation Error", 
                           f"Validation error at row {row+1}, column {col+1}:\n{message}")

    def find_svg_file(self, lithology_code, lithology_qualifier=''):
        svg_dir = os.path.join(os.getcwd(), 'src', 'assets', 'svg')
        
        if not isinstance(lithology_code, str) or not lithology_code:
            print(f"DEBUG (MainWindow): Invalid lithology_code provided: {lithology_code}")
            return None

        # Construct the base prefix for the SVG file
        base_prefix = lithology_code.upper()

        # If a qualifier is provided, try to find a combined SVG first
        if lithology_qualifier and isinstance(lithology_qualifier, str):
            combined_code = (base_prefix + lithology_qualifier.upper()).strip()
            combined_filename_prefix = combined_code + ' '
            print(f"DEBUG (MainWindow): Searching for combined SVG with prefix '{combined_filename_prefix}' in '{svg_dir}'")
            for filename in os.listdir(svg_dir):
                if filename.upper().startswith(combined_filename_prefix):
                    found_path = os.path.join(svg_dir, filename)
                    print(f"DEBUG (MainWindow): Found combined SVG: {found_path}")
                    return found_path
            print(f"DEBUG (MainWindow): No combined SVG found for prefix '{combined_filename_prefix}'")

        # If no combined SVG found or no qualifier provided, fall back to just the lithology code
        single_filename_prefix = base_prefix + ' '
        print(f"DEBUG (MainWindow): Falling back to searching for single SVG with prefix '{single_filename_prefix}' in '{svg_dir}'")
        for filename in os.listdir(svg_dir):
            if filename.upper().startswith(single_filename_prefix):
                found_path = os.path.join(svg_dir, filename)
                print(f"DEBUG (MainWindow): Found single SVG: {found_path}")
                return found_path
        
        print(f"DEBUG (MainWindow): No SVG found for lithology code '{lithology_code}' (and qualifier '{lithology_qualifier}')")
        return None

    def connect_signals(self):
        self.loadLasButton.clicked.connect(self.load_las_file_dialog)
        self.runAnalysisButton.clicked.connect(self.run_analysis)
        self.exportCsvButton.clicked.connect(self.export_editor_data_to_csv)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Connect table data changed signal if it exists (for CoalLogTableWidget)
        if hasattr(self.editorTable, 'dataChangedSignal'):
            self.editorTable.dataChangedSignal.connect(self._on_table_data_changed)
        
        # Connect table validation error signal if it exists
        if hasattr(self.editorTable, 'validationErrorSignal'):
            self.editorTable.validationErrorSignal.connect(self._on_table_validation_error)

    def load_las_file_dialog(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open LAS File", "", "LAS Files (*.las);;All Files (*)")
        if file_path:
            self.las_file_path = file_path
            self.load_las_data()

    def load_coallog_data(self):
        try:
            coallog_path = os.path.join(os.getcwd(), 'src', 'assets', 'CoalLog v3.1 Dictionaries.xlsx')
            return load_coallog_dictionaries(coallog_path)
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", f"Failed to load CoalLog dictionaries: {e}")
            return None

    def load_lithology_qualifier_map(self):
        try:
            qualifier_map_path = os.path.join(os.getcwd(), 'src', 'assets', 'litho_lithoQuals.json')
            with open(qualifier_map_path, 'r') as f:
                data = json.load(f)
                return data.get("lithology_qualifiers", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load lithology qualifier map: {e}")
            return {}

    def load_las_data(self):
        if not self.las_file_path:
            return
        try:
            data_processor = DataProcessor()
            dataframe, mnemonics = data_processor.load_las_file(self.las_file_path)
            self.gammaRayComboBox.clear()
            self.densityComboBox.clear()
            self.shortSpaceDensityComboBox.clear()
            self.longSpaceDensityComboBox.clear()

            self.gammaRayComboBox.addItems(mnemonics)
            self.densityComboBox.addItems(mnemonics)
            self.shortSpaceDensityComboBox.addItems(mnemonics)
            self.longSpaceDensityComboBox.addItems(mnemonics)

            if 'GR' in mnemonics:
                self.gammaRayComboBox.setCurrentText('GR')
            # Both density combo boxes get the same default selection
            if 'RHOB' in mnemonics:
                self.densityComboBox.setCurrentText('RHOB')
                self.shortSpaceDensityComboBox.setCurrentText('RHOB')
            if 'DENS' in mnemonics: # Assuming 'DENS' for short space density
                self.densityComboBox.setCurrentText('DENS')
                self.shortSpaceDensityComboBox.setCurrentText('DENS')
            if 'LSD' in mnemonics: # Assuming 'LSD' for long space density
                self.longSpaceDensityComboBox.setCurrentText('LSD')

            QMessageBox.information(self, "LAS File Loaded", f"Successfully loaded {os.path.basename(self.las_file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load LAS file: {e}")
            self.las_file_path = None

    def load_default_lithology_rules(self):
        self.lithology_rules = DEFAULT_LITHOLOGY_RULES

    def on_tab_changed(self, index):
        if self.tab_widget.tabText(index) != "Settings":
            self.save_settings_rules_from_table()

    def setup_settings_tab(self):
        # Add data processing controls at the top
        self.settings_layout.addWidget(QLabel("Data Processing Controls:"))
        self.settings_layout.addLayout(self.control_panel_layout)

        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.settings_layout.addWidget(separator)

        self.settings_rules_table = QTableWidget()
        self.settings_rules_table.setColumnCount(9)
        self.settings_rules_table.setHorizontalHeaderLabels([
            "Name", "Code", "Qualifier", "Gamma Range", "Density Range",
            "Visual Props", "Background", "Preview", "Actions"
        ])
        # Set column widths for compact layout
        self.settings_rules_table.setColumnWidth(0, 140)  # Name
        self.settings_rules_table.setColumnWidth(1, 60)   # Code
        self.settings_rules_table.setColumnWidth(2, 100)  # Qualifier
        self.settings_rules_table.setColumnWidth(3, 80)   # Gamma Range
        self.settings_rules_table.setColumnWidth(4, 80)   # Density Range
        self.settings_rules_table.setColumnWidth(5, 120)  # Visual Props
        self.settings_rules_table.setColumnWidth(6, 60)   # Background
        self.settings_rules_table.setColumnWidth(7, 60)   # Preview
        self.settings_rules_table.setColumnWidth(8, 80)   # Actions
        self.settings_rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.settings_layout.addWidget(self.settings_rules_table)
        self.settings_button_layout = QHBoxLayout()
        self.addRuleButton = QPushButton("Add Rule")
        self.removeRuleButton = QPushButton("Remove Rule")
        self.settings_button_layout.addWidget(self.addRuleButton)
        self.settings_button_layout.addWidget(self.removeRuleButton)
        self.settings_layout.addLayout(self.settings_button_layout)

        # New controls for stratigraphic column separators
        self.separator_settings_layout = QHBoxLayout()
        self.separator_settings_layout.addWidget(QLabel("Separator Line Thickness:"))
        self.separatorThicknessSpinBox = QDoubleSpinBox()
        self.separatorThicknessSpinBox.setRange(0.0, 5.0)
        self.separatorThicknessSpinBox.setSingleStep(0.1)
        self.separator_settings_layout.addWidget(self.separatorThicknessSpinBox)

        self.drawSeparatorsCheckBox = QCheckBox("Draw Separator Lines")
        self.separator_settings_layout.addWidget(self.drawSeparatorsCheckBox)
        self.settings_layout.addLayout(self.separator_settings_layout)

        # New controls for curve line thickness
        self.curve_thickness_layout = QHBoxLayout()
        self.curve_thickness_layout.addWidget(QLabel("Curve Line Thickness:"))
        self.curveThicknessSpinBox = QDoubleSpinBox()
        self.curveThicknessSpinBox.setRange(0.1, 5.0)
        self.curveThicknessSpinBox.setSingleStep(0.1)
        self.curve_thickness_layout.addWidget(self.curveThicknessSpinBox)
        self.settings_layout.addLayout(self.curve_thickness_layout)

        # New controls for curve inversion
        self.curve_inversion_layout = QHBoxLayout()
        self.invertGammaCheckBox = QCheckBox("Invert Gamma")
        self.invertShortSpaceDensityCheckBox = QCheckBox("Invert Short Space Density")
        self.invertLongSpaceDensityCheckBox = QCheckBox("Invert Long Space Density")
        self.curve_inversion_layout.addWidget(self.invertGammaCheckBox)
        self.curve_inversion_layout.addWidget(self.invertShortSpaceDensityCheckBox)
        self.curve_inversion_layout.addWidget(self.invertLongSpaceDensityCheckBox)
        self.settings_layout.addLayout(self.curve_inversion_layout)

        # New buttons for saving/loading settings
        self.settings_file_buttons_layout = QHBoxLayout()
        self.saveAsSettingsButton = QPushButton("Save Settings As...")
        self.updateSettingsButton = QPushButton("Update Settings")
        self.loadSettingsButton = QPushButton("Load Settings...")
        self.settings_file_buttons_layout.addWidget(self.saveAsSettingsButton)
        self.settings_file_buttons_layout.addWidget(self.updateSettingsButton)
        self.settings_file_buttons_layout.addWidget(self.loadSettingsButton)
        
        # Add new controls for researched defaults
        self.useResearchedDefaultsCheckBox = QCheckBox("Apply Researched Defaults for Missing Ranges")
        self.useResearchedDefaultsCheckBox.setChecked(self.use_researched_defaults)
        self.settings_file_buttons_layout.addWidget(self.useResearchedDefaultsCheckBox)

        # Add control for merging thin units
        self.mergeThinUnitsCheckBox = QCheckBox("Merge thin lithology units (< 5cm)")
        self.mergeThinUnitsCheckBox.setChecked(self.merge_thin_units)
        self.settings_file_buttons_layout.addWidget(self.mergeThinUnitsCheckBox)

        # Add control for smart interbedding
        self.smartInterbeddingCheckBox = QCheckBox("Smart Interbedding")
        self.smartInterbeddingCheckBox.setChecked(self.smart_interbedding)
        self.settings_file_buttons_layout.addWidget(self.smartInterbeddingCheckBox)

        # Add control for fallback classification
        self.fallbackClassificationCheckBox = QCheckBox("Enable Fallback Classification")
        self.fallbackClassificationCheckBox.setChecked(False)  # Default to False
        self.fallbackClassificationCheckBox.setToolTip("Apply fallback classification to reduce 'NL' (Not Logged) results")
        self.settings_file_buttons_layout.addWidget(self.fallbackClassificationCheckBox)

        # Add controls for smart interbedding parameters
        self.smartInterbeddingParamsLayout = QHBoxLayout()
        self.smartInterbeddingParamsLayout.addWidget(QLabel("Max Sequence Length:"))
        self.smartInterbeddingMaxSequenceSpinBox = QSpinBox()
        self.smartInterbeddingMaxSequenceSpinBox.setRange(5, 50)
        self.smartInterbeddingMaxSequenceSpinBox.setValue(self.smart_interbedding_max_sequence_length)
        self.smartInterbeddingParamsLayout.addWidget(self.smartInterbeddingMaxSequenceSpinBox)

        self.smartInterbeddingParamsLayout.addWidget(QLabel("Thick Unit Threshold (m):"))
        self.smartInterbeddingThickUnitSpinBox = QDoubleSpinBox()
        self.smartInterbeddingThickUnitSpinBox.setRange(0.1, 5.0)
        self.smartInterbeddingThickUnitSpinBox.setSingleStep(0.1)
        self.smartInterbeddingThickUnitSpinBox.setValue(self.smart_interbedding_thick_unit_threshold)
        self.smartInterbeddingParamsLayout.addWidget(self.smartInterbeddingThickUnitSpinBox)
        self.smartInterbeddingParamsLayout.addStretch()
        self.settings_layout.addLayout(self.smartInterbeddingParamsLayout)

        # Add analysis method selection
        analysis_method_layout = QHBoxLayout()
        analysis_method_label = QLabel("Analysis Method:")
        self.analysisMethodComboBox = QComboBox()
        self.analysisMethodComboBox.addItems(["Standard", "Simple"])
        # Set current method based on settings
        if hasattr(self, 'analysis_method') and self.analysis_method == "simple":
            self.analysisMethodComboBox.setCurrentText("Simple")
        else:
            self.analysisMethodComboBox.setCurrentText("Standard")
        analysis_method_layout.addWidget(analysis_method_label)
        analysis_method_layout.addWidget(self.analysisMethodComboBox)
        analysis_method_layout.addStretch()
        self.settings_file_buttons_layout.addLayout(analysis_method_layout)
        self.analysisMethodComboBox.currentTextChanged.connect(lambda: self.update_settings(auto_save=True))

        # Add new button for researched defaults
        self.researchedDefaultsButton = QPushButton("Researched Defaults")
        self.settings_file_buttons_layout.addWidget(self.researchedDefaultsButton)

        # Add lithology report export button
        self.exportLithologyReportButton = QPushButton("Export Lithology Report")
        self.settings_file_buttons_layout.addWidget(self.exportLithologyReportButton)

        self.settings_layout.addLayout(self.settings_file_buttons_layout)

        # Add range gap visualizer
        self.range_gap_controls_layout = QHBoxLayout()
        self.range_gap_controls_layout.addWidget(QLabel("Range Analysis:"))
        self.refreshRangeAnalysisButton = QPushButton("Refresh Ranges")
        self.refreshRangeAnalysisButton.clicked.connect(self.refresh_range_visualization)
        self.range_gap_controls_layout.addWidget(self.refreshRangeAnalysisButton)
        self.range_gap_controls_layout.addStretch()
        self.settings_layout.addLayout(self.range_gap_controls_layout)

        self.settings_layout.addWidget(self.range_visualizer)

        self.settings_layout.addStretch(1) # Add stretch to push controls to top

        # Initialize range visualization
        self.refresh_range_visualization()

        self.addRuleButton.clicked.connect(self.add_settings_rule)
        self.removeRuleButton.clicked.connect(self.remove_settings_rule)
        
        self.saveAsSettingsButton.clicked.connect(self.save_settings_as_file)
        self.updateSettingsButton.clicked.connect(self.update_settings)
        self.loadSettingsButton.clicked.connect(self.load_settings_from_file)
        self.researchedDefaultsButton.clicked.connect(self.open_researched_defaults_dialog) # Connect new button
        self.exportLithologyReportButton.clicked.connect(self.export_lithology_report) # Connect report button

        self.load_settings_rules_to_table()
        self.load_separator_settings()
        self.load_curve_thickness_settings() # Load new setting
        self.load_curve_inversion_settings()
        self._apply_researched_defaults_if_needed() # Call new method after loading settings
        # Connect separator controls to update_settings, not save_all_settings directly
        self.separatorThicknessSpinBox.valueChanged.connect(lambda: self.update_settings(auto_save=True))
        self.drawSeparatorsCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect curve thickness control to update_settings
        self.curveThicknessSpinBox.valueChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect curve inversion checkboxes to update_settings
        self.invertGammaCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        self.invertShortSpaceDensityCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        self.invertLongSpaceDensityCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect researched defaults checkbox to update_settings
        self.useResearchedDefaultsCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect merge thin units checkbox to update_settings
        self.mergeThinUnitsCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect smart interbedding checkbox to update_settings
        self.smartInterbeddingCheckBox.stateChanged.connect(lambda: self.update_settings(auto_save=True))
        # Connect smart interbedding parameter spinboxes to update_settings
        self.smartInterbeddingMaxSequenceSpinBox.valueChanged.connect(lambda: self.update_settings(auto_save=True))
        self.smartInterbeddingThickUnitSpinBox.valueChanged.connect(lambda: self.update_settings(auto_save=True))

    def load_separator_settings(self):
        self.separatorThicknessSpinBox.setValue(self.initial_separator_thickness)
        self.drawSeparatorsCheckBox.setChecked(self.initial_draw_separators)

    def load_curve_thickness_settings(self):
        self.curveThicknessSpinBox.setValue(self.initial_curve_thickness)

    def load_curve_inversion_settings(self):
        self.invertGammaCheckBox.setChecked(self.initial_curve_inversion_settings.get('gamma', False))
        self.invertShortSpaceDensityCheckBox.setChecked(self.initial_curve_inversion_settings.get('short_space_density', False))
        self.invertLongSpaceDensityCheckBox.setChecked(self.initial_curve_inversion_settings.get('long_space_density', False))

    def save_settings_as_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Settings As", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                # Ensure current UI settings are reflected in self.lithology_rules before saving
                self.save_settings_rules_from_table(show_message=False)
                current_separator_thickness = self.separatorThicknessSpinBox.value()
                current_draw_separators = self.drawSeparatorsCheckBox.isChecked()
                current_curve_thickness = self.curveThicknessSpinBox.value() # Get new setting
                current_curve_inversion_settings = {
                    'gamma': self.invertGammaCheckBox.isChecked(),
                    'short_space_density': self.invertShortSpaceDensityCheckBox.isChecked(),
                    'long_space_density': self.invertLongSpaceDensityCheckBox.isChecked()
                }
                
                # Get current value of researched defaults checkbox
                current_use_researched_defaults = self.useResearchedDefaultsCheckBox.isChecked()

                # Get current analysis method
                current_analysis_method = self.analysisMethodComboBox.currentText().lower()
                
                # Get current merge settings
                current_merge_thin_units = self.mergeThinUnitsCheckBox.isChecked()
                current_merge_threshold = self.merge_threshold  # Keep the loaded threshold

                # Get current smart interbedding settings
                current_smart_interbedding = self.smartInterbeddingCheckBox.isChecked()
                current_smart_interbedding_max_sequence = self.smartInterbeddingMaxSequenceSpinBox.value()
                current_smart_interbedding_thick_unit = self.smartInterbeddingThickUnitSpinBox.value()

                # Call save_settings with the chosen file path
                save_settings(self.lithology_rules, current_separator_thickness, current_draw_separators, current_curve_inversion_settings, current_curve_thickness, current_use_researched_defaults, current_analysis_method, current_merge_thin_units, current_merge_threshold, current_smart_interbedding, current_smart_interbedding_max_sequence, current_smart_interbedding_thick_unit, file_path)
                QMessageBox.information(self, "Settings Saved", f"Settings saved to {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def update_settings(self, auto_save=False):
        # This method will be called when any setting changes or when "Update Settings" is clicked
        # It gathers all current settings and saves them to the default settings file
        self.save_settings_rules_from_table(show_message=False) # Save rules first

        current_separator_thickness = self.separatorThicknessSpinBox.value()
        current_draw_separators = self.drawSeparatorsCheckBox.isChecked()
        current_curve_thickness = self.curveThicknessSpinBox.value() # Get new setting
        current_curve_inversion_settings = {
            'gamma': self.invertGammaCheckBox.isChecked(),
            'short_space_density': self.invertShortSpaceDensityCheckBox.isChecked(),
            'long_space_density': self.invertLongSpaceDensityCheckBox.isChecked()
        }
        
        current_use_researched_defaults = self.useResearchedDefaultsCheckBox.isChecked()
        current_analysis_method = self.analysisMethodComboBox.currentText().lower()
        current_merge_thin_units = self.mergeThinUnitsCheckBox.isChecked()
        current_merge_threshold = self.merge_threshold  # Keep the loaded threshold
        current_smart_interbedding = self.smartInterbeddingCheckBox.isChecked()
        current_smart_interbedding_max_sequence = self.smartInterbeddingMaxSequenceSpinBox.value()
        current_smart_interbedding_thick_unit = self.smartInterbeddingThickUnitSpinBox.value()
        save_settings(self.lithology_rules, current_separator_thickness, current_draw_separators, current_curve_inversion_settings, current_curve_thickness, current_use_researched_defaults, current_analysis_method, current_merge_thin_units, current_merge_threshold, current_smart_interbedding, current_smart_interbedding_max_sequence, current_smart_interbedding_thick_unit)

        # Update instance variables to ensure smart interbedding uses current values
        self.smart_interbedding = current_smart_interbedding
        self.smart_interbedding_max_sequence_length = current_smart_interbedding_max_sequence
        self.smart_interbedding_thick_unit_threshold = current_smart_interbedding_thick_unit

        if not auto_save: # Only show message if triggered by the "Update Settings" button
            QMessageBox.information(self, "Settings Updated", "All settings have been updated and saved.")

            # Reload settings to ensure UI reflects saved state (only for manual updates)
            app_settings = load_settings()
            self.lithology_rules = app_settings["lithology_rules"]
            self.initial_separator_thickness = app_settings["separator_thickness"]
            self.initial_draw_separators = app_settings["draw_separator_lines"]
            self.initial_curve_inversion_settings = app_settings["curve_inversion_settings"]
            self.initial_curve_thickness = app_settings["curve_thickness"] # Reload new setting
            self.use_researched_defaults = app_settings["use_researched_defaults"]
            self.useResearchedDefaultsCheckBox.setChecked(self.use_researched_defaults)
            self.analysis_method = app_settings.get("analysis_method", "standard")
            if hasattr(self, 'analysisMethodComboBox'):
                if self.analysis_method == "simple":
                    self.analysisMethodComboBox.setCurrentText("Simple")
                else:
                    self.analysisMethodComboBox.setCurrentText("Standard")
            self.load_settings_rules_to_table()
            self.load_separator_settings()
            self.load_curve_thickness_settings() # Reload new setting
            self.load_curve_inversion_settings()
            # Update smart interbedding UI elements to reflect reloaded settings
            self.smartInterbeddingCheckBox.setChecked(self.smart_interbedding)
            self.smartInterbeddingMaxSequenceSpinBox.setValue(self.smart_interbedding_max_sequence_length)
            self.smartInterbeddingThickUnitSpinBox.setValue(self.smart_interbedding_thick_unit_threshold)


    def load_settings_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Settings", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                loaded_settings = load_settings(file_path) # Pass file_path to load_settings
                self.lithology_rules = loaded_settings["lithology_rules"]
                self.initial_separator_thickness = loaded_settings["separator_thickness"]
                self.initial_draw_separators = loaded_settings["draw_separator_lines"]
                self.initial_curve_inversion_settings = loaded_settings["curve_inversion_settings"] # Load new setting
                self.initial_curve_thickness = loaded_settings["curve_thickness"] # Load new setting
                self.use_researched_defaults = loaded_settings["use_researched_defaults"]
                self.useResearchedDefaultsCheckBox.setChecked(self.use_researched_defaults)

                self.load_settings_rules_to_table()
                self.load_separator_settings()
                self.load_curve_thickness_settings() # Reload new setting
                self.load_curve_inversion_settings() # Load new setting
                self._apply_researched_defaults_if_needed() # Call new method after loading settings
                QMessageBox.information(self, "Settings Loaded", f"Settings loaded from {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load settings: {e}")

    def closeEvent(self, event):
        # Save window geometry and settings automatically when the application closes
        self.save_window_geometry()
        self.update_settings(auto_save=True)
        super().closeEvent(event)

    def save_window_geometry(self):
        """Save current window size and position to settings."""
        try:
            from PyQt6.QtCore import QRect
        except ImportError:
            from PyQt5.QtCore import QRect

        # Get current window geometry
        geometry = self.geometry()
        is_maximized = self.isMaximized()

        # Prepare geometry data
        geometry_data = {
            'x': geometry.x(),
            'y': geometry.y(),
            'width': geometry.width(),
            'height': geometry.height(),
            'maximized': is_maximized
        }

        # Load current settings and add geometry
        try:
            app_settings = load_settings()
            app_settings['window_geometry'] = geometry_data

            # Save updated settings
            from ..core.settings_manager import DEFAULT_SETTINGS_FILE
            import json
            os.makedirs(os.path.dirname(DEFAULT_SETTINGS_FILE), exist_ok=True)
            with open(DEFAULT_SETTINGS_FILE, 'w') as f:
                json.dump(app_settings, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save window geometry: {e}")

    def on_tab_changed(self, index):
        # Remove redundant save when switching tabs
        # if self.tab_widget.tabText(index) != "Settings":
        #     self.save_settings_rules_from_table()
        pass # No automatic saving on tab change anymore

    def load_settings_rules_to_table(self):
        self.settings_rules_table.setRowCount(len(self.lithology_rules))
        for row_idx, rule in enumerate(self.lithology_rules):
            # Column 0: Name (QComboBox)
            litho_desc_combo = QComboBox()
            litho_desc_combo.addItems(self.coallog_data['Litho_Type']['Description'].tolist())
            if rule.get('name', '') in self.coallog_data['Litho_Type']['Description'].tolist():
                litho_desc_combo.setCurrentText(rule.get('name', ''))
            self.settings_rules_table.setCellWidget(row_idx, 0, litho_desc_combo)
            litho_desc_combo.currentTextChanged.connect(self.update_litho_code)
            litho_desc_combo.currentTextChanged.connect(lambda _, r=row_idx: self.update_rule_preview(r))
            litho_desc_combo.currentTextChanged.connect(lambda text, r=row_idx: self.update_qualifier_dropdown(r, text))

            # Column 1: Code (read-only QLabel)
            self.settings_rules_table.setItem(row_idx, 1, QTableWidgetItem(str(rule.get('code', ''))))
            self.settings_rules_table.item(row_idx, 1).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            # Column 2: Qualifier (QComboBox)
            qual_combo = QComboBox()
            self.settings_rules_table.setCellWidget(row_idx, 2, qual_combo)

            # Column 3: Gamma Range (CompactRangeWidget)
            gamma_widget = CompactRangeWidget()
            gamma_widget.set_values(rule.get('gamma_min', 0.0), rule.get('gamma_max', 0.0))
            gamma_widget.valuesChanged.connect(lambda min_val, max_val, r=row_idx: self.update_range_values(r, 'gamma', min_val, max_val))
            self.settings_rules_table.setCellWidget(row_idx, 3, gamma_widget)

            # Column 4: Density Range (CompactRangeWidget)
            density_widget = CompactRangeWidget()
            density_widget.set_values(rule.get('density_min', 0.0), rule.get('density_max', 0.0))
            density_widget.valuesChanged.connect(lambda min_val, max_val, r=row_idx: self.update_range_values(r, 'density', min_val, max_val))
            self.settings_rules_table.setCellWidget(row_idx, 4, density_widget)

            # Column 5: Visual Props (MultiAttributeWidget)
            visual_widget = MultiAttributeWidget(coallog_data=self.coallog_data)
            visual_widget.set_properties({
                'shade': rule.get('shade', ''),
                'hue': rule.get('hue', ''),
                'colour': rule.get('colour', ''),
                'weathering': rule.get('weathering', ''),
                'strength': rule.get('strength', '')
            })
            visual_widget.propertiesChanged.connect(lambda props, r=row_idx: self.update_visual_properties(r, props))
            self.settings_rules_table.setCellWidget(row_idx, 5, visual_widget)

            # Column 6: Background (QPushButton for color picker)
            color_button = QPushButton()
            color_hex = rule.get('background_color', '#FFFFFF')
            color_button.setStyleSheet(f"background-color: {color_hex}")
            color_button.clicked.connect(lambda _, r=row_idx: self.open_color_picker(r))
            self.settings_rules_table.setCellWidget(row_idx, 6, color_button)

            # Column 7: Preview (EnhancedPatternPreview)
            preview_widget = EnhancedPatternPreview()
            self.settings_rules_table.setCellWidget(row_idx, 7, preview_widget)
            self.update_rule_preview(row_idx)

            # Column 8: Actions (QWidget with buttons)
            actions_widget = self.create_actions_widget(row_idx)
            self.settings_rules_table.setCellWidget(row_idx, 8, actions_widget)

            # Dynamically populate qualifiers and set the saved value
            self.update_qualifier_dropdown(row_idx, litho_desc_combo.currentText())
            saved_qualifier = rule.get('qualifier', '')
            # Find the index of the saved qualifier code and set it
            index = qual_combo.findData(saved_qualifier, Qt.ItemDataRole.UserRole)
            if index != -1:
                qual_combo.setCurrentIndex(index)
            else:
                qual_combo.setCurrentIndex(0) # Select the blank item if not found

    def save_settings_rules_from_table(self, show_message=True):
        rules = []
        for row_idx in range(self.settings_rules_table.rowCount()):
            rule = {}

            # Column 0: Name (QComboBox)
            rule['name'] = self.settings_rules_table.cellWidget(row_idx, 0).currentText()

            # Column 1: Code (read-only item)
            rule['code'] = self.settings_rules_table.item(row_idx, 1).text() if self.settings_rules_table.item(row_idx, 1) else ''

            # Column 2: Qualifier (QComboBox)
            rule['qualifier'] = self.settings_rules_table.cellWidget(row_idx, 2).currentData(Qt.ItemDataRole.UserRole)

            # Column 3: Gamma Range (CompactRangeWidget)
            gamma_widget = self.settings_rules_table.cellWidget(row_idx, 3)
            if isinstance(gamma_widget, CompactRangeWidget):
                gamma_min, gamma_max = gamma_widget.get_values()
                rule['gamma_min'] = gamma_min
                rule['gamma_max'] = gamma_max
            else:
                rule['gamma_min'] = INVALID_DATA_VALUE
                rule['gamma_max'] = INVALID_DATA_VALUE

            # Column 4: Density Range (CompactRangeWidget)
            density_widget = self.settings_rules_table.cellWidget(row_idx, 4)
            if isinstance(density_widget, CompactRangeWidget):
                density_min, density_max = density_widget.get_values()
                rule['density_min'] = density_min
                rule['density_max'] = density_max
            else:
                rule['density_min'] = INVALID_DATA_VALUE
                rule['density_max'] = INVALID_DATA_VALUE

            # Column 5: Visual Props (MultiAttributeWidget)
            visual_widget = self.settings_rules_table.cellWidget(row_idx, 5)
            if isinstance(visual_widget, MultiAttributeWidget):
                visual_props = visual_widget.get_properties()
                rule.update(visual_props)
            else:
                # Fallback to empty strings if widget not available
                rule['shade'] = ''
                rule['hue'] = ''
                rule['colour'] = ''
                rule['weathering'] = ''
                rule['strength'] = ''

            # Column 6: Background (QPushButton)
            color_button = self.settings_rules_table.cellWidget(row_idx, 6)
            if color_button:
                try:
                    rule['background_color'] = QColor(color_button.styleSheet().split(':')[-1].strip()).name()
                except:
                    rule['background_color'] = '#FFFFFF'
            else:
                rule['background_color'] = '#FFFFFF'

            # Find and store the absolute path to the SVG file directly in the rule, using qualifier
            rule['svg_path'] = self.find_svg_file(rule['code'], rule['qualifier'])

            rules.append(rule)
        self.lithology_rules = rules
        # Only show message if explicitly called, not on every tab change or auto-save
        if show_message:
            QMessageBox.information(self, "Settings Saved", "Lithology rules updated.")

    def create_actions_widget(self, row):
        """Create a widget with edit/delete buttons for the Actions column."""
        try:
            from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
        except ImportError:
            from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton

        actions_widget = QWidget()
        layout = QHBoxLayout(actions_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Edit button (could be used for advanced editing)
        edit_button = QPushButton("✏")
        edit_button.setFixedSize(20, 20)
        edit_button.setToolTip("Edit rule details")
        edit_button.clicked.connect(lambda: self.edit_rule(row))
        layout.addWidget(edit_button)

        # Delete button
        delete_button = QPushButton("🗑")
        delete_button.setFixedSize(20, 20)
        delete_button.setToolTip("Delete this rule")
        delete_button.clicked.connect(lambda: self.remove_settings_rule())
        layout.addWidget(delete_button)

        # Status indicator (could show validation status)
        status_label = QLabel("✓")
        status_label.setFixedSize(20, 20)
        status_label.setStyleSheet("color: green; font-weight: bold;")
        status_label.setToolTip("Rule is valid")
        layout.addWidget(status_label)

        return actions_widget

    def update_range_values(self, row, range_type, min_val, max_val):
        """Update range values from CompactRangeWidget signals and trigger visualization refresh."""
        # This method handles the signals from CompactRangeWidget
        # The actual value extraction happens in save_settings_rules_from_table

        # Trigger real-time gap visualization update with debouncing
        self._schedule_gap_visualization_update()

    def update_visual_properties(self, row, properties):
        """Update visual properties from MultiAttributeWidget signals."""
        # This method handles the signals from MultiAttributeWidget
        # The actual value extraction happens in save_settings_rules_from_table
        pass  # Values will be retrieved when saving

    def edit_rule(self, row):
        """Handle advanced editing of a rule (placeholder for future expansion)."""
        # Could open a comprehensive rule editor dialog
        QMessageBox.information(self, "Edit Rule", f"Advanced editing for rule {row + 1} (feature coming soon)")

    def add_dropdown_to_table(self, row, col, items, current_text=''):
        combo = QComboBox()
        combo.addItems(items)
        if current_text in items:
            combo.setCurrentText(current_text)
        self.settings_rules_table.setCellWidget(row, col, combo)

    def add_settings_rule(self):
        row_position = self.settings_rules_table.rowCount()
        self.settings_rules_table.insertRow(row_position)

        # Column 0: Name (QComboBox)
        litho_desc_combo = QComboBox()
        litho_desc_combo.addItems(self.coallog_data['Litho_Type']['Description'].tolist())
        self.settings_rules_table.setCellWidget(row_position, 0, litho_desc_combo)
        litho_desc_combo.currentTextChanged.connect(self.update_litho_code)
        litho_desc_combo.currentTextChanged.connect(lambda _, r=row_position: self.update_rule_preview(r))
        litho_desc_combo.currentTextChanged.connect(lambda text, r=row_position: self.update_qualifier_dropdown(r, text))

        # Column 1: Code (read-only)
        self.settings_rules_table.setItem(row_position, 1, QTableWidgetItem(""))
        self.settings_rules_table.item(row_position, 1).setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

        # Column 2: Qualifier (QComboBox)
        qual_combo = QComboBox()
        self.settings_rules_table.setCellWidget(row_position, 2, qual_combo)

        # Column 3: Gamma Range (CompactRangeWidget)
        gamma_widget = CompactRangeWidget()
        gamma_widget.set_values(0.0, 0.0)
        gamma_widget.valuesChanged.connect(lambda min_val, max_val, r=row_position: self.update_range_values(r, 'gamma', min_val, max_val))
        self.settings_rules_table.setCellWidget(row_position, 3, gamma_widget)

        # Column 4: Density Range (CompactRangeWidget)
        density_widget = CompactRangeWidget()
        density_widget.set_values(0.0, 0.0)
        density_widget.valuesChanged.connect(lambda min_val, max_val, r=row_position: self.update_range_values(r, 'density', min_val, max_val))
        self.settings_rules_table.setCellWidget(row_position, 4, density_widget)

        # Column 5: Visual Props (MultiAttributeWidget)
        visual_widget = MultiAttributeWidget(coallog_data=self.coallog_data)
        visual_widget.set_properties({
            'shade': '',
            'hue': '',
            'colour': '',
            'weathering': '',
            'strength': ''
        })
        visual_widget.propertiesChanged.connect(lambda props, r=row_position: self.update_visual_properties(r, props))
        self.settings_rules_table.setCellWidget(row_position, 5, visual_widget)

        # Column 6: Background (QPushButton)
        color_button = QPushButton()
        color_button.setStyleSheet("background-color: #FFFFFF")
        color_button.clicked.connect(lambda _, r=row_position: self.open_color_picker(r))
        self.settings_rules_table.setCellWidget(row_position, 6, color_button)

        # Column 7: Preview (EnhancedPatternPreview)
        preview_widget = EnhancedPatternPreview()
        self.settings_rules_table.setCellWidget(row_position, 7, preview_widget)

        # Column 8: Actions (QWidget with buttons)
        actions_widget = self.create_actions_widget(row_position)
        self.settings_rules_table.setCellWidget(row_position, 8, actions_widget)

    def update_litho_code(self, text):
        sender = self.sender()
        if sender:
            row = self.settings_rules_table.indexAt(sender.pos()).row()
            litho_code = self.coallog_data['Litho_Type'].loc[self.coallog_data['Litho_Type']['Description'] == text, 'Code'].iloc[0]
            self.settings_rules_table.setItem(row, 1, QTableWidgetItem(litho_code))

    def update_qualifier_dropdown(self, row, selected_litho_name):
        # Find the corresponding litho code
        litho_code = None
        litho_type_df = self.coallog_data.get('Litho_Type')
        if litho_type_df is not None:
            match = litho_type_df[litho_type_df['Description'] == selected_litho_name]
            if not match.empty:
                litho_code = match['Code'].iloc[0]

        qual_combo = self.settings_rules_table.cellWidget(row, 2)
        if not isinstance(qual_combo, QComboBox):
            return

        current_qualifier_code = qual_combo.currentData(Qt.ItemDataRole.UserRole) # Get the currently selected code
        qual_combo.clear()

        qual_combo.addItem("", "") # Add a blank option with empty code
        
        if litho_code:
            litho_info = self.lithology_qualifier_map.get(litho_code, {})
            qualifiers = litho_info.get('qualifiers', {})
            if qualifiers:
                # Qualifiers are a dict of {code: description}
                for code, description in qualifiers.items():
                    qual_combo.addItem(description, code) # Display description, store code as UserRole data
        
        # Try to restore the previous selection by code
        index = qual_combo.findData(current_qualifier_code, Qt.ItemDataRole.UserRole)
        if index != -1:
            qual_combo.setCurrentIndex(index)
        else:
            qual_combo.setCurrentIndex(0) # Select the blank item if not found

    def remove_settings_rule(self):
        current_row = self.settings_rules_table.currentRow()
        if current_row >= 0:
            self.settings_rules_table.removeRow(current_row)
        self.save_settings_rules_from_table()

    def open_color_picker(self, row):
        # Column 6: Background color button
        button = self.settings_rules_table.cellWidget(row, 6)
        initial_color = QColor(button.styleSheet().split(':')[-1].strip())
        color = QColorDialog.getColor(initial_color, self)
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}")
            self.update_rule_preview(row)

    def update_rule_preview(self, row):
        litho_code_item = self.settings_rules_table.item(row, 1)
        if not litho_code_item:
            return
        litho_code = litho_code_item.text()

        qual_combo = self.settings_rules_table.cellWidget(row, 2)
        litho_qualifier = qual_combo.currentData(Qt.ItemDataRole.UserRole) if isinstance(qual_combo, QComboBox) else ''

        svg_file = self.find_svg_file(litho_code, litho_qualifier)
        # Column 6: Background color button
        color_button = self.settings_rules_table.cellWidget(row, 6)
        color = QColor(color_button.styleSheet().split(':')[-1].strip()) if color_button else QColor('#FFFFFF')
        # Column 7: Preview widget
        preview_widget = self.settings_rules_table.cellWidget(row, 7)
        if preview_widget and hasattr(preview_widget, 'update_preview'):
            preview_widget.update_preview(svg_path=svg_file, background_color=color.name())

    def setup_editor_tab(self):
        self.editor_tab_layout = QVBoxLayout(self.editor_tab)

        # 1. Create the Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 2. Left Container (LAS/Gamma Ray Curves)
        curves_container = QWidget()
        curves_layout = QVBoxLayout(curves_container)
        curves_layout.setContentsMargins(0, 0, 0, 0)
        curves_layout.addWidget(self.curvePlotter)

        # 3. Middle Container (Stratigraphic Column)
        strat_container = QWidget()
        strat_layout = QVBoxLayout(strat_container)
        strat_layout.setContentsMargins(0, 0, 0, 0)
        strat_layout.addWidget(self.stratigraphicColumnView)

        # 4. Right Container (Editor Table + Export)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        # Add Create Interbedding button
        button_layout = QHBoxLayout()
        self.createInterbeddingButton = QPushButton("Create Interbedding")
        self.createInterbeddingButton.clicked.connect(self.create_manual_interbedding)
        button_layout.addWidget(self.createInterbeddingButton)
        button_layout.addWidget(self.exportCsvButton)
        button_layout.addStretch()

        table_layout.addWidget(self.editorTable)
        table_layout.addLayout(button_layout)

        # 5. Add to Splitter & Set defaults (3 adjacent panels)
        self.main_splitter.addWidget(curves_container)
        self.main_splitter.addWidget(strat_container)
        self.main_splitter.addWidget(table_container)
        self.main_splitter.setStretchFactor(0, 1) # Curves area
        self.main_splitter.setStretchFactor(1, 1) # Strat column area
        self.main_splitter.setStretchFactor(2, 1) # Table area

        # 6. Create a container for the main content and zoom controls
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(5)

        # Add Splitter to the content layout
        main_content_layout.addWidget(self.main_splitter)

        # 7. Zoom Controls (affects both curve and strat views)
        zoom_controls_layout = QHBoxLayout()

        zoom_label = QLabel("Zoom:")
        zoom_controls_layout.addWidget(zoom_label)

        self.zoomSlider = QSlider(Qt.Orientation.Horizontal)
        self.zoomSlider.setMinimum(50)  # 50% zoom
        self.zoomSlider.setMaximum(500)  # 500% zoom
        self.zoomSlider.setValue(100)  # Default 100% zoom
        self.zoomSlider.setSingleStep(10)
        self.zoomSlider.setPageStep(50)
        zoom_controls_layout.addWidget(self.zoomSlider)

        self.zoomSpinBox = QDoubleSpinBox()
        self.zoomSpinBox.setRange(50.0, 500.0)
        self.zoomSpinBox.setValue(100.0)
        self.zoomSpinBox.setSingleStep(10.0)
        self.zoomSpinBox.setSuffix("%")
        zoom_controls_layout.addWidget(self.zoomSpinBox)

        zoom_controls_layout.addStretch()  # Push controls to the left

        # Add zoom controls to content layout with fixed height
        zoom_container = QWidget()
        zoom_container.setLayout(zoom_controls_layout)
        zoom_container.setFixedHeight(40)  # Fixed height for zoom controls
        main_content_layout.addWidget(zoom_container)

        # Add the main content widget to the editor tab layout
        self.editor_tab_layout.addWidget(main_content_widget)

        # Connect zoom controls to synchronize between curve and strat views
        self.zoomSlider.valueChanged.connect(self.on_zoom_changed)
        self.zoomSpinBox.valueChanged.connect(self.on_zoom_changed)

        # Initialize empty table
        self.editorTable.setRowCount(0)
        self.editorTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def on_zoom_changed(self):
        """Handle zoom control changes and apply synchronized zoom to both views."""
        # Get zoom value from the sender to avoid recursive calls
        sender = self.sender()
        if sender == self.zoomSlider:
            zoom_percentage = self.zoomSlider.value()
            self.zoomSpinBox.blockSignals(True)  # Prevent recursive call
            self.zoomSpinBox.setValue(zoom_percentage)
            self.zoomSpinBox.blockSignals(False)
        else:
            zoom_percentage = self.zoomSpinBox.value()
            self.zoomSlider.blockSignals(True)  # Prevent recursive call
            self.zoomSlider.setValue(int(zoom_percentage))
            self.zoomSlider.blockSignals(False)

        # Apply zoom to both views
        zoom_factor = zoom_percentage / 100.0  # Convert percentage to factor (1.0 = 100%)
        self.apply_synchronized_zoom(zoom_factor)

    def apply_synchronized_zoom(self, zoom_factor):
        """Apply the same zoom factor to both curve plotter and stratigraphic column."""
        self.curvePlotter.set_zoom_level(zoom_factor)
        self.stratigraphicColumnView.set_zoom_level(zoom_factor)

    def populate_editor_table(self, dataframe):
        self.editorTable.clear()
        if dataframe.empty:
            self.editorTable.setRowCount(0)
            self.editorTable.setColumnCount(0)
            return
        self.editorTable.setRowCount(dataframe.shape[0])
        self.editorTable.setColumnCount(dataframe.shape[1])
        self.editorTable.setHorizontalHeaderLabels(dataframe.columns.tolist())
        for i in range(dataframe.shape[0]):
            for j in range(dataframe.shape[1]):
                item = QTableWidgetItem(str(dataframe.iloc[i, j]))
                self.editorTable.setItem(i, j, item)

    def export_editor_data_to_csv(self):
        if self.editorTable.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "No data to export in the editor tab.")
            return
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            try:
                column_headers = [self.editorTable.horizontalHeaderItem(i).text() for i in range(self.editorTable.columnCount())]
                data = []
                for row in range(self.editorTable.rowCount()):
                    row_data = []
                    for col in range(self.editorTable.columnCount()):
                        item = self.editorTable.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                df_to_export = pd.DataFrame(data, columns=column_headers)
                df_to_export.to_csv(file_path, index=False)
                QMessageBox.information(self, "Export Successful", f"Data exported to {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export data: {e}")

    def run_analysis(self):
        if not self.las_file_path:
            QMessageBox.warning(self, "No LAS File", "Please load an LAS file first.")
            return
        if not self.lithology_rules:
            QMessageBox.warning(self, "No Lithology Rules", "Please define lithology rules in settings first.")
            return
        # Short Space Density selection maps to both density fields
        density_selection = self.shortSpaceDensityComboBox.currentText()
        # Keep hidden combo box synchronized for backward compatibility
        self.densityComboBox.setCurrentText(density_selection)

        mnemonic_map = {
            'gamma': self.gammaRayComboBox.currentText(),
            'density': density_selection,  # Use Short Space Density selection
            'short_space_density': density_selection,  # Same as density
            'long_space_density': self.longSpaceDensityComboBox.currentText()
        }
        if not mnemonic_map['gamma'] or not mnemonic_map['density']:
            QMessageBox.warning(self, "Missing Curve Mapping", "Please select both Gamma Ray and Density curves.")
            return
        # Ensure lithology rules are up-to-date from the settings table before running analysis
        self.save_settings_rules_from_table(show_message=False)

        self.thread = QThread()
        # Pass mnemonic_map to the Worker
        use_fallback_classification = self.fallbackClassificationCheckBox.isChecked()
        self.worker = Worker(self.las_file_path, mnemonic_map, self.lithology_rules, self.use_researched_defaults, self.merge_thin_units, self.merge_threshold, self.smart_interbedding, self.smart_interbedding_max_sequence_length, self.smart_interbedding_thick_unit_threshold, use_fallback_classification)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.runAnalysisButton.setEnabled(False)
        QMessageBox.information(self, "Analysis Started", "Running analysis in background...")
        self.thread.start()

    def analysis_finished(self, units_dataframe, classified_dataframe):
        self.runAnalysisButton.setEnabled(True)

        # Store recent analysis results for reporting
        self.last_classified_dataframe = classified_dataframe.copy()
        self.last_units_dataframe = units_dataframe.copy()
        self.last_analysis_file = self.las_file_path
        self.last_analysis_timestamp = pd.Timestamp.now()

        # Check for smart interbedding suggestions if enabled
        print(f"DEBUG: Smart interbedding enabled check: {self.smart_interbedding}")
        if self.smart_interbedding:
            self._check_smart_interbedding_suggestions(units_dataframe, classified_dataframe)
        else:
            self._finalize_analysis_display(units_dataframe, classified_dataframe)

    def analysis_error(self, message):
        self.runAnalysisButton.setEnabled(True)
        QMessageBox.critical(self, "Analysis Error", message)

    def _apply_researched_defaults_if_needed(self):
        """
        Checks lithology rules for zero/blank gamma/density ranges and prompts the user
        to apply researched defaults if available. Updates self.lithology_rules and
        refreshes the settings table.
        Respects the use_researched_defaults setting.
        """
        if not self.use_researched_defaults:
            return  # Skip applying defaults if user has disabled this feature

        from ..core.config import RESEARCHED_LITHOLOGY_DEFAULTS

        rules_updated = False
        for rule_idx, rule in enumerate(self.lithology_rules):
            code = rule.get('code')

            # Check if this lithology code has researched defaults
            if code in RESEARCHED_LITHOLOGY_DEFAULTS:
                researched_defaults = RESEARCHED_LITHOLOGY_DEFAULTS[code]

                # Check gamma ranges - zeros or missing
                gamma_missing = (rule.get('gamma_min', INVALID_DATA_VALUE) == INVALID_DATA_VALUE and
                                rule.get('gamma_max', INVALID_DATA_VALUE) == INVALID_DATA_VALUE) or \
                               (rule.get('gamma_min', 0.0) == 0.0 and rule.get('gamma_max', 0.0) == 0.0)

                # Check density ranges - zeros or missing
                density_missing = (rule.get('density_min', INVALID_DATA_VALUE) == INVALID_DATA_VALUE and
                                  rule.get('density_max', INVALID_DATA_VALUE) == INVALID_DATA_VALUE) or \
                                 (rule.get('density_min', 0.0) == 0.0 and rule.get('density_max', 0.0) == 0.0)

                # Determine if we need to prompt user
                gamma_prompt = gamma_missing and 'gamma_min' in researched_defaults and 'gamma_max' in researched_defaults
                density_prompt = density_missing and 'density_min' in researched_defaults and 'density_max' in researched_defaults

                if gamma_prompt or density_prompt:
                    # Build prompt message
                    prompt_text = f"The ranges for '{rule.get('name', code)}' are currently zero/blank.\n"
                    prompt_text += "Would you like to apply researched default ranges?\n\n"

                    if gamma_prompt:
                        prompt_text += f"Gamma: {researched_defaults.get('gamma_min', 'N/A')} - {researched_defaults.get('gamma_max', 'N/A')}\n"
                    if density_prompt:
                        prompt_text += f"Density: {researched_defaults.get('density_min', 'N/A')} - {researched_defaults.get('density_max', 'N/A')}\n"

                    reply = QMessageBox.question(self, "Apply Researched Defaults", prompt_text,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                    if reply == QMessageBox.StandardButton.Yes:
                        if gamma_missing and gamma_prompt:
                            rule['gamma_min'] = researched_defaults['gamma_min']
                            rule['gamma_max'] = researched_defaults['gamma_max']
                        if density_missing and density_prompt:
                            rule['density_min'] = researched_defaults['density_min']
                            rule['density_max'] = researched_defaults['density_max']
                        rules_updated = True

        if rules_updated:
            self.load_settings_rules_to_table() # Refresh the table to show updated values
            self.update_settings(auto_save=True) # Save the updated settings to file
            QMessageBox.information(self, "Defaults Applied", "Researched default ranges have been applied and saved.")

    def open_researched_defaults_dialog(self):
        """Opens a dialog to display researched default lithology ranges."""
        dialog = ResearchedDefaultsDialog(self)
        dialog.exec()

    def refresh_range_visualization(self):
        """Refresh the range gap visualization with current lithology rules"""
        # Get current rules from the table
        current_rules = []
        for row_idx in range(self.settings_rules_table.rowCount()):
            rule = {}
            rule['name'] = self.settings_rules_table.cellWidget(row_idx, 0).currentText()
            rule['code'] = self.settings_rules_table.item(row_idx, 1).text() if self.settings_rules_table.item(row_idx, 1) else ''

            # Get gamma range from CompactRangeWidget (column 3)
            gamma_widget = self.settings_rules_table.cellWidget(row_idx, 3)
            if isinstance(gamma_widget, CompactRangeWidget):
                rule['gamma_min'], rule['gamma_max'] = gamma_widget.get_values()
            else:
                rule['gamma_min'], rule['gamma_max'] = 0.0, 0.0

            # Get density range from CompactRangeWidget (column 4)
            density_widget = self.settings_rules_table.cellWidget(row_idx, 4)
            if isinstance(density_widget, CompactRangeWidget):
                rule['density_min'], rule['density_max'] = density_widget.get_values()
            else:
                rule['density_min'], rule['density_max'] = 0.0, 0.0

            # Get background color for visualization (column 6)
            color_button = self.settings_rules_table.cellWidget(row_idx, 6)
            if color_button:
                rule['background_color'] = QColor(color_button.styleSheet().split(':')[-1].strip()).name()
            else:
                rule['background_color'] = '#FFFFFF'

            current_rules.append(rule)

        # Analyze ranges and update visualization with overlapping support
        gamma_covered, gamma_gaps = self.range_analyzer.analyze_gamma_ranges_with_overlaps(current_rules)
        density_covered, density_gaps = self.range_analyzer.analyze_density_ranges_with_overlaps(current_rules)

        self.range_visualizer.update_ranges(gamma_covered, gamma_gaps, density_covered, density_gaps, use_overlaps=True, lithology_rules=current_rules)

    def export_lithology_report(self):
        """Export a comprehensive lithology report with density statistics."""
        # Check if we have recent analysis data
        if self.last_classified_dataframe is None:
            QMessageBox.warning(self, "No Recent Analysis", "No recent analysis data available. Please run an analysis first.")
            return

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Export Lithology Report", "", "CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return

        try:
            # Get current lithology rules from the table
            self.save_settings_rules_from_table(show_message=False)  # Ensure rules are current

            # Filter out NL from rules for reporting
            rules = [rule for rule in self.lithology_rules if rule.get('code', '').upper() != 'NL']

            # DataFrames for analysis
            classified_df = self.last_classified_dataframe.copy()
            units_df = self.last_units_dataframe.copy() if self.last_units_dataframe is not None else None

            # Calculate total rows for percentage calculations
            total_rows = len(classified_df)

            # Prepare report data
            report_data = []

            for rule in rules:
                rule_code = rule.get('code', '')
                rule_name = rule.get('name', '')
                rule_qualifier = rule.get('qualifier', '')

                # Use units dataframe to get more complete data if available
                classification_count = 0
                if units_df is not None and not units_df.empty:
                    # Filter units by both code and qualifier for unique combinations
                    mask = (units_df['LITHOLOGY_CODE'] == rule_code)
                    if rule_qualifier and 'lithology_qualifier' in units_df.columns:
                        mask = mask & (units_df['lithology_qualifier'] == rule_qualifier)

                    matching_units = units_df[mask]
                    if not matching_units.empty:
                        # Calculate total thickness for this rule combination
                        thickness_col = 'thickness' if 'thickness' in matching_units.columns else None
                        classification_count = matching_units.shape[0]  # Count of units, not rows
                    else:
                        # Fallback: check classified dataframe
                        classified_mask = (classified_df['LITHOLOGY_CODE'] == rule_code)
                        classification_count = classified_mask.sum()
                else:
                    # Fallback: use classified dataframe only
                    classified_mask = (classified_df['LITHOLOGY_CODE'] == rule_code)
                    classification_count = classified_mask.sum()

                classification_percentage = (classification_count / total_rows * 100) if total_rows > 0 else 0

                # Get density statistics by filtering classified dataframe
                density_stats = {}
                if 'short_space_density' in classified_df.columns:
                    # Filter rows that match this rule's classification
                    density_mask = (classified_df['LITHOLOGY_CODE'] == rule_code)
                    # Note: We can't easily filter by qualifier in classified dataframe since qualifier column doesn't exist there

                    densities = classified_df.loc[density_mask, 'short_space_density'].dropna()
                    if len(densities) > 0:
                        density_stats['associated_ssd_min'] = densities.min()
                        density_stats['associated_ssd_max'] = densities.max()
                        density_stats['associated_ssd_mean'] = densities.mean()
                        density_stats['associated_ssd_median'] = densities.median()
                    else:
                        density_stats['associated_ssd_min'] = None
                        density_stats['associated_ssd_max'] = None
                        density_stats['associated_ssd_mean'] = None
                        density_stats['associated_ssd_median'] = None

                # Build report row
                row = {
                    'lithology_name': rule_name,
                    'lithology_code': rule_code,
                    'lithology_qualifier': rule_qualifier if rule_qualifier else '',
                    'gamma_min': rule.get('gamma_min', None),
                    'gamma_max': rule.get('gamma_max', None),
                    'density_min': rule.get('density_min', None),
                    'density_max': rule.get('density_max', None),
                    'classification_count': classification_count,
                    'classification_percentage': round(classification_percentage, 2),
                    'associated_ssd_min': density_stats.get('associated_ssd_min'),
                    'associated_ssd_max': density_stats.get('associated_ssd_max'),
                    'associated_ssd_mean': round(density_stats.get('associated_ssd_mean'), 4) if density_stats.get('associated_ssd_mean') is not None else None,
                    'associated_ssd_median': round(density_stats.get('associated_ssd_median'), 4) if density_stats.get('associated_ssd_median') is not None else None,
                }

                report_data.append(row)

            # Enhanced NL Analysis Section
            nl_count = (classified_df['LITHOLOGY_CODE'] == 'NL').sum()
            nl_percentage = (nl_count / total_rows * 100) if total_rows > 0 else 0

            if nl_count > 0:
                # Calculate density stats for NL classifications
                nl_densities = classified_df.loc[classified_df['LITHOLOGY_CODE'] == 'NL', 'short_space_density'].dropna() if 'short_space_density' in classified_df.columns else pd.Series()

                nl_stats = {
                    'associated_ssd_min': nl_densities.min() if len(nl_densities) > 0 else None,
                    'associated_ssd_max': nl_densities.max() if len(nl_densities) > 0 else None,
                    'associated_ssd_mean': round(nl_densities.mean(), 4) if len(nl_densities) > 0 else None,
                    'associated_ssd_median': round(nl_densities.median(), 4) if len(nl_densities) > 0 else None,
                }

                # Add gamma stats for NL classifications
                nl_gammas = classified_df.loc[classified_df['LITHOLOGY_CODE'] == 'NL', 'gamma'].dropna() if 'gamma' in classified_df.columns else pd.Series()
                if len(nl_gammas) > 0:
                    nl_stats.update({
                        'gamma_min': nl_gammas.min(),
                        'gamma_max': nl_gammas.max(),
                        'gamma_mean': round(nl_gammas.mean(), 4),
                        'gamma_median': round(nl_gammas.median(), 4),
                    })
                else:
                    nl_stats.update({
                        'gamma_min': None,
                        'gamma_max': None,
                        'gamma_mean': None,
                        'gamma_median': None,
                    })

                nl_row = {
                    'lithology_name': 'No Lithology (NL) - INVESTIGATE',
                    'lithology_code': 'NL',
                    'lithology_qualifier': 'N/A',
                    'gamma_min': 'See NL Analysis Section',
                    'gamma_max': 'See NL Analysis Section',
                    'density_min': nl_stats.get('associated_ssd_min'),
                    'density_max': nl_stats.get('associated_ssd_max'),
                    'classification_count': nl_count,
                    'classification_percentage': round(nl_percentage, 2),
                    'associated_ssd_min': nl_stats.get('associated_ssd_min'),
                    'associated_ssd_max': nl_stats.get('associated_ssd_max'),
                    'associated_ssd_mean': nl_stats.get('associated_ssd_mean'),
                    'associated_ssd_median': nl_stats.get('associated_ssd_median'),
                }
                report_data.append(nl_row)

                # Add NL Analysis Header
                nl_header_row = {
                    'lithology_name': '=== NL ANALYSIS SECTION ===',
                    'lithology_code': f'NL Count: {nl_count}',
                    'lithology_qualifier': f'NL %: {round(nl_percentage, 2)}%',
                    'gamma_min': f'Gamma Range: {nl_stats.get("gamma_min"):.1f} - {nl_stats.get("gamma_max"):.1f}' if nl_stats.get("gamma_min") is not None else 'Gamma Range: N/A',
                    'gamma_max': f'Mean: {nl_stats.get("gamma_mean"):.1f}' if nl_stats.get("gamma_mean") is not None else 'Mean: N/A',
                    'density_min': f'Density Range: {nl_stats.get("associated_ssd_min"):.3f} - {nl_stats.get("associated_ssd_max"):.3f}' if nl_stats.get("associated_ssd_min") is not None else 'Density Range: N/A',
                    'density_max': f'Mean: {nl_stats.get("associated_ssd_mean"):.3f}' if nl_stats.get("associated_ssd_mean") is not None else 'Mean: N/A',
                    'classification_count': 'Individual NL Data Points Below',
                    'classification_percentage': '',
                    'associated_ssd_min': '',
                    'associated_ssd_max': '',
                    'associated_ssd_mean': '',
                    'associated_ssd_median': '',
                }
                report_data.append(nl_header_row)

                # Add Column Headers for NL Data Points
                nl_data_header_row = {
                    'lithology_name': '=== INDIVIDUAL NL DATA POINTS ===',
                    'lithology_code': 'Row #',
                    'lithology_qualifier': 'Depth',
                    'gamma_min': 'Gamma (API)',
                    'gamma_max': 'Density (g/cc)',
                    'density_min': 'Lithology Code',
                    'density_max': '',
                    'classification_count': '',
                    'classification_percentage': '',
                    'associated_ssd_min': '',
                    'associated_ssd_max': '',
                    'associated_ssd_mean': '',
                    'associated_ssd_median': '',
                }
                report_data.append(nl_data_header_row)

                # Get NL rows with their data
                nl_rows = classified_df.loc[classified_df['LITHOLOGY_CODE'] == 'NL'].copy()

                # Process NL rows in batches to show individual data points
                nl_batch_size = min(50, len(nl_rows))  # Show up to 50 individual NL points to keep report manageable

                for idx in range(min(nl_batch_size, len(nl_rows))):
                    row = nl_rows.iloc[idx]
                    nl_data_row = {
                        'lithology_name': f'NL_Data_Point_{idx+1}',
                        'lithology_code': str(idx+1),
                        'lithology_qualifier': round(float(row[DEPTH_COLUMN]), 3),
                        'gamma_min': round(float(row['gamma']), 2) if 'gamma' in row and pd.notna(row['gamma']) else 'N/A',
                        'gamma_max': round(float(row['short_space_density']), 4) if 'short_space_density' in row and pd.notna(row['short_space_density']) else 'N/A',
                        'density_min': 'NL',
                        'density_max': '',
                        'classification_count': '',
                        'classification_percentage': '',
                        'associated_ssd_min': '',
                        'associated_ssd_max': '',
                        'associated_ssd_mean': '',
                        'associated_ssd_median': '',
                    }
                    report_data.append(nl_data_row)

                # If there are more NL points than shown, add a summary
                if len(nl_rows) > nl_batch_size:
                    summary_row = {
                        'lithology_name': f'... and {len(nl_rows) - nl_batch_size} more NL data points',
                        'lithology_code': '',
                        'lithology_qualifier': '',
                        'gamma_min': '',
                        'gamma_max': '',
                        'density_min': '',
                        'density_max': '',
                        'classification_count': '',
                        'classification_percentage': '',
                        'associated_ssd_min': '',
                        'associated_ssd_max': '',
                        'associated_ssd_mean': '',
                        'associated_ssd_median': '',
                    }
                    report_data.append(summary_row)
            else:
                # No NL classifications - add standard NL row
                nl_row = {
                    'lithology_name': 'No Lithology (NL)',
                    'lithology_code': 'NL',
                    'lithology_qualifier': 'N/A',
                    'gamma_min': 'N/A',
                    'gamma_max': 'N/A',
                    'density_min': 'N/A',
                    'density_max': 'N/A',
                    'classification_count': 0,
                    'classification_percentage': 0.0,
                    'associated_ssd_min': None,
                    'associated_ssd_max': None,
                    'associated_ssd_mean': None,
                    'associated_ssd_median': None,
                }
                report_data.append(nl_row)

            # Add header row with metadata
            header_row = {
                'lithology_name': f'Report generated: {self.last_analysis_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.last_analysis_timestamp else "Unknown"}',
                'lithology_code': f'Source file: {os.path.basename(self.last_analysis_file) if self.last_analysis_file else "Unknown"}',
                'lithology_qualifier': f'Total rows analyzed: {total_rows}',
                'gamma_min': '',
                'gamma_max': '',
                'density_min': '',
                'density_max': '',
                'classification_count': '',
                'classification_percentage': '',
                'associated_ssd_min': '',
                'associated_ssd_max': '',
                'associated_ssd_mean': '',
                'associated_ssd_median': '',
            }
            report_data.insert(0, header_row)

            # Convert to DataFrame and export
            report_df = pd.DataFrame(report_data)
            report_df.to_csv(file_path, index=False)

            QMessageBox.information(self, "Report Exported",
                f"Lithology report exported successfully!\n\n"
                f"File: {os.path.basename(file_path)}\n"
                f"Rules analyzed: {len(rules)}\n"
                f"Total classifications: {total_rows}\n\n"
                f"The report includes density statistics from the most recent analysis.")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export lithology report: {str(e)}")
            import traceback
            traceback.print_exc()

    def create_manual_interbedding(self):
        """Handle manual interbedding creation from selected table rows."""
        if self.last_units_dataframe is None or self.last_units_dataframe.empty:
            QMessageBox.warning(self, "No Data", "No lithology units available. Please run an analysis first.")
            return

        # Get selected rows from the table
        selected_rows = set()
        for item in self.editorTable.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) < 2:
            QMessageBox.warning(self, "Selection Required", "Please select at least 2 consecutive lithology units to create interbedding.")
            return

        # Sort selected rows
        selected_rows = sorted(list(selected_rows))

        # Check if selected rows are consecutive
        if not self._are_rows_consecutive(selected_rows):
            QMessageBox.warning(self, "Invalid Selection", "Selected rows must be consecutive for interbedding.")
            return

        # Get the unit data for selected rows
        selected_units = []
        for row_idx in selected_rows:
            if row_idx < len(self.last_units_dataframe):
                unit_data = self.last_units_dataframe.iloc[row_idx].to_dict()
                selected_units.append(unit_data)

        # Open the interbedding dialog
        from .dialogs.interbedding_dialog import InterbeddingDialog
        dialog = InterbeddingDialog(selected_units, self)

        if dialog.exec():
            # Apply the interbedding changes
            interbedding_data = dialog.get_interbedding_data()
            self._apply_manual_interbedding(selected_rows, interbedding_data)

    def _are_rows_consecutive(self, row_indices):
        """Check if the given row indices are consecutive."""
        if not row_indices:
            return False

        sorted_indices = sorted(row_indices)
        for i in range(1, len(sorted_indices)):
            if sorted_indices[i] != sorted_indices[i-1] + 1:
                return False
        return True

    def _apply_manual_interbedding(self, selected_rows, interbedding_data):
        """Apply manual interbedding changes to the units dataframe."""
        if self.last_units_dataframe is None:
            return

        # Create a copy of the dataframe
        updated_df = self.last_units_dataframe.copy()

        # Remove the selected rows
        updated_df = updated_df.drop(selected_rows)

        # Reset index
        updated_df = updated_df.reset_index(drop=True)

        # Find insertion point (where the first selected row was)
        insert_idx = selected_rows[0]

        # Create new interbedded rows
        new_rows = []
        for lith in interbedding_data['lithologies']:
            # Find the rule for this lithology - ensure each lithology gets its own visual properties
            rule = None
            lith_code = lith['code'].upper() if lith['code'] else ''  # Normalize to uppercase
            for r in self.lithology_rules:
                rule_code = r.get('code', '').upper() if r.get('code') else ''  # Normalize to uppercase
                if rule_code == lith_code:
                    rule = r
                    break

            # If no rule found, create a default rule with basic properties
            if not rule:
                rule = {
                    'qualifier': '',
                    'shade': '',
                    'hue': '',
                    'colour': '',
                    'weathering': '',
                    'strength': '',
                    'background_color': '#FFFFFF',
                    'svg_path': self.find_svg_file(lith_code, '')
                }

            # Only the dominant lithology (sequence 1) gets the full thickness
            # Subordinate lithologies get 0 thickness since they're mixed in
            thickness = (interbedding_data['to_depth'] - interbedding_data['from_depth']) if lith['sequence'] == 1 else 0.0

            new_row = {
                'from_depth': interbedding_data['from_depth'],
                'to_depth': interbedding_data['to_depth'],
                'thickness': thickness,
                'LITHOLOGY_CODE': lith['code'],
                'lithology_qualifier': rule.get('qualifier', ''),
                'shade': rule.get('shade', ''),
                'hue': rule.get('hue', ''),
                'colour': rule.get('colour', ''),
                'weathering': rule.get('weathering', ''),
                'estimated_strength': rule.get('strength', ''),
                'background_color': rule.get('background_color', '#FFFFFF'),
                'svg_path': rule.get('svg_path', self.find_svg_file(lith['code'], '')),
                'record_sequence': lith['sequence'],
                'inter_relationship': interbedding_data['interrelationship_code'] if lith['sequence'] == 1 else '',
                'percentage': lith['percentage']
            }
            new_rows.append(new_row)

        # Insert new rows at the correct position
        if insert_idx >= len(updated_df):
            # Append to end
            for new_row in new_rows:
                updated_df = updated_df.append(new_row, ignore_index=True)
        else:
            # Split dataframe and insert
            before = updated_df.iloc[:insert_idx]
            after = updated_df.iloc[insert_idx:]
            middle = pd.DataFrame(new_rows)
            updated_df = pd.concat([before, middle, after], ignore_index=True)

        # Update the stored dataframe
        self.last_units_dataframe = updated_df

        # Refresh the display
        editor_columns = [
            'from_depth', 'to_depth', 'thickness', 'LITHOLOGY_CODE',
            'lithology_qualifier', 'shade', 'hue', 'colour',
            'weathering', 'estimated_strength', 'record_sequence',
            'inter_relationship', 'percentage'
        ]
        if 'background_color' in updated_df.columns:
            editor_columns.append('background_color')

        editor_dataframe = updated_df[[col for col in editor_columns if col in updated_df.columns]]
        self.editorTable.load_data(editor_dataframe)

        # Update stratigraphic column
        if hasattr(self, 'stratigraphicColumnView'):
            separator_thickness = self.separatorThicknessSpinBox.value()
            draw_separators = self.drawSeparatorsCheckBox.isChecked()
            if self.last_classified_dataframe is not None:
                min_depth = self.last_classified_dataframe[DEPTH_COLUMN].min()
                max_depth = self.last_classified_dataframe[DEPTH_COLUMN].max()
                self.stratigraphicColumnView.draw_column(updated_df, min_depth, max_depth, separator_thickness, draw_separators)

        QMessageBox.information(self, "Interbedding Created", f"Successfully created interbedding with {len(new_rows)} components.")

    def _check_smart_interbedding_suggestions(self, units_dataframe, classified_dataframe):
        """Check for smart interbedding suggestions and show dialog if found."""
        try:
            # Debug: Method Entry
            print("DEBUG: _check_smart_interbedding_suggestions method called")
            print(f"DEBUG: Smart interbedding enabled: {self.smart_interbedding}")
            print(f"DEBUG: Max sequence length: {self.smart_interbedding_max_sequence_length}")
            print(f"DEBUG: Thick unit threshold: {self.smart_interbedding_thick_unit_threshold}")

            # Debug: Input Validation
            print(f"DEBUG: Units dataframe shape: {units_dataframe.shape if hasattr(units_dataframe, 'shape') else 'No shape'}")
            print(f"DEBUG: Units dataframe columns: {list(units_dataframe.columns) if hasattr(units_dataframe, 'columns') else 'No columns'}")
            print(f"DEBUG: First 5 units: {units_dataframe.head() if hasattr(units_dataframe, 'head') else 'No head method'}")
            print(f"DEBUG: Classified dataframe shape: {classified_dataframe.shape if hasattr(classified_dataframe, 'shape') else 'No shape'}")

            # Create analyzer instance for post-processing
            analyzer = Analyzer()

            # Find interbedding candidates
            max_sequence_length = self.smart_interbedding_max_sequence_length
            thick_unit_threshold = self.smart_interbedding_thick_unit_threshold

            print(f"DEBUG: Calling find_interbedding_candidates with max_sequence_length={max_sequence_length}, thick_unit_threshold={thick_unit_threshold}")
            candidates = analyzer.find_interbedding_candidates(
                units_dataframe,
                max_sequence_length=max_sequence_length,
                thick_unit_threshold=thick_unit_threshold
            )

            print(f"DEBUG: Found {len(candidates) if candidates else 0} interbedding candidates")

            if candidates:
                print("DEBUG: Candidates found, creating SmartInterbeddingSuggestionsDialog")
                # Debug: Show candidate details
                for i, candidate in enumerate(candidates):
                    print(f"DEBUG: Candidate {i}: from_depth={candidate.get('from_depth')}, to_depth={candidate.get('to_depth')}, lithologies={len(candidate.get('lithologies', []))}")

                # Show suggestions dialog
                from .dialogs.smart_interbedding_suggestions_dialog import SmartInterbeddingSuggestionsDialog
                dialog = SmartInterbeddingSuggestionsDialog(candidates, self)
                print("DEBUG: SmartInterbeddingSuggestionsDialog created")

                dialog_result = dialog.exec()
                print(f"DEBUG: Dialog exec() returned: {dialog_result}")

                if dialog_result:
                    print("DEBUG: Dialog accepted, getting selected candidates")
                    # Apply selected suggestions
                    selected_indices = dialog.get_selected_candidates()
                    print(f"DEBUG: Selected candidate indices: {selected_indices}")

                    if selected_indices:
                        print("DEBUG: Applying interbedding candidates")
                        updated_units_df = analyzer.apply_interbedding_candidates(
                            units_dataframe, candidates, selected_indices, self.lithology_rules
                        )
                        # Update stored dataframe
                        self.last_units_dataframe = updated_units_df
                        print(f"DEBUG: Updated units dataframe shape: {updated_units_df.shape if hasattr(updated_units_df, 'shape') else 'No shape'}")
                    else:
                        print("DEBUG: No candidates selected")
                else:
                    print("DEBUG: Dialog rejected")

                # Continue to finalize display regardless of user choice
                print("DEBUG: Finalizing analysis display with updated dataframe")
                self._finalize_analysis_display(self.last_units_dataframe, classified_dataframe)
            else:
                print("DEBUG: No candidates found, proceeding with normal display")
                # No candidates found, proceed normally
                self._finalize_analysis_display(units_dataframe, classified_dataframe)

        except Exception as e:
            # Log error and continue with normal display
            print(f"DEBUG: Exception in smart interbedding suggestions: {e}")
            import traceback
            traceback.print_exc()
            self._finalize_analysis_display(units_dataframe, classified_dataframe)

    def _finalize_analysis_display(self, units_dataframe, classified_dataframe):
        """Finalize the analysis display after all processing is complete."""
        # Get separator settings from UI controls
        separator_thickness = self.separatorThicknessSpinBox.value()
        draw_separators = self.drawSeparatorsCheckBox.isChecked()

        # Calculate overall min and max depth from the classified_dataframe
        # This ensures both plots use the same consistent depth scale
        min_overall_depth = classified_dataframe[DEPTH_COLUMN].min()
        max_overall_depth = classified_dataframe[DEPTH_COLUMN].max()

        # Pass the overall depth range to the stratigraphic column
        self.stratigraphicColumnView.draw_column(units_dataframe, min_overall_depth, max_overall_depth, separator_thickness, draw_separators)

        # Prepare curve configurations for the single CurvePlotter
        curve_configs = []
        curve_inversion_settings = {
            'gamma': self.invertGammaCheckBox.isChecked(),
            'short_space_density': self.invertShortSpaceDensityCheckBox.isChecked(),
            'long_space_density': self.invertLongSpaceDensityCheckBox.isChecked()
        }
        current_curve_thickness = self.curveThicknessSpinBox.value()

        if 'gamma' in classified_dataframe.columns:
            curve_configs.append({
                'name': 'gamma',
                'min': CURVE_RANGES['gamma']['min'],
                'max': CURVE_RANGES['gamma']['max'],
                'color': CURVE_RANGES['gamma']['color'],
                'inverted': curve_inversion_settings.get('gamma', False),
                'thickness': current_curve_thickness
            })
        if 'short_space_density' in classified_dataframe.columns:
            curve_configs.append({
                'name': 'short_space_density',
                'min': CURVE_RANGES['short_space_density']['min'],
                'max': CURVE_RANGES['short_space_density']['max'],
                'color': CURVE_RANGES['short_space_density']['color'],
                'inverted': curve_inversion_settings.get('short_space_density', False),
                'thickness': current_curve_thickness
            })
        if 'long_space_density' in classified_dataframe.columns:
            curve_configs.append({
                'name': 'long_space_density',
                'min': CURVE_RANGES['long_space_density']['min'],
                'max': CURVE_RANGES['long_space_density']['max'],
                'color': CURVE_RANGES['long_space_density']['color'],
                'inverted': curve_inversion_settings.get('long_space_density', False),
                'thickness': current_curve_thickness
            })

        # Update the single curve plotter and set its depth range
        self.curvePlotter.set_curve_configs(curve_configs)
        self.curvePlotter.set_data(classified_dataframe)
        self.curvePlotter.set_depth_range(min_overall_depth, max_overall_depth)

        editor_columns = [
            'from_depth', 'to_depth', 'thickness', 'LITHOLOGY_CODE',
            'lithology_qualifier', 'shade', 'hue', 'colour',
            'weathering', 'estimated_strength', 'record_sequence',
            'inter_relationship', 'percentage'
        ]
        if 'background_color' in units_dataframe.columns:
            editor_columns.append('background_color')

        editor_dataframe = units_dataframe[[col for col in editor_columns if col in units_dataframe.columns]]
        self.editorTable.load_data(editor_dataframe)
        self.tab_widget.setCurrentIndex(self.tab_widget.indexOf(self.editor_tab))
        QMessageBox.information(self, "Analysis Complete", "Borehole analysis finished successfully!")

    def _schedule_gap_visualization_update(self):
        """Schedule a debounced update of the gap visualization to prevent excessive updates during rapid user input."""
        # Start or restart the timer with 500ms delay
        self.gap_update_timer.start(500)

    def _perform_gap_visualization_update(self):
        """Perform the actual gap visualization update after debounce delay."""
        try:
            self.refresh_range_visualization()
        except Exception as e:
            # Log error but don't crash the application
            print(f"Error updating gap visualization: {e}")
            import traceback
            traceback.print_exc()
    
    # ====== MDI METHODS ======
    
    def new_hole(self):
        """Create a new drill hole editor window"""
        sub_window = HoleEditorSubWindow(parent=self)
        sub_window.setWindowTitle(f"Hole Editor {self.window_counter} - Untitled")
        self.mdi_area.addSubWindow(sub_window)
        sub_window.show()
        self.window_counter += 1
        self.update_window_menu()
    
    def open_hole(self):
        """Open an existing drill hole file in new sub-window"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Drill Hole File", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;LAS Files (*.las);;All Files (*.*)"
        )
        
        if file_path:
            sub_window = HoleEditorSubWindow(file_path, parent=self)
            self.mdi_area.addSubWindow(sub_window)
            sub_window.show()
            self.update_window_menu()
    
    def close_active_window(self):
        """Close the active sub-window"""
        active = self.mdi_area.activeSubWindow()
        if active:
            active.close()
    
    def close_all_windows(self):
        """Close all sub-windows"""
        for window in self.mdi_area.subWindowList():
            window.close()
    
    def update_window_menu(self):
        """Update the Window menu with list of open windows"""
        # Clear existing window list (skip permanent actions)
        for action in self.window_menu.actions():
            if action.text().startswith("&") and not action.text()[1:2].isdigit():
                continue  # Keep permanent actions
            self.window_menu.removeAction(action)
        
        # Add separator if there are windows
        windows = self.mdi_area.subWindowList()
        if windows:
            self.window_menu.addSeparator()
        
        # Add each window to menu
        for i, window in enumerate(windows):
            action = QAction(f"&{i+1} {window.windowTitle()}", self)
            action.triggered.connect(lambda checked, w=window: self.activate_window(w))
            self.window_menu.addAction(action)
    
    
    
    def open_file_from_sidebar(self):
        """Open the currently selected file from sidebar"""
        file_path = self.project_sidebar.get_selected_file()
        if file_path and os.path.isfile(file_path):
            # Check if it's a supported file type
            if file_path.lower().endswith(('.csv', '.xlsx', '.las')):
                self.open_hole_with_path(file_path)
            else:
                QMessageBox.warning(self, "Unsupported File", 
                                   f"Unsupported file type: {os.path.basename(file_path)}")
    
    def open_hole_with_path(self, file_path):
        """Open a hole with specific file path (used by sidebar)"""
        sub_window = HoleEditorSubWindow(file_path, parent=self)
        self.mdi_area.addSubWindow(sub_window)
        sub_window.show()
        
        # Load the file into the sub-window
        sub_window.load_file(file_path)
        
        self.update_window_menu()
        
    def activate_window(self, window):
        """Activate a specific window"""
        window.setFocus()
        window.showNormal()
        window.raise_()
    
    def show_settings_dialog(self):
        """Show the tabbed settings dialog"""
        dialog = TabbedSettingsDialog(parent=self)
        dialog.exec()
    
