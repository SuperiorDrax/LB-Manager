
"""
Custom delegate for rendering comic cards in virtualized grid view
Manages widget pooling and image loading
"""
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QStyleOptionViewItem, QFrame
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QEvent, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap, QPalette
from .widget_pool import WidgetPool, ComicCardWidget
import time
from typing import Optional, Dict, Any


class ComicCardDelegate(QStyledItemDelegate):
    """
    Delegate for rendering comic cards with widget pooling
    
    This delegate:
    1. Uses widget pool to reuse QWidget instances
    2. Only creates widgets for visible items
    3. Manages image loading and caching
    4. Handles mouse interactions
    """
    
    def __init__(self, main_window, parent_view=None):
        super().__init__(parent_view)
        self.main_window = main_window
        self.parent_view = parent_view
        
        # Widget pool for reusing card widgets
        self.widget_pool = WidgetPool(main_window, max_size=50)
        
        # Image loading queue
        self.image_load_queue = []
        self.is_loading_images = False
        
        # Performance tracking
        self._visible_range = (0, 0)
        self._last_update_time = 0
        self._update_throttle_ms = 100
        
        # Style configuration
        self.card_size = QSize(140, 250)
        self.cover_size = QSize(120, 170)
        
        # Connect to model signals if available
        if hasattr(main_window, 'table') and hasattr(main_window.table, 'get_model'):
            model = main_window.table.get_model()
            if model:
                model.dataChanged.connect(self.on_model_data_changed)
                model.layoutChanged.connect(self.on_model_layout_changed)
                
    def sizeHint(self, option, index):
        """
        Return fixed size for all items
        """
        return QSize(140, 250)
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """
        Paint only background - widgets handle content
        This prevents double rendering
        """
        if not index.isValid():
            return
            
        # Paint only background for selection/hover
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(227, 242, 253))  # Light blue
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor(248, 249, 250))  # Light gray
            
        # Draw border if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor(33, 150, 243), 2))  # Blue border
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 6, 6)
            painter.restore()
            
    def paint_card_background(self, painter, option, index):
        """
        Paint card background with rounded corners
        """
        rect = option.rect.adjusted(1, 1, -1, -1)
        
        # Set background color
        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = QColor(227, 242, 253)  # Light blue for selection
        elif option.state & QStyle.StateFlag.State_MouseOver:
            bg_color = QColor(248, 249, 250)  # Light gray for hover
        else:
            bg_color = QColor(255, 255, 255)  # White
            
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 6, 6)
        
        # Draw border
        border_color = QColor(222, 226, 230)
        if option.state & QStyle.StateFlag.State_Selected:
            border_color = QColor(33, 150, 243)  # Blue for selection
            
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)
        painter.restore()
        
    def paint_card_content(self, painter, option, index):
        """
        Paint card content (title, author, status)
        Note: Cover images are handled by widget pooling
        """
        # Get data from model
        model = index.model()
        row_data = self.get_row_data(index.row(), model)
        if not row_data:
            return
            
        rect = option.rect
        padding = 8
        
        # Title (top area)
        title = row_data.get('title', '')
        if len(title) > 10:
            title = title[:8] + '...'
            
        title_rect = QRect(
            rect.left() + padding,
            rect.top() + self.cover_size.height() + padding * 2,
            rect.width() - padding * 2,
            40
        )
        
        painter.save()
        painter.setPen(QColor(44, 62, 80))  # Dark blue text
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, title)
        painter.restore()
        
        # Author (middle area)
        author = row_data.get('author', '')
        author_rect = QRect(
            rect.left() + padding,
            title_rect.bottom(),
            rect.width() - padding * 2,
            20
        )
        
        painter.save()
        painter.setPen(QColor(127, 140, 141))  # Gray text
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(author_rect, Qt.AlignmentFlag.AlignCenter, author)
        painter.restore()
        
        # Status (bottom area)
        status = row_data.get('read_status', 'unread')
        status_text = {
            'unread': 'Unread',
            'reading': 'Reading',
            'completed': 'Completed'
        }.get(status, status)
        
        status_color = {
            'unread': QColor(231, 76, 60),    # Red
            'reading': QColor(243, 156, 18),  # Orange
            'completed': QColor(39, 174, 96)  # Green
        }.get(status, QColor(149, 165, 166))  # Gray
        
        status_rect = QRect(
            rect.left() + padding,
            author_rect.bottom(),
            rect.width() - padding * 2,
            16
        )
        
        # Draw status background
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(status_color))
        painter.drawRoundedRect(status_rect, 8, 8)
        
        # Draw status text
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, status_text)
        painter.restore()
        
    def paint_selection_border(self, painter, option):
        """
        Paint selection border around card
        """
        rect = option.rect.adjusted(1, 1, -1, -1)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(33, 150, 243), 2))  # Blue border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)
        painter.restore()
        
    def createEditor(self, parent, option, index):
        """
        Create editor for item - not used for comic cards
        """
        return None
        
    def updateEditorGeometry(self, editor, option, index):
        """
        Update editor geometry - not used for comic cards
        """
        pass
        
    def editorEvent(self, event, model, option, index):
        """
        Handle editor events (mouse interactions)
        """
        if not index.isValid():
            return False
            
        event_type = event.type()
        
        if event_type == QEvent.Type.MouseButtonPress:
            return self.handle_mouse_press(event, model, index)
        elif event_type == QEvent.Type.MouseButtonDblClick:
            return self.handle_double_click(event, model, index)
        elif event_type == QEvent.Type.MouseMove:
            return self.handle_mouse_move(event, model, index)
            
        return super().editorEvent(event, model, option, index)
        
    def handle_mouse_press(self, event, model, index):
        """
        Handle mouse press events
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Let the parent view handle selection
            return False
        return False
        
    def handle_double_click(self, event, model, index):
        """
        Handle double click events
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Notify parent view
            if self.parent_view:
                self.parent_view.doubleClicked.emit(index)
            return True
        return False
        
    def handle_mouse_move(self, event, model, index):
        """
        Handle mouse move events for hover effects
        """
        # Update hover state
        option = QStyleOptionViewItem()
        self.initStyleOption(option, index)
        
        # Check if mouse is over this item
        if option.rect.contains(event.pos()):
            # Set hover state
            option.state |= QStyle.StateFlag.State_MouseOver
            # Trigger repaint
            if self.parent_view:
                self.parent_view.viewport().update()
            return True
            
        return False

    def set_visible_rows(self, visible_rows):
        """
        Set which rows are currently visible (for paging)
        
        Args:
            visible_rows: List of row indices in full model
        """
        self._visible_rows = visible_rows
        
    def rowCount(self, parent=None):
        """Override row count for paging"""
        if hasattr(self, '_visible_rows'):
            return len(self._visible_rows)
        return super().rowCount(parent)
        
    def get_row_data(self, row, model):
        """
        Get row data from model
        """
        if hasattr(model, 'get_row_data'):
            return model.get_row_data(row)
        
        # Fallback: create basic row data
        row_data = {}
        columns = ['websign', 'author', 'title', 'group', 'show', 
                'magazine', 'origin', 'tag', 'read_status', 'progress', 'file_path']
        
        for i, column in enumerate(columns):
            if i < model.columnCount():
                index = model.index(row, i)
                value = model.data(index, Qt.ItemDataRole.DisplayRole)
                row_data[column] = str(value) if value is not None else ""
        
        return row_data
        
    def update_visible_range(self, start_row, end_row):
        """
        Update which rows are currently visible
        Manage widget pool accordingly
        """
        current_time = time.time() * 1000
        
        # Throttle updates
        if current_time - self._last_update_time < self._update_throttle_ms:
            return
            
        self._last_update_time = current_time
        self._visible_range = (start_row, end_row)
        
        # Update widget pool
        self.widget_pool.update_visible_range(start_row, end_row)
        
        # Schedule image loading for visible items
        QTimer.singleShot(50, self.load_visible_images)
        
    def load_visible_images(self):
        """
        Load images for currently visible items
        """
        if self.is_loading_images:
            return
            
        self.is_loading_images = True
        
        try:
            # Get visible widgets
            visible_widgets = self.widget_pool.get_visible_widgets()
            
            for row, widget in visible_widgets:
                if hasattr(widget, 'load_cover_image'):
                    # Schedule image loading
                    QTimer.singleShot(0, widget.load_cover_image)
                    
        finally:
            self.is_loading_images = False
            
    def on_model_data_changed(self, top_left, bottom_right, roles):
        """
        Handle model data changes
        """
        # Update affected widgets
        for row in range(top_left.row(), bottom_right.row() + 1):
            widget = self.widget_pool.get_widget_for_row(row)
            if widget and hasattr(widget, 'update_content'):
                # Get updated row data from model
                if hasattr(self.parent_view, 'model'):
                    model = self.parent_view.model()
                    if model:
                        row_data = self.get_row_data(row, model)
                        if row_data:
                            widget.update_content(row_data, row)  # Pass arguments!
                
    def on_model_layout_changed(self):
        """
        Handle model layout changes (sorting, filtering)
        """
        # Invalidate widget pool
        self.widget_pool.invalidate_all()
        
    def get_widget_pool_stats(self):
        """
        Get widget pool statistics
        
        Returns:
            dict: Pool statistics
        """
        return self.widget_pool.get_stats()
        
    def cleanup(self):
        """
        Clean up resources
        """
        self.widget_pool.cleanup()