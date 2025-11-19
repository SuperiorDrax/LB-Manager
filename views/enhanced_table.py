from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtCore import Qt

class EnhancedTableWidget(QTableWidget):
    """
    Table widget with three-state sorting: none → ascending → descending → none
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Track sorting state for each column: "none", "asc", "desc"
        self.sort_states = {}
        self.current_sort_column = -1  # Currently sorted column index
        
        # Connect header click signal
        self.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
    
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