from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
import re

class TableController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.current_search_row = 0
        self.data = []
        self.websign_tracker = {}
    
    def add_to_table(self, data):
        """Add parsed data to table with tag support"""
        if len(data) == 7:
            author, title, group, show, magazine, origin, websign = data
            tag = ""
        else:
            author, title, group, show, magazine, origin, websign, tag = data

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
        
        # Set data in table - now 8 columns
        table.setItem(row_position, 0, websign_item)                 # websign
        table.setItem(row_position, 1, QTableWidgetItem(author))     # author
        table.setItem(row_position, 2, QTableWidgetItem(title))      # title
        table.setItem(row_position, 3, QTableWidgetItem(group))      # group
        table.setItem(row_position, 4, QTableWidgetItem(show))       # show
        table.setItem(row_position, 5, QTableWidgetItem(magazine))   # magazine
        table.setItem(row_position, 6, QTableWidgetItem(origin))     # origin
        table.setItem(row_position, 7, QTableWidgetItem(tag))        # tag

        if websign not in self.websign_tracker:
            self.websign_tracker[websign] = []
        self.websign_tracker[websign].append(row_position)

        if len(self.websign_tracker[websign]) > 1:
            self.highlight_duplicate_rows(websign)
    
    def search_next(self, options):
        """Search with multiple conditions"""
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
        """Filter table with multiple conditions"""
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
        
        rows_to_remove = []
        
        # Find rows that don't match the conditions
        for row in range(self.main_window.table.rowCount() - 1, -1, -1):
            item1 = self.main_window.table.item(row, col1_index)
            if not item1:
                rows_to_remove.append(row)
                continue
            
            # Single condition
            if match_func2 is None:
                if not match_func1(item1.text()):
                    rows_to_remove.append(row)
            # Multiple conditions
            else:
                item2 = self.main_window.table.item(row, col2_index)
                if not item2:
                    rows_to_remove.append(row)
                    continue
                
                condition1_matched = match_func1(item1.text())
                condition2_matched = match_func2(item2.text())
                
                if options['logic'] == 'AND':
                    if not (condition1_matched and condition2_matched):
                        rows_to_remove.append(row)
                else:  # OR logic
                    if not (condition1_matched or condition2_matched):
                        rows_to_remove.append(row)
        
        if len(rows_to_remove) == self.main_window.table.rowCount():
            QMessageBox.warning(self.main_window, "Filter", "Cannot find the specified text.")
            return
        
        # Remove rows that don't match
        for row in rows_to_remove:
            self.main_window.table.removeRow(row)
    
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