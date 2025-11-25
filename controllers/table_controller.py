from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import re

class TableController(QObject):
    data_added = pyqtSignal()
    data_removed = pyqtSignal()
    filter_state_changed = pyqtSignal(bool)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.websign_tracker = {}
        self.is_filtered = False
        self.original_row_visibility = []

        self.current_search_row = -1
        self.last_search_options = None
    
    def add_to_table(self, data):
        """Add parsed data to table with tag support"""
        author, title, group, show, magazine, origin, websign, tag, read_status, progress = data

        table = self.main_window.table
        
        # Add new row
        row_position = table.rowCount()
        table.insertRow(row_position)
        
        # Create custom items for numeric sorting of websign
        websign_item = QTableWidgetItem()
        if websign and websign.isdigit():
            # Set numeric data for proper sorting
            websign_item.setData(Qt.ItemDataRole.DisplayRole, int(websign))
            websign_item.setData(Qt.ItemDataRole.UserRole, websign)  # Store original string
        else:
            websign_item.setText(websign)
        
        # Create read status item
        read_status_item = QTableWidgetItem(self.get_read_status_display(read_status))
        read_status_item.setData(Qt.ItemDataRole.UserRole, read_status)
        self.apply_read_status_style(read_status_item, read_status)
        
        # Create progress item
        progress_item = QTableWidgetItem(f"{progress}%")
        progress_item.setData(Qt.ItemDataRole.UserRole, progress)
        
        # Set data in table - now 8 columns
        table.setItem(row_position, 0, websign_item)                 # websign
        table.setItem(row_position, 1, QTableWidgetItem(author))     # author
        table.setItem(row_position, 2, QTableWidgetItem(title))      # title
        table.setItem(row_position, 3, QTableWidgetItem(group))      # group
        table.setItem(row_position, 4, QTableWidgetItem(show))       # show
        table.setItem(row_position, 5, QTableWidgetItem(magazine))   # magazine
        table.setItem(row_position, 6, QTableWidgetItem(origin))     # origin
        table.setItem(row_position, 7, QTableWidgetItem(tag))        # tag
        table.setItem(row_position, 8, read_status_item)             # read_status
        table.setItem(row_position, 9, progress_item)                # progress

        if websign not in self.websign_tracker:
            self.websign_tracker[websign] = []
        self.websign_tracker[websign].append(row_position)

        if len(self.websign_tracker[websign]) > 1:
            self.highlight_duplicate_rows(websign)
        
        self.data_added.emit()

    def apply_search_filter(self, options):
        """Apply search filter with undo capability"""
        # Save current visibility state (if it's the first filter)
        if not self.is_filtered:
            self.save_current_visibility()
        
        # Apply filter
        self.filter_table(options)
        self.is_filtered = True
        
        # Emit state change signal
        self.filter_state_changed.emit(True)
        self.update_search_button_state()

    def save_current_visibility(self):
        """Save current row visibility state"""
        self.original_row_visibility = []
        for row in range(self.main_window.table.rowCount()):
            self.original_row_visibility.append(not self.main_window.table.isRowHidden(row))

    def reset_search_filter(self):
        """Reset search filter to original state"""
        if self.is_filtered and self.original_row_visibility:
            # Restore original visibility state
            for row, visible in enumerate(self.original_row_visibility):
                self.main_window.table.setRowHidden(row, not visible)
        
        self.is_filtered = False
        self.original_row_visibility = []
        self.filter_state_changed.emit(False)
        self.update_search_button_state()

    def get_visible_row_count(self):
        """Calculate visible row count"""
        count = 0
        for row in range(self.main_window.table.rowCount()):
            if not self.main_window.table.isRowHidden(row):
                count += 1
        return count

    def update_search_button_state(self):
        """Update search button text and behavior based on filter state"""
        search_button = self.main_window.search_button
        
        try:
            search_button.clicked.disconnect()
        except:
            pass
        
        if self.is_filtered:
            visible_count = self.get_visible_row_count()
            search_button.setText(f"Show All ({visible_count} shown)")
            search_button.clicked.connect(self.reset_search_filter)
        else:
            search_button.setText("Search")
            search_button.clicked.connect(self.main_window.show_search_dialog)
    
    def search_next(self, options):
        """Search with multiple conditions"""
        if not hasattr(self, 'current_search_row'):
            self.current_search_row = -1

        if not options:
            return
        
        start_row = self.current_search_row
        row_count = self.main_window.table.rowCount()
        use_regex = options.get('use_regex', False)
        
        # Compile regex if enabled
        if use_regex:
            try:
                pattern1 = re.compile(options['condition1']['text'], re.IGNORECASE)
                match_func1 = lambda text: pattern1.search(text) is not None
                
                if 'condition2' in options:
                    pattern2 = re.compile(options['condition2']['text'], re.IGNORECASE)
                    match_func2 = lambda text: pattern2.search(text) is not None
                else:
                    match_func2 = None
                    
            except re.error as e:
                QMessageBox.warning(self.main_window, "Regex Error", 
                                f"Invalid regular expression:\n{str(e)}")
                return
        else:
            text1 = options['condition1']['text'].lower()
            match_func1 = lambda text: text1 in text.lower()
            
            if 'condition2' in options:
                text2 = options['condition2']['text'].lower()
                match_func2 = lambda text: text2 in text.lower()
            else:
                match_func2 = None
        
        # Get column indices
        column_mapping = {
            'websign': 0, 'author': 1, 'title': 2, 'group': 3,
            'show': 4, 'magazine': 5, 'origin': 6, 'tag': 7
        }
        
        col1_index = column_mapping[options['condition1']['column']]
        if 'condition2' in options:
            col2_index = column_mapping[options['condition2']['column']]
        
        # Search from current position
        for row in range(start_row, row_count):
            item1 = self.main_window.table.item(row, col1_index)
            if not item1:
                continue
            
            # Single condition
            if match_func2 is None:
                if match_func1(item1.text()):
                    self.main_window.table.selectRow(row)
                    self.current_search_row = row + 1
                    return
            # Multiple conditions
            else:
                item2 = self.main_window.table.item(row, col2_index)
                if not item2:
                    continue
                
                condition1_matched = match_func1(item1.text())
                condition2_matched = match_func2(item2.text())
                
                if options['logic'] == 'AND':
                    if condition1_matched and condition2_matched:
                        self.main_window.table.selectRow(row)
                        self.current_search_row = row + 1
                        return
                else:  # OR logic
                    if condition1_matched or condition2_matched:
                        self.main_window.table.selectRow(row)
                        self.current_search_row = row + 1
                        return
        
        # If not found, ask to search from beginning
        reply = QMessageBox.question(self.main_window, "Search", 
                                "Cannot find more occurrences. Search from the beginning?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.current_search_row = 0
            for row in range(row_count):
                item1 = self.main_window.table.item(row, col1_index)
                if not item1:
                    continue
                
                if match_func2 is None:
                    if match_func1(item1.text()):
                        self.main_window.table.selectRow(row)
                        self.current_search_row = row + 1
                        return
                else:
                    item2 = self.main_window.table.item(row, col2_index)
                    if not item2:
                        continue
                    
                    condition1_matched = match_func1(item1.text())
                    condition2_matched = match_func2(item2.text())
                    
                    if options['logic'] == 'AND':
                        if condition1_matched and condition2_matched:
                            self.main_window.table.selectRow(row)
                            self.current_search_row = row + 1
                            return
                    else:  # OR logic
                        if condition1_matched or condition2_matched:
                            self.main_window.table.selectRow(row)
                            self.current_search_row = row + 1
                            return
            
            QMessageBox.warning(self.main_window, "Search", "Cannot find the specified text.")
        else:
            self.current_search_row = 0

    def filter_table(self, options):
        """Filter table with multiple conditions - hide rows instead of deleting"""
        if not options:
            return
        
        use_regex = options.get('use_regex', False)
        
        # Compile regex if enabled
        if use_regex:
            try:
                pattern1 = re.compile(options['condition1']['text'], re.IGNORECASE)
                match_func1 = lambda text: pattern1.search(text) is not None
                
                if 'condition2' in options:
                    pattern2 = re.compile(options['condition2']['text'], re.IGNORECASE)
                    match_func2 = lambda text: pattern2.search(text) is not None
                else:
                    match_func2 = None
                    
            except re.error as e:
                QMessageBox.warning(self.main_window, "Regex Error", 
                                f"Invalid regular expression:\n{str(e)}")
                return
        else:
            text1 = options['condition1']['text'].lower()
            match_func1 = lambda text: text1 in text.lower()
            
            if 'condition2' in options:
                text2 = options['condition2']['text'].lower()
                match_func2 = lambda text: text2 in text.lower()
            else:
                match_func2 = None
        
        # Get column indices
        column_mapping = {
            'websign': 0, 'author': 1, 'title': 2, 'group': 3,
            'show': 4, 'magazine': 5, 'origin': 6, 'tag': 7
        }
        
        col1_index = column_mapping[options['condition1']['column']]
        if 'condition2' in options:
            col2_index = column_mapping[options['condition2']['column']]
        
        # Hide rows that don't match the conditions instead of deleting
        visible_count = 0
        for row in range(self.main_window.table.rowCount()):
            item1 = self.main_window.table.item(row, col1_index)
            if not item1:
                self.main_window.table.setRowHidden(row, True)
                continue
            
            # Single condition
            if match_func2 is None:
                if match_func1(item1.text()):
                    self.main_window.table.setRowHidden(row, False)
                    visible_count += 1
                else:
                    self.main_window.table.setRowHidden(row, True)
            # Multiple conditions
            else:
                item2 = self.main_window.table.item(row, col2_index)
                if not item2:
                    self.main_window.table.setRowHidden(row, True)
                    continue
                
                condition1_matched = match_func1(item1.text())
                condition2_matched = match_func2(item2.text())
                
                if options['logic'] == 'AND':
                    if condition1_matched and condition2_matched:
                        self.main_window.table.setRowHidden(row, False)
                        visible_count += 1
                    else:
                        self.main_window.table.setRowHidden(row, True)
                else:  # OR logic
                    if condition1_matched or condition2_matched:
                        self.main_window.table.setRowHidden(row, False)
                        visible_count += 1
                    else:
                        self.main_window.table.setRowHidden(row, True)
        
        if visible_count == 0:
            QMessageBox.warning(self.main_window, "Filter", "Cannot find the specified text.")
    
    def highlight_duplicate_rows(self, websign):
        """Highlight all rows with duplicate websign with light red background"""
        if websign in self.websign_tracker:
            duplicate_color = QColor(255, 230, 230)  # Light red
            for row in self.websign_tracker[websign]:
                for col in range(self.main_window.table.columnCount()):
                    item = self.main_window.table.item(row, col)
                    if item:
                        item.setBackground(duplicate_color)

    def reapply_duplicate_highlighting(self):
        """Re-apply duplicate highlighting while preserving alternating row colors"""
        # Clear all backgrounds and let Qt handle alternating colors
        for row in range(self.main_window.table.rowCount()):
            for col in range(self.main_window.table.columnCount()):
                item = self.main_window.table.item(row, col)
                if item:
                    # Clear background to let Qt's alternating colors take effect
                    item.setBackground(QBrush())  # Clear brush
        
        # Force Qt to recalculate alternating colors
        self.main_window.table.setAlternatingRowColors(False)
        self.main_window.table.setAlternatingRowColors(True)
        
        # Then apply highlighting for duplicates (will override for duplicate rows only)
        for websign, rows in self.websign_tracker.items():
            if len(rows) > 1:
                self.highlight_duplicate_rows(websign)

    def show_duplicate_warning(self, websign, duplicate_rows):
        """Show warning for duplicate websign"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Duplicate Websign Detected")
        msg.setText(f"Websign '{websign}' already exists in the table.")
        msg.setInformativeText(f"Found at row(s): {', '.join(str(r+1) for r in duplicate_rows)}\n\nDo you want to add this duplicate entry?")
        
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.YesToAll
        )
        
        return msg.exec()

    def rebuild_websign_tracker(self):
        """Rebuild websign tracker from current table data and update highlighting"""
        self.websign_tracker.clear()
        
        # Build new tracker
        for row in range(self.main_window.table.rowCount()):
            websign_item = self.main_window.table.item(row, 0)
            if websign_item and websign_item.text():
                websign = websign_item.text()
                if websign not in self.websign_tracker:
                    self.websign_tracker[websign] = []
                self.websign_tracker[websign].append(row)
        
        # Re-apply highlighting (this will now preserve alternating colors)
        self.reapply_duplicate_highlighting()

    def on_row_removed(self, deleted_row):
        """Update websign tracker and other data when row is removed"""
        # Rebuild the entire websign tracker since row indices change
        self.rebuild_websign_tracker()
    
    def update_progress(self, row, progress):
        """Update progress for specified row"""
        try:
            progress_item = self.main_window.table.item(row, 9)
            if progress_item:
                progress = max(0, min(100, progress))  # Clamp between 0-100
                progress_item.setText(f"{progress}%")
                progress_item.setData(Qt.ItemDataRole.UserRole, progress)
                
                # Auto-update read status based on progress
                read_status_item = self.main_window.table.item(row, 8)
                if read_status_item:
                    if progress == 0:
                        new_status = "unread"
                    elif progress == 100:
                        new_status = "completed"
                    else:
                        new_status = "reading"
                    
                    read_status_item.setData(Qt.ItemDataRole.UserRole, new_status)
                    read_status_item.setText(self.get_read_status_display(new_status))
                    self.apply_read_status_style(read_status_item, new_status)
                    
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    def get_read_status_display(self, status):
        """Convert status to display text"""
        status_map = {
            "unread": "Unread",
            "reading": "Reading", 
            "completed": "Completed"
        }
        return status_map.get(status, "Unread")

    def apply_read_status_style(self, item, status):
        """Apply styling based on read status"""
        if status == "completed":
            item.setBackground(QColor(220, 255, 220))  # Light green
            item.setForeground(QColor(0, 100, 0))      # Dark green text
        elif status == "reading":
            item.setBackground(QColor(255, 255, 200))  # Light yellow
            item.setForeground(QColor(140, 100, 0))    # Dark yellow text
        else:  # unread
            item.setBackground(QColor(255, 220, 220))  # Light red
            item.setForeground(QColor(100, 0, 0))      # Dark red text