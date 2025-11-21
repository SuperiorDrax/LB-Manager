from PyQt6.QtWidgets import QTableWidget, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor

class CoverTooltip(QLabel):
    """Custom tooltip for displaying cover images"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            CoverTooltip {
                background-color: white;
                border: 2px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.setScaledContents(False)

class EnhancedTableWidget(QTableWidget):
    """
    Table widget with three-state sorting: none → ascending → descending → none
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Track sorting state for each column: "none", "asc", "desc"
        self.sort_states = {}
        self.current_sort_column = -1  # Currently sorted column index
        
        # Cover hover functionality
        self.cover_tooltip = CoverTooltip(self)
        self.cover_tooltip.hide()
        
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_cover_tooltip)
        self.last_hover_row = -1
        self.hover_delay = 500  # milliseconds
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Connect header click signal
        self.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

    def mouseMoveEvent(self, event):
        """Handle mouse move for cover hover"""
        # Get row under cursor
        row = self.rowAt(event.pos().y())
        
        if row != self.last_hover_row:
            # Hide tooltip if moved to different row
            self.cover_tooltip.hide()
            self.hover_timer.stop()
            self.last_hover_row = row
            
            if row >= 0:
                # Start timer for hover delay
                self.hover_timer.start(self.hover_delay)
        
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave table"""
        self.cover_tooltip.hide()
        self.hover_timer.stop()
        self.last_hover_row = -1
        super().leaveEvent(event)
    
    def show_cover_tooltip(self):
        """Show cover image tooltip for current hover row"""
        if self.last_hover_row < 0:
            return
        
        # Get main window reference
        main_window = self.parent().parent() if self.parent() else None
        if not main_window or not hasattr(main_window, 'web_controller'):
            return
        
        try:
            # Get websign from the row
            websign_item = self.item(self.last_hover_row, 0)
            if not websign_item:
                return
            
            websign = websign_item.data(Qt.ItemDataRole.UserRole)
            if not websign:
                websign = websign_item.text()
            
            if not websign:
                return
            
            # Get cover image through web controller
            cover_pixmap = main_window.web_controller.get_cover_image(websign)
            if cover_pixmap:
                # Set pixmap to custom tooltip
                self.cover_tooltip.setPixmap(cover_pixmap)
                
                # Calculate position (right side of cursor)
                cursor_pos = QCursor.pos()
                tooltip_x = cursor_pos.x() + 20
                tooltip_y = cursor_pos.y() - cover_pixmap.height() // 2
                
                # Ensure tooltip stays on screen
                screen_geometry = self.screen().availableGeometry()
                if tooltip_x + cover_pixmap.width() > screen_geometry.right():
                    tooltip_x = cursor_pos.x() - cover_pixmap.width() - 20
                if tooltip_y + cover_pixmap.height() > screen_geometry.bottom():
                    tooltip_y = screen_geometry.bottom() - cover_pixmap.height()
                if tooltip_y < screen_geometry.top():
                    tooltip_y = screen_geometry.top()
                
                # Show tooltip
                self.cover_tooltip.move(tooltip_x, tooltip_y)
                self.cover_tooltip.show()
                
        except Exception as e:
            print(f"Error showing cover tooltip: {e}")
    
    def on_header_clicked(self, logical_index):
        """
        Handle header click for three-state sorting
        State cycle: none → ascending → descending → none
        """
        # Get current state of clicked column
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
            # Clear sorting by setting sort indicator to -1
            self.clear_sort_indicator(column)
            # Reset table to unsorted state by sorting with no column
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
    
    def clear_sort_indicator(self, column):
        """
        Clear visual sort indicator for column
        Args:
            column: Column index
        """
        # Set indicator to non-existent column to clear visual indicator
        header = self.horizontalHeader()
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
    
    def clear_all_sorting(self):
        """Clear all sorting states and indicators"""
        self.sort_states.clear()
        self.current_sort_column = -1
        # Clear visual indicator
        self.clear_sort_indicator(-1)
        # Reset table to unsorted state
        self.sortByColumn(-1, Qt.SortOrder.AscendingOrder)

