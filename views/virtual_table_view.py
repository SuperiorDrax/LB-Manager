"""
Virtual Table View optimized for large datasets
Replaces EnhancedTableWidget with QTableView + VirtualDataModel
"""
from PyQt6.QtWidgets import QTableView, QHeaderView, QMenu, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QModelIndex
from PyQt6.QtGui import QAction
from models.virtual_data_model import VirtualDataModel
import time


class VirtualTableView(QTableView):
    """
    Virtual table view with three-state sorting and full compatibility
    with existing architecture components
    """
    
    # Signals for compatibility with existing code
    itemSelectionChanged = pyqtSignal()  # Compat with QTableWidget signal
    doubleClicked = pyqtSignal(QModelIndex)  # Compat signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize data model
        self.data_model = VirtualDataModel()
        self.setModel(self.data_model)
        
        # Sorting state tracking
        self.sort_states = {}  # column_index -> "none", "asc", "desc"
        self.current_sort_column = -1
        
        # Selection tracking
        self.last_selection_time = 0
        self.selection_debounce_timer = QTimer()
        self.selection_debounce_timer.setSingleShot(True)
        self.selection_debounce_timer.timeout.connect(self._emit_selection_changed)
        
        # Initialize UI
        self.init_ui()
        
        # Connect signals
        self.connect_signals()
    
    def init_ui(self):
        """Initialize table view UI with compatibility features"""
        # Set table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.setSortingEnabled(True)
        
        # Configure header
        header = self.horizontalHeader()
        header.setSectionsMovable(True)  # Allow column reordering
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.setStretchLastSection(False)
        
        # Set default column widths from model
        for i, col_def in enumerate(self.data_model.COLUMNS):
            self.setColumnWidth(i, col_def.get('width', 100))
        
        # Configure vertical header
        vertical_header = self.verticalHeader()
        vertical_header.setDefaultSectionSize(24)
        vertical_header.setVisible(True)
        
        # Set style
        self.setStyleSheet("""
            QTableView {
                gridline-color: #dee2e6;
                background-color: white;
            }
            QTableView::item {
                padding: 4px;
            }
            QTableView::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
        """)
    
    def connect_signals(self):
        """Connect signals for compatibility"""
        # Connect header signals
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
        self.horizontalHeader().sectionResized.connect(self.on_column_resized)
        self.horizontalHeader().sectionMoved.connect(self.on_column_moved)
        
        # Connect selection change with debouncing
        self.selectionModel().selectionChanged.connect(self._on_selection_changed_debounced)
        
        # Connect double click
        self.doubleClicked.connect(self._handle_double_click)
    
    # ==================== Data Management (Compatibility Layer) ====================
    
    def setColumnCount(self, count: int):
        """Compatibility method - column count is managed by model"""
        # Column count is fixed by model, this is a no-op for compatibility
        pass
    
    def setHorizontalHeaderLabels(self, labels):
        """Compatibility method - header labels are managed by model"""
        # Header labels are managed by model, this is a no-op for compatibility
        pass
    
    def rowCount(self):
        """Get visible row count from virtual model"""
        return self.data_model.rowCount()
    
    def columnCount(self):
        """Compatibility method - get column count"""
        return self.data_model.columnCount()
    
    def setRowCount(self, count):
        """Compatibility method - rows are managed by model"""
        if count == 0:
            self.clear()
    
    def clear(self):
        """Clear all data from table"""
        self.data_model.clear_all_data()
    
    def insertRow(self, row):
        """Compatibility method - use add_row_data instead"""
        # This is a simplified compatibility method
        # Actual insertion should use add_row_data
        pass
    
    # ==================== Sorting Implementation ====================
    
    def on_header_clicked(self, logical_index):
        """
        Handle header click for three-state sorting
        State cycle: none → ascending → descending → none
        """
        current_state = self.sort_states.get(logical_index, "none")
        
        # Determine next state in cycle
        if current_state == "none":
            new_state = "asc"
        elif current_state == "asc":
            new_state = "desc"
        else:  # "desc"
            new_state = "none"
        
        # Apply the new sorting state
        self.apply_sort(logical_index, new_state)
    
    def apply_sort(self, column, sort_state):
        """
        Apply sorting state to specified column
        Args:
            column: Column index to sort
            sort_state: One of "none", "asc", "desc"
        """
        # Clear previous column's visual indicator if switching columns
        if self.current_sort_column != column and self.current_sort_column >= 0:
            self.clear_sort_indicator(self.current_sort_column)
        
        # Update current column and state
        self.current_sort_column = column
        self.sort_states[column] = sort_state
        
        if sort_state == "none":
            # Clear sorting
            self.clear_sort_indicator(column)
            # Note: QTableView handles sorting automatically
            self.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        elif sort_state == "asc":
            # Sort ascending
            self.sortByColumn(column, Qt.SortOrder.AscendingOrder)
            self.set_sort_indicator(column, True)
        else:  # "desc"
            # Sort descending
            self.sortByColumn(column, Qt.SortOrder.DescendingOrder)
            self.set_sort_indicator(column, False)
    
    def set_sort_indicator(self, column, ascending):
        """
        Set visual sort indicator in header
        Args:
            column: Column index
            ascending: True for ascending, False for descending
        """
        header = self.horizontalHeader()
        sort_order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder
        header.setSortIndicator(column, sort_order)
        header.setSortIndicatorShown(True)
    
    def clear_sort_indicator(self, column):
        """
        Clear visual sort indicator for column
        Args:
            column: Column index
        """
        header = self.horizontalHeader()
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
    
    def clear_all_sorting(self):
        """Clear all sorting states and indicators"""
        self.sort_states.clear()
        self.current_sort_column = -1
        self.clear_sort_indicator(-1)
        self.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
    
    # ==================== Selection Handling ====================
    
    def _on_selection_changed_debounced(self, selected, deselected):
        """Debounced selection change handler"""
        current_time = time.time()
        
        # If selection changed very recently, restart timer
        if current_time - self.last_selection_time < 0.1:
            self.selection_debounce_timer.stop()
        
        self.selection_debounce_timer.start(50)  # 50ms debounce
        self.last_selection_time = current_time
    
    def _emit_selection_changed(self):
        """Emit selection changed signal after debouncing"""
        self.itemSelectionChanged.emit()
    
    def _handle_double_click(self, index):
        """Handle double click event"""
        self.doubleClicked.emit(index)
    
    def get_selected_rows(self):
        """
        Get all selected row indices
        
        Returns:
            List[int]: List of selected row indices (sorted)
        """
        selected_rows = set()
        selection_model = self.selectionModel()
        
        if not selection_model:
            return []
        
        # Get selected indexes
        selected_indexes = selection_model.selectedRows()
        
        for index in selected_indexes:
            if index.isValid():
                selected_rows.add(index.row())
        
        # Also check for row selections (when entire row is selected)
        selected_ranges = selection_model.selection()
        for range_ in selected_ranges:
            top = range_.top()
            bottom = range_.bottom()
            for row in range(top, bottom + 1):
                selected_rows.add(row)
        
        return sorted(list(selected_rows))
    
    def selectRow(self, row):
        """Select a specific row"""
        if 0 <= row < self.data_model.rowCount():
            index = self.model().index(row, 0)
            self.selectionModel().select(
                index,
                self.selectionModel().SelectionFlag.Select | self.selectionModel().SelectionFlag.Rows
            )
    
    # ==================== Header Context Menu ====================
    
    def show_header_context_menu(self, position):
        """Show right-click menu for column headers"""
        menu = QMenu(self)
        
        # Add column visibility controls
        for i, col_def in enumerate(self.data_model.COLUMNS):
            action = menu.addAction(col_def['display'])
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.triggered.connect(lambda checked, idx=i: self.toggle_column_visibility(idx, checked))
        
        # Show menu at cursor position
        menu.exec(self.horizontalHeader().mapToGlobal(position))
    
    def toggle_column_visibility(self, column_index, visible):
        """Toggle visibility of a specific column"""
        self.setColumnHidden(column_index, not visible)
    
    # ==================== State Management Integration ====================
    
    def on_column_resized(self, logical_index, old_size, new_size):
        """Handle column resize for state manager"""
        # This signal will be connected to state_manager.on_column_resized
        if hasattr(self.parent(), 'state_manager'):
            self.parent().state_manager.on_column_resized(logical_index, old_size, new_size)
    
    def on_column_moved(self, logical_index, old_visual_index, new_visual_index):
        """Handle column move for state manager"""
        # This signal will be connected to state_manager.on_column_moved
        if hasattr(self.parent(), 'state_manager'):
            self.parent().state_manager.on_column_moved(logical_index, old_visual_index, new_visual_index)
    
    # ==================== Filter Integration ====================
    
    def apply_status_filter(self, status):
        """Apply status filter to table"""
        self.data_model.set_status_filter(status)
    
    def apply_tag_filter(self, selected_tags):
        """Apply tag filter to table"""
        self.data_model.set_tag_filter(selected_tags)
    
    def reset_table_filter(self):
        """Reset table filter to show all rows"""
        self.data_model.clear_filters()
    
    def update_sidebar_counts(self):
        """Update sidebar counts - compatibility method"""
        # This will be implemented when integrating with main_window
        pass
    
    # ==================== Data Access (Compatibility Methods) ====================
    
    def item(self, row, column):
        """
        Minimal compatibility method - returns None
        
        Note: In virtual model, data should be accessed through model.data()
        This method exists only to prevent crashes in existing code.
        """
        return None  # Force code to use model.data() instead
    
    def setItem(self, row, column, item):
        """
        Compatibility method - data should be set through model.setData()
        
        Note: This method does nothing in virtual model.
        Data must be updated through model.setData() or model.update_row()
        """
        # No-op - data must be updated through model
        pass
    
    def isRowHidden(self, row):
        """
        Compatibility method - rows are filtered at model level in virtual model
        
        Note: In virtual model, filtered rows are not in the visible rows list at all.
        So if the row index is within range, it's visible.
        """
        if row < 0 or row >= self.data_model.rowCount():
            return True  # Out of range rows are "hidden"
        return False  # All rows in range are visible in virtual model
    
    def setRowHidden(self, row, hide):
        """
        Compatibility method - rows are filtered at model level
        """
        # Rows are filtered at model level, not view level
        pass
    
    # ==================== Performance Methods ====================
    
    def setUpdatesEnabled(self, enabled):
        """
        Enable/disable UI updates for batch operations
        """
        super().setUpdatesEnabled(enabled)
        if enabled:
            self.viewport().update()
    
    def get_performance_stats(self):
        """Get performance statistics"""
        return self.data_model.get_performance_stats()
    
    # ==================== Public API for Controllers ====================
    
    def add_row_data(self, data_tuple):
        """
        Add row data to the model
        Args:
            data_tuple: Tuple of 11 values in correct column order
        """
        # Convert tuple to dict for model
        data_dict = {}
        for i, col_def in enumerate(self.data_model.COLUMNS):
            if i < len(data_tuple):
                data_dict[col_def['name']] = data_tuple[i]
        
        self.data_model.add_row(data_dict)
    
    def add_rows_data(self, rows_data):
        """
        Add multiple rows to the model efficiently
        Args:
            rows_data: List of tuples, each with 11 values
        """
        data_dicts = []
        for data_tuple in rows_data:
            data_dict = {}
            for i, col_def in enumerate(self.data_model.COLUMNS):
                if i < len(data_tuple):
                    data_dict[col_def['name']] = data_tuple[i]
            data_dicts.append(data_dict)
        
        self.data_model.add_rows(data_dicts)
    
    def get_model(self):
        """Get the data model"""
        return self.data_model

    def sync_selection_with_grid(self, grid_selected_rows):
        """
        Sync selection with grid view selections
        
        Args:
            grid_selected_rows: Set of row indices selected in grid view
        """
        selection_model = self.selectionModel()
        if not selection_model:
            return
        
        # Clear current selection
        selection_model.clearSelection()
        
        # Select rows that are selected in grid
        for row in grid_selected_rows:
            if 0 <= row < self.data_model.rowCount():
                index = self.model().index(row, 0)
                selection_model.select(
                    index,
                    self.selectionModel().SelectionFlag.Select | 
                    self.selectionModel().SelectionFlag.Rows
                )