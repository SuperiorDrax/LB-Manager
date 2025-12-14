"""
Paged virtual grid view with fixed number of items per page
Maintains virtualization benefits while providing page navigation
"""
from PyQt6.QtWidgets import (
    QListView, QAbstractItemView, QApplication, QFrame, 
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QRect, QModelIndex
from PyQt6.QtGui import QPalette
import time
from .comic_card_delegate import ComicCardDelegate
from .virtual_grid_view import VirtualGridView


class PagedVirtualGridView(QWidget):
    """Paged virtual grid view with page navigation controls"""
    
    # Signals
    page_changed = pyqtSignal(int, int)  # current_page, total_pages
    selection_changed = pyqtSignal()
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        # Page configuration
        self.items_per_page = 20
        self.current_page = 0
        self.total_pages = 0
        
        # Current visible rows in the model
        self._visible_rows = []
        
        # Initialize UI
        self.init_ui()
        
        # Performance monitoring
        self._performance_stats = {
            'items_loaded': 0,
            'page_load_time': 0,
            'cache_hits': 0
        }
        
    def init_ui(self):
        """Initialize the paged grid view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create the virtual grid view (reusing existing VirtualGridView)
        self.grid_view = VirtualGridView(self.main_window)
        self.grid_view.setSpacing(15)
        self.grid_view.setGridSize(QSize(140, 250))
        QTimer.singleShot(0, self._connect_grid_signals)
        
        layout.addWidget(self.grid_view)
        
        # Create pagination controls
        self.create_pagination_controls()
        layout.addWidget(self.pagination_widget)
        
        self.setLayout(layout)

    def _connect_grid_signals(self):
        """Connect grid_view signals"""
        if self.grid_view.selectionModel():
            self.grid_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.grid_view.doubleClicked.connect(self.on_item_double_clicked)
        
    def create_pagination_controls(self):
        """Create pagination control widgets"""
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(10, 5, 10, 5)
        
        # Previous page button
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        
        # Page info label
        self.page_label = QLabel("Page 1 of 1")
        
        # Next page button
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        # Items per page selector (optional)
        self.page_size_label = QLabel("Items per page:")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "30", "50"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_size_label)
        pagination_layout.addWidget(self.page_size_combo)
        
        self.pagination_widget.setLayout(pagination_layout)
        
    def set_main_window_model(self):
        """Set model and connect to data change signals"""
        if hasattr(self.main_window, 'table') and hasattr(self.main_window.table, 'get_model'):
            model = self.main_window.table.get_model()
            if model:
                # Store reference to full model
                self.full_model = model
                
                # Set model to inner grid view
                self.grid_view.setModel(model)
                
                # Connect to model signals for automatic updates
                model.dataChanged.connect(self._on_model_data_changed)
                model.layoutChanged.connect(self._on_model_layout_changed)
                
                # Initialize pagination
                self.update_page_model()
                
                print(f"[PagedVirtualGridView] Model set with {model.rowCount()} rows")

    def _on_model_data_changed(self, topLeft, bottomRight, roles):
        """Handle model data changes - update pagination"""
        self.update_page_model()
        
    def _on_model_layout_changed(self):
        """Handle model layout changes - update pagination"""
        self.update_page_model()
                
    def update_page_model(self):
        """Update pagination based on current model state"""
        if not hasattr(self, 'full_model') or not self.full_model:
            return
            
        total_rows = self.full_model.rowCount()
        
        if total_rows > 0:
            # Calculate page range
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, total_rows)
            
            # Store visible rows for this page
            self._visible_rows = list(range(start_idx, end_idx))
            
            # Update pagination info
            self.total_pages = max(1, (total_rows + self.items_per_page - 1) // self.items_per_page)
            
            print(f"[PagedVirtualGridView] Page {self.current_page + 1}/{self.total_pages}, " 
                f"showing rows {start_idx}-{end_idx}")
        else:
            # Handle empty model
            self._visible_rows = []
            self.total_pages = 1
            
        # Update UI display
        self.update_pagination_display()
        
        # Notify page change
        self.page_changed.emit(self.current_page, self.total_pages)
        
    def update_pagination_display(self):
        """Update pagination controls display"""
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)
        
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_model()
            
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_model()
            
    def on_page_size_changed(self, new_size):
        """Handle page size change"""
        try:
            self.items_per_page = int(new_size)
            self.current_page = 0  # Reset to first page
            self.update_page_model()
        except ValueError:
            pass
            
    def on_selection_changed(self, selected, deselected):
        """Handle selection changes from grid view"""
        self.selection_changed.emit()
        
    def on_item_double_clicked(self, index):
        """Handle double click - translate to full model index"""
        if not index.isValid():
            return
            
        # Get actual row in full model
        visible_row = index.row()
        if 0 <= visible_row < len(self._visible_rows):
            actual_row = self._visible_rows[visible_row]
            
            # Create index in full model
            if hasattr(self.main_window, 'table') and hasattr(self.main_window.table, 'get_model'):
                model = self.main_window.table.get_model()
                full_index = model.index(actual_row, 0)
                self.main_window.on_table_double_click(full_index)
                
    def get_selected_rows(self):
        """
        Get selected rows in full model coordinates
        
        Returns:
            List[int]: List of selected row indices in full model
        """
        selected_indexes = self.grid_view.selectedIndexes()
        selected_rows = []
        
        for index in selected_indexes:
            if index.isValid():
                visible_row = index.row()
                if 0 <= visible_row < len(self._visible_rows):
                    selected_rows.append(self._visible_rows[visible_row])
                    
        return sorted(list(set(selected_rows)))
        
    def sync_selection_with_grid(self, selected_rows_set):
        """
        Sync selection from other view
        
        Args:
            selected_rows_set: Set of row indices in full model to select
        """
        self.grid_view.selectionModel().clearSelection()
        
        # Convert full model rows to visible rows
        visible_selections = []
        for full_row in selected_rows_set:
            if full_row in self._visible_rows:
                visible_row = self._visible_rows.index(full_row)
                visible_selections.append(visible_row)
                
        # Select in grid view
        model = self.grid_view.model()
        if model:
            for visible_row in visible_selections:
                index = model.index(visible_row, 0)
                self.grid_view.selectionModel().select(
                    index, 
                    self.grid_view.selectionModel().SelectionFlag.Select
                )
                
    def refresh_page(self):
        """Refresh current page"""
        self.update_page_model()
        
    def get_performance_stats(self):
        """Get performance statistics"""
        return self._performance_stats.copy()