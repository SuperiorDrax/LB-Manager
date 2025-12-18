"""
True virtualized grid view for comic browsing
Overrides QListView layout methods for precise spacing control
"""
from PyQt6.QtWidgets import QListView, QAbstractItemView, QApplication, QFrame
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QRect, QModelIndex
from PyQt6.QtGui import QPalette, QPainter
from .comic_card_delegate import ComicCardDelegate
import time

class VirtualGridView(QListView):
    """True virtualized grid view with precise spacing control"""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        # Card and spacing configuration
        self.card_size = QSize(140, 250)
        self.horizontal_spacing = 15
        self.vertical_spacing = 15
        
        # Basic configuration
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMovement(QListView.Movement.Static)
        
        # CRITICAL FIX: Use custom delegate
        self.delegate = ComicCardDelegate(self.main_window, self)
        self.setItemDelegate(self.delegate)
        
        # Disable QListView's default spacing
        self.setSpacing(0)
        
        # Update grid metrics
        self._update_grid_metrics()
        
        # Set no frame
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Widget management
        self._visible_widgets = {}  # row -> widget
        self._pending_updates = False
        
        # Performance monitoring
        self._last_scroll_time = 0
        self._scroll_throttle_ms = 50
        self._performance_stats = {
            'visible_items': 0,
            'widget_pool_size': 0,
            'cache_hit_rate': 0,
            'last_paint_time': 0
        }
        
        # Connect signals
        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.clicked.connect(self.on_item_clicked)
        self.doubleClicked.connect(self.on_item_double_clicked)
        
        # Schedule initial layout
        QTimer.singleShot(100, self.update_widget_positions)
        
    def update_visible_items(self):
        """Update which items have widget representation"""
        if not self.model():
            return
            
        model = self.model()
        
        if model.rowCount() == 0:
            self._clear_all_widgets()
            return
            
        # Calculate which rows are actually visible in viewport
        viewport_rect = self.viewport().rect()
        scroll_y = self.verticalScrollBar().value()
        viewport_height = viewport_rect.height()
        
        # Calculate visible Y range in virtual space
        visible_top_virtual = scroll_y
        visible_bottom_virtual = scroll_y + viewport_height
        
        # Convert virtual Y to grid rows
        columns_per_row = self._calculate_columns_per_row()
        if columns_per_row == 0:
            return
            
        grid_height = self.gridSize().height()
        
        start_grid_y = visible_top_virtual // grid_height
        end_grid_y = visible_bottom_virtual // grid_height
        
        # Convert grid Y to model rows
        start_row = max(0, start_grid_y * columns_per_row)
        end_row = min(model.rowCount() - 1, (end_grid_y + 1) * columns_per_row - 1)
        
        # Add buffer
        buffer_rows = 2
        buffer_grid_y = buffer_rows
        start_row = max(0, start_row - buffer_grid_y * columns_per_row)
        end_row = min(model.rowCount() - 1, end_row + buffer_grid_y * columns_per_row)
        
        # Create/update widgets
        self._update_widgets_for_rows(start_row, end_row)
        
        # Remove non-visible widgets
        self._remove_non_visible_widgets(start_row, end_row)
        
        # Update positions
        self.update_widget_positions()
        
    def _update_widgets_for_rows(self, start_row, end_row):
        """Create or update widgets for specified rows"""
        for row in range(start_row, end_row + 1):
            if row not in self._visible_widgets:
                # Create new widget for this row
                self._create_widget_for_row(row)
            else:
                # Update existing widget position
                self._update_widget_position(row)
                
    def _create_widget_for_row(self, row):
        """Create and position widget for a specific row"""
        if not self.model():
            return
            
        index = self.model().index(row, 0)
        if not index.isValid():
            return
            
        # Get row data
        model = self.model()
        row_data = self._get_row_data(row, model)
        if not row_data:
            return
            
        # Get widget from delegate's pool
        widget = self.delegate.widget_pool.acquire_widget(row, row_data)
        if not widget:
            return
            
        # Set widget parent to viewport
        widget.setParent(self.viewport())
        
        # Set widget position
        rect = self.visualRect(index)
        widget.setGeometry(rect)
        
        # Make widget visible
        widget.show()
        widget.raise_()
        
        # Store reference
        self._visible_widgets[row] = widget
        
        # Connect signals
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
    def _get_row_data(self, row, model):
        """Extract row data from model"""
        return model.get_row_data(row)
        
    def _update_widget_position(self, row):
        """Update position of existing widget"""
        if row not in self._visible_widgets:
            return
            
        index = self.model().index(row, 0)
        if not index.isValid():
            return
            
        widget = self._visible_widgets[row]
        rect = self.visualRect(index)
        widget.setGeometry(rect)
        
    def _remove_non_visible_widgets(self, start_row, end_row):
        """Remove widgets for rows no longer visible"""
        rows_to_remove = []
        
        for row in list(self._visible_widgets.keys()):
            if row < start_row or row > end_row:
                rows_to_remove.append(row)
                
        for row in rows_to_remove:
            widget = self._visible_widgets[row]
            
            # Return widget to pool
            self.delegate.widget_pool.release_widget(row)
            
            # Remove from viewport
            widget.hide()
            widget.setParent(None)
            
            del self._visible_widgets[row]
            
    def _clear_all_widgets(self):
        """Clear all widgets from viewport"""
        for row, widget in list(self._visible_widgets.items()):
            self.delegate.widget_pool.release_widget(row)
            widget.hide()
            widget.setParent(None)
            
        self._visible_widgets.clear()
        
    def _on_widget_clicked(self, row):
        """Handle widget click"""
        index = self.model().index(row, 0)
        if index.isValid():
            self.on_item_clicked(index)

    def update_widget_positions(self):
        """Update positions of all visible widgets"""
        if not self.model():
            return
            
        viewport = self.viewport()
        viewport_rect = viewport.rect()
        
        for row, widget in self._visible_widgets.items():
            index = self.model().index(row, 0)
            if index.isValid():
                # Get viewport-relative position
                rect = self.visualRect(index)
                
                # Check if widget is within or near viewport
                widget_visible = rect.intersects(viewport_rect) or \
                                rect.top() < viewport_rect.bottom() + 100 or \
                                rect.bottom() > viewport_rect.top() - 100
                
                if widget_visible:
                    widget.setGeometry(rect)
                    widget.show()
                else:
                    # Widget is far outside viewport, hide it
                    widget.hide()
                
    def resizeEvent(self, event):
        """
        Handle resize events
        """
        super().resizeEvent(event)
        
        # Update grid metrics
        self._update_grid_metrics()
        
        # Update widget positions
        QTimer.singleShot(50, self.update_widget_positions)
        QTimer.singleShot(100, self.update_visible_items)
        
    def scrollContentsBy(self, dx, dy):
        """Handle scrolling - update widget positions"""
        super().scrollContentsBy(dx, dy)
        
        # Update widget positions after scroll
        QTimer.singleShot(10, self.update_widget_positions)
        
    def paintEvent(self, event):
        """
        Override paint event
        IMPORTANT: We paint background only, widgets handle content
        """
        # Paint background
        painter = QPainter(self.viewport())
        painter.fillRect(event.rect(), self.palette().color(QPalette.ColorRole.Base))
        painter.end()
        
        # Call parent for selection painting
        super().paintEvent(event)
        
    def setModel(self, model):
        """Set model and clear existing widgets"""
        # Clear existing widgets
        self._clear_all_widgets()
        
        # Set new model
        super().setModel(model)
        
        # Update visible items
        QTimer.singleShot(100, self.update_visible_items)

    def _update_grid_metrics(self):
        """Update grid metrics: grid cell = card size + spacing"""
        grid_width = self.card_size.width() + self.horizontal_spacing
        grid_height = self.card_size.height() + self.vertical_spacing
        self.setGridSize(QSize(grid_width, grid_height))

    def on_scroll(self, value):
        """
        Handle scroll events with throttling
        """
        current_time = time.time() * 1000
        if current_time - self._last_scroll_time > self._scroll_throttle_ms:
            self._last_scroll_time = current_time
            # Trigger deferred update
            QTimer.singleShot(10, self.update_visible_items)

    def on_item_clicked(self, index):
        """Simplest click handler - just select the item"""
        if not index.isValid():
            return
        
        # Just select the clicked item
        self.selectionModel().select(index, 
            self.selectionModel().SelectionFlag.ClearAndSelect)
        
    def on_item_double_clicked(self, index):
        """Handle item double click to open viewer"""        
        if not index.isValid():
            return
            
        # Select the item
        self.selectionModel().select(index, self.selectionModel().SelectionFlag.Select)
        
        # Open viewer using main window's handler
        self.main_window.on_table_double_click(index)

    def set_main_window_model(self):
        """
        Set the model from main window's table
        This should be called after main window initialization
        """
        model = self.main_window.table.get_model()
        if model:
            # Store reference to source model
            self.source_model = model
            
            # Set model to the view
            self.setModel(model)
            print(f"[VirtualGridView] Model set with {model.rowCount()} rows")
            
            # Connect to model signals for data changes
            model.dataChanged.connect(self._on_model_data_changed)
            model.rowsInserted.connect(self._on_rows_inserted)
            model.rowsRemoved.connect(self._on_rows_removed)
            model.layoutChanged.connect(self._on_model_layout_changed)
            
            # Update visible items after model is set
            QTimer.singleShot(100, self.update_visible_items)

    def _on_model_data_changed(self, top_left, bottom_right, roles):
        """Handle data changes in the model"""
        # Update widgets for affected rows
        for row in range(top_left.row(), bottom_right.row() + 1):
            if row in self._visible_widgets:
                # Update existing widget
                widget = self._visible_widgets[row]
                if self.model():
                    row_data = self._get_row_data(row, self.model())
                    widget.update_content(row_data, row)
        
        # Schedule view update
        QTimer.singleShot(10, self.update_visible_items)

    def _on_rows_inserted(self, parent, first, last):
        """Handle rows being inserted"""
        # Clear all widgets and rebuild
        self._clear_all_widgets()
        
        # Update visible items
        QTimer.singleShot(50, self.update_visible_items)

    def _on_rows_removed(self, parent, first, last):
        """Handle rows being removed"""
        # Remove widgets for removed rows
        for row in range(first, last + 1):
            if row in self._visible_widgets:
                widget = self._visible_widgets[row]
                self.delegate.widget_pool.release_widget(row)
                widget.hide()
                widget.setParent(None)
                del self._visible_widgets[row]
        
        # Update remaining widget positions
        self.update_widget_positions()

    def _on_model_layout_changed(self):
        """Handle layout changes (sorting, filtering)"""
        # Clear all widgets and rebuild
        self._clear_all_widgets()
        
        # Update visible items
        QTimer.singleShot(50, self.update_visible_items)

    def indexAt(self, point):
        """
        Override indexAt to find item based on position
        Accounts for scroll position!
        """
        if not self.model() or self.model().rowCount() == 0:
            return QModelIndex()
            
        columns_per_row = self._calculate_columns_per_row()
        if columns_per_row == 0:
            return QModelIndex()
        
        # CRITICAL: Add scroll offset to Y coordinate
        scroll_y = self.verticalScrollBar().value()
        adjusted_y = point.y() + scroll_y  # Add scroll offset!
        
        # Calculate which grid cell was clicked (using adjusted Y)
        grid_x = point.x() // self.gridSize().width()
        grid_y = adjusted_y // self.gridSize().height()  # Use adjusted_y!
        
        # Calculate row index
        row = grid_y * columns_per_row + grid_x
        
        if 0 <= row < self.model().rowCount():
            return self.model().index(row, 0)
            
        return QModelIndex()

    def visualRect(self, index):
        """
        Override visualRect to precisely position each item
        Returns viewport-relative coordinates
        """
        if not index.isValid():
            return QRect()
            
        # Calculate row and column
        row = index.row()
        columns_per_row = self._calculate_columns_per_row()
        
        if columns_per_row == 0:
            return QRect()
            
        col = row % columns_per_row
        actual_row = row // columns_per_row
        
        # Calculate ABSOLUTE position in virtual space
        x_absolute = col * self.gridSize().width()
        y_absolute = actual_row * self.gridSize().height()
        
        # Offset within grid cell (center the card)
        x_offset = (self.gridSize().width() - self.card_size.width()) // 2
        y_offset = (self.gridSize().height() - self.card_size.height()) // 2
        
        # Convert to VIEWPORT-RELATIVE coordinates by subtracting scroll offset
        scroll_y = self.verticalScrollBar().value()
        
        x_viewport = x_absolute + x_offset
        y_viewport = y_absolute + y_offset - scroll_y  # Subtract scroll!
        
        return QRect(x_viewport, y_viewport, 
                    self.card_size.width(), self.card_size.height())

    def refresh(self):
        """Manually refresh the grid view"""
        print("[VirtualGridView] Manual refresh called")
        self._clear_all_widgets()
        self.update_visible_items()

    def _calculate_columns_per_row(self):
        """Calculate number of columns per row"""
        viewport_width = self.viewport().width()
        grid_width = self.gridSize().width()
        
        if viewport_width <= 0 or grid_width <= 0:
            return 1
            
        columns = max(1, viewport_width // grid_width)
        return columns

    def wheelEvent(self, event):
        """
        Handle wheel events with debug
        """
        # Call parent for actual scrolling
        super().wheelEvent(event)
        
        # Update widget positions after scroll
        QTimer.singleShot(10, self.update_widget_positions)

    def get_selected_rows(self):
        """
        Get all selected row indices
        
        Returns:
            List[int]: List of selected row indices (sorted)
        """
        selected_indexes = self.selectedIndexes()
        
        # Get unique rows
        rows = set()
        for index in selected_indexes:
            if index.isValid():
                rows.add(index.row())  # This is MODEL row index
        
        return sorted(list(rows))
    
    def selectionChanged(self, selected, deselected):
        """Handle selection changes"""
        super().selectionChanged(selected, deselected)
        
        # Notify main window
        self.main_window.on_grid_selection_changed()

    def showEvent(self, event):
        """Handle show event - load images when grid becomes visible"""
        super().showEvent(event)
        
        # Force update of visible items to load images
        QTimer.singleShot(50, self._load_visible_images)

    def _load_visible_images(self):
        """Load images for all visible widgets"""
        if not self.model():
            return
            
        for row, widget in self._visible_widgets.items():
            # Schedule image loading
            QTimer.singleShot(0, widget.load_cover_image)

    def refresh_images(self):
        """Refresh all visible widget images"""
        # Reload images for all visible widgets
        for row, widget in self._visible_widgets.items():
            # Use singleShot to prevent UI freezing
            QTimer.singleShot(0, widget.load_cover_image)
        
        # Also update visible items to catch any new widgets
        self.update_visible_items()