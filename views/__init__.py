"""
Views package for LB Manager
"""
from .main_window import MainWindow
from .virtual_table_view import VirtualTableView
from .virtual_grid_view import VirtualGridView
from .comic_card_delegate import ComicCardDelegate
from .widget_pool import WidgetPool, ComicCardWidget
from .sidebar import Sidebar
from .detail_panel import DetailPanel
from .tag_cloud import TagCloud
from .dialogs import InsertDialog, SearchDialog, EditDialog
from .image_viewer import ImageViewer

__all__ = [
    'MainWindow',
    'VirtualTableView',
    'VirtualGridView',
    'ComicCardDelegate',
    'WidgetPool',
    'ComicCardWidget',
    'Sidebar',
    'DetailPanel',
    'TagCloud',
    'InsertDialog',
    'SearchDialog',
    'EditDialog',
    'ImageViewer'
]