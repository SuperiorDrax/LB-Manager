from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import re
import os

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
        """
        Add parsed data to virtual table and track duplicates
        
        Args:
            data: Tuple with 7, 8, 10, or 11 parameters
        """
        # Get virtual model from main window
        if not hasattr(self.main_window.table, 'get_model'):
            print("Error: Virtual model not available")
            return
        
        model = self.main_window.table.get_model()
        
        # Process data based on parameter count
        processed_data = self._process_input_data(data)
        if not processed_data:
            print(f"Warning: Failed to process data with {len(data)} elements")
            return
        
        # Check for duplicate before adding
        websign = processed_data.get('websign', '')
        
        if websign and websign in self.websign_tracker:
            # Show warning for duplicate
            duplicate_rows = self.websign_tracker[websign]
            response = self.show_duplicate_warning(websign, duplicate_rows)
            
            if response == QMessageBox.StandardButton.No:
                return  # Don't add duplicate
            elif response == QMessageBox.StandardButton.YesToAll:
                # Add all duplicates without asking
                pass
        
        # Add to virtual model
        model.add_row(processed_data)
        
        # Get the new row's visible index (last row)
        new_visible_row = model.rowCount() - 1
        
        # Update websign tracker
        if websign:
            if websign not in self.websign_tracker:
                self.websign_tracker[websign] = []
            self.websign_tracker[websign].append(new_visible_row)
            
            # Highlight if duplicate
            if len(self.websign_tracker[websign]) > 1:
                self.highlight_duplicate_rows(websign)
        
        # Emit data added signal
        self.data_added.emit()
        
        print(f"Added row with websign: {websign}, total rows: {model.get_total_rows()}")

    def _process_input_data(self, data):
        """
        Process input data tuple into dictionary for virtual model
        
        Args:
            data: Input tuple with variable length
        
        Returns:
            dict: Processed data dictionary
        """
        # Handle variable parameter count with defaults
        if len(data) == 7:
            # Format: author, title, group, show, magazine, origin, websign
            author, title, group, show, magazine, origin, websign = data
            tag = ""
            read_status = "unread"
            progress = 0
            file_path = ""
        elif len(data) == 8:
            # Format: author, title, group, show, magazine, origin, websign, tag
            author, title, group, show, magazine, origin, websign, tag = data
            read_status = "unread"
            progress = 0
            file_path = ""
        elif len(data) == 10:
            # Full format: author, title, group, show, magazine, origin, websign, tag, read_status, progress
            author, title, group, show, magazine, origin, websign, tag, read_status, progress = data
            file_path = ""
        elif len(data) == 11:
            # Full format with file path
            author, title, group, show, magazine, origin, websign, tag, read_status, progress, file_path = data
        else:
            print(f"Warning: Unexpected data length: {len(data)} elements")
            return None
        
        # Process file path
        processed_file_path = self.process_file_path(websign, file_path)
        
        # Return dictionary compatible with VirtualDataModel
        return {
            'websign': websign,
            'author': author,
            'title': title,
            'group': group,
            'show': show,
            'magazine': magazine,
            'origin': origin,
            'tag': tag,
            'read_status': read_status,
            'progress': progress,
            'file_path': processed_file_path
        }

    def process_file_path(self, websign, original_file_path):
        """
        Process file path: convert to relative, validate, search if needed
        Returns processed relative file path or empty string
        """
        # Get lib_path from web_controller
        lib_path = self.main_window.web_controller.lib_path_value
        
        if not lib_path:
            # No library path set, cannot process
            return original_file_path  # Return as is
        
        # If original file path is provided
        if original_file_path and original_file_path.strip():
            return self._validate_and_convert_path(websign, original_file_path.strip(), lib_path)
        else:
            # No file path provided, search for it
            return self._search_for_file(websign, lib_path)

    def _validate_and_convert_path(self, websign, file_path, lib_path):
        """Validate file path and convert to relative if needed"""
        # Check if it's absolute or relative
        if os.path.isabs(file_path):
            # Convert absolute path to relative path
            try:
                relative_path = os.path.relpath(file_path, lib_path)
                # Check if the file exists
                if os.path.exists(file_path):
                    return relative_path
                else:
                    # File doesn't exist, ask user
                    return self._handle_missing_file_batch(websign, file_path, lib_path)
            except ValueError:
                # Paths are on different drives, cannot make relative
                return self._handle_missing_file_batch(websign, file_path, lib_path)
        else:
            # Already relative path
            full_path = os.path.join(lib_path, file_path)
            if os.path.exists(full_path):
                return file_path
            else:
                return self._handle_missing_file_batch(websign, full_path, lib_path)

    def _search_for_file(self, websign, lib_path):
        """Search for ZIP file by websign in library directory"""
        from utils.file_locator import FileLocator
        
        try:
            locator = FileLocator(max_depth=3)
            found_path = locator.find_zip_by_websign(websign, lib_path)
            
            if found_path:
                # Convert to relative path
                relative_path = os.path.relpath(found_path, lib_path)
                return relative_path
            else:
                return ""  # Not found
        except Exception as e:
            print(f"Error searching for file {websign}: {e}")
            return ""

    def _handle_missing_file_batch(self, websign, expected_path, lib_path):
        """
        Handle missing file in batch mode - always search
        (For interactive mode, would show dialog)
        """
        # In batch import, always try to search for the file
        return self._search_for_file(websign, lib_path)

    def apply_search_filter(self, options):
        """
        Apply search filter using virtual model's capabilities
        
        Args:
            options: Search options dictionary
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        # Note: VirtualDataModel currently doesn't have text search filters
        # We need to implement this or use a different approach
        
        # For now, save current state and apply basic filter
        if not self.is_filtered:
            self.save_current_visibility()
        
        # Apply filter using virtual model if possible
        self._apply_virtual_filter(options)
        self.is_filtered = True
        
        # Emit state change signal
        self.filter_state_changed.emit(True)
        self.update_search_button_state()

    def _apply_virtual_filter(self, options):
        """
        Apply filter using virtual model's capabilities - Complete implementation
        
        Args:
            options: Search options dictionary
        """
        if not options:
            return
        
        # Get virtual model
        if not hasattr(self.main_window.table, 'get_model'):
            print("Error: Virtual model not available")
            return
        
        model = self.main_window.table.get_model()
        
        # Extract search parameters
        condition1 = options.get('condition1', {})
        condition2 = options.get('condition2')
        logic = options.get('logic', 'AND').upper()
        use_regex = options.get('use_regex', False)
        case_sensitive = options.get('case_sensitive', False)
        
        # Validate conditions
        if not condition1 or 'column' not in condition1 or 'text' not in condition1:
            print("Error: Invalid condition1 in filter options")
            return
        
        # Get column indices
        column_mapping = {
            'websign': 0, 'author': 1, 'title': 2, 'group': 3,
            'show': 4, 'magazine': 5, 'origin': 6, 'tag': 7
        }
        
        col1_name = condition1['column']
        search_text1 = condition1['text']
        
        if col1_name not in column_mapping:
            print(f"Error: Invalid column name '{col1_name}'")
            return
        
        col1_index = column_mapping[col1_name]
        
        if condition2:
            col2_name = condition2.get('column')
            search_text2 = condition2.get('text')
            
            if not col2_name or not search_text2 or col2_name not in column_mapping:
                condition2 = None  # Invalid second condition
            else:
                col2_index = column_mapping[col2_name]
        
        # Create custom filter function
        def text_filter(row_tuple, row_index):
            """Filter function that works with tuples directly - more efficient"""
            try:
                # Get value from column 1 using column index (NO DICT CONVERSION)
                if col1_index < len(row_tuple):
                    cell_value1 = row_tuple[col1_index]
                    cell_value1 = str(cell_value1) if cell_value1 is not None else ""
                else:
                    return False
                
                # If search text is empty, match everything
                if not search_text1:
                    matches_cond1 = True
                else:
                    # Prepare search text
                    if not case_sensitive:
                        cell_value1_lower = cell_value1.lower()
                        search_text1_lower = search_text1.lower()
                    else:
                        cell_value1_lower = cell_value1
                        search_text1_lower = search_text1
                    
                    # Check first condition
                    if use_regex:
                        import re
                        try:
                            pattern1 = re.compile(search_text1_lower, 0 if case_sensitive else re.IGNORECASE)
                            matches_cond1 = pattern1.search(cell_value1_lower) is not None
                        except re.error:
                            # Invalid regex, fall back to substring
                            matches_cond1 = search_text1_lower in cell_value1_lower
                    else:
                        matches_cond1 = search_text1_lower in cell_value1_lower
                
                # Check second condition if present
                if condition2:
                    if col2_index < len(row_tuple):
                        cell_value2 = row_tuple[col2_index]
                        cell_value2 = str(cell_value2) if cell_value2 is not None else ""
                    else:
                        return False
                    
                    # If search text is empty, match everything
                    if not search_text2:
                        matches_cond2 = True
                    else:
                        if not case_sensitive:
                            cell_value2_lower = cell_value2.lower()
                            search_text2_lower = search_text2.lower()
                        else:
                            cell_value2_lower = cell_value2
                            search_text2_lower = search_text2
                        
                        if use_regex:
                            import re
                            try:
                                pattern2 = re.compile(search_text2_lower, 0 if case_sensitive else re.IGNORECASE)
                                matches_cond2 = pattern2.search(cell_value2_lower) is not None
                            except re.error:
                                matches_cond2 = search_text2_lower in cell_value2_lower
                        else:
                            matches_cond2 = search_text2_lower in cell_value2_lower
                    
                    # Apply logic
                    if logic == 'AND':
                        return matches_cond1 and matches_cond2
                    else:  # OR
                        return matches_cond1 or matches_cond2
                else:
                    return matches_cond1
                    
            except Exception as e:
                print(f"Error in filter function: {e}")
        
        # Apply the filter
        if hasattr(model, 'apply_advanced_filter'):
            model.apply_advanced_filter(text_filter)
            self.is_filtered = True
            
            visible_count = model.rowCount()
            total_count = model.get_total_rows() if hasattr(model, 'get_total_rows') else 0
            
            print(f"Applied text filter: {visible_count}/{total_count} rows visible")
            print(f"  Condition1: {col1_name} contains '{search_text1}'")
            if condition2:
                print(f"  Condition2: {col2_name} contains '{search_text2}'")
                print(f"  Logic: {logic}")
            print(f"  Regex: {use_regex}, Case-sensitive: {case_sensitive}")
        else:
            print("Error: Model doesn't support advanced filtering")
            QMessageBox.warning(self.main_window, "Filter Error", 
                            "The data model doesn't support text filtering.")

    def save_current_visibility(self):
        """
        Save current visibility state for undo capability
        
        Note: In virtual model, we save the current visible row indices
        """
        if not hasattr(self.main_window.table, 'get_model'):
            self.original_row_visibility = []
            return
        
        model = self.main_window.table.get_model()
        
        # Save current visible rows
        self.original_row_visibility = model.get_visible_rows().copy()
        
        print(f"Saved visibility state: {len(self.original_row_visibility)} visible rows")

    def reset_search_filter(self):
        """
        Reset search filter using virtual model capabilities
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        model = self.main_window.table.get_model()
        
        if self.is_filtered:
            # Clear all filters in virtual model
            model.clear_filters()
            
            # Clear text filter if supported
            if hasattr(model, 'clear_text_filter'):
                model.clear_text_filter()
            
            # Clear advanced filter if supported
            if hasattr(model, 'clear_advanced_filter'):
                model.clear_advanced_filter()
            
            print("Cleared all filters")
        
        self.is_filtered = False
        self.original_row_visibility = []
        self.filter_state_changed.emit(False)
        self.update_search_button_state()

    def get_filter_info(self):
        """
        Get information about current filters
        
        Returns:
            dict: Filter information
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return {}
        
        model = self.main_window.table.get_model()
        
        info = {
            'is_filtered': self.is_filtered,
            'visible_rows': self.get_visible_row_count(),
            'total_rows': 0,
            'filter_details': {}
        }
        
        # Get total rows
        if hasattr(model, 'get_total_rows'):
            info['total_rows'] = model.get_total_rows()
        
        # Get filter state from model
        if hasattr(model, 'get_filter_state'):
            info['filter_details'] = model.get_filter_state()
        
        return info

    def get_visible_row_count(self):
        """
        Calculate visible row count from virtual model
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return 0
        
        model = self.main_window.table.get_model()
        return model.rowCount()

    def update_search_button_state(self):
        """
        Update search button text and behavior based on filter state
        """
        if not hasattr(self.main_window, 'search_button'):
            return
        
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
        """
        Search with multiple conditions using virtual model
        
        Args:
            options: Search options dictionary
        """
        if not hasattr(self, 'current_search_row'):
            self.current_search_row = -1
        
        if not options:
            return
        
        # Get virtual model
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        model = self.main_window.table.get_model()
        
        # Search for matching rows
        if hasattr(model, 'search_rows'):
            matching_rows = model.search_rows(options)
            
            if not matching_rows:
                QMessageBox.warning(self.main_window, "Search", 
                                    "Cannot find the specified text.")
                self.current_search_row = 0
                return
            
            # Find next match from current position
            for i, row in enumerate(matching_rows):
                if row > self.current_search_row:
                    self.current_search_row = row
                    
                    # Select the row in table
                    if hasattr(self.main_window.table, 'selectRow'):
                        self.main_window.table.selectRow(row)
                    
                    # Update for next search
                    if i == len(matching_rows) - 1:
                        self.current_search_row = 0  # Wrap around
                    else:
                        self.current_search_row = row + 1
                    return
            
            # If we get here, no matches after current position
            reply = QMessageBox.question(self.main_window, "Search", 
                                    "Cannot find more occurrences. Search from the beginning?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.current_search_row = 0
                if matching_rows:
                    row = matching_rows[0]
                    self.current_search_row = row + 1
                    if hasattr(self.main_window.table, 'selectRow'):
                        self.main_window.table.selectRow(row)
            else:
                self.current_search_row = 0
        else:
            QMessageBox.warning(self.main_window, "Search Error", 
                                "Search not supported in current model.")

    def filter_table(self, options):
        """
        Filter table with multiple conditions - using virtual model
        
        Args:
            options: Filter options dictionary
        """
        if not options:
            return
        
        # Get virtual model
        if not hasattr(self.main_window.table, 'get_model'):
            print("Error: Virtual model not available")
            return
        
        model = self.main_window.table.get_model()
        
        # Save current visibility state if it's the first filter
        if not self.is_filtered:
            self.save_current_visibility()
        
        try:
            # Apply the virtual filter
            self._apply_virtual_filter(options)
            
            # Update filter state
            self.is_filtered = True
            self.filter_state_changed.emit(True)
            self.update_search_button_state()
            
            # Show result count
            visible_count = self.get_visible_row_count()
            total_count = model.get_total_rows() if hasattr(model, 'get_total_rows') else 0
            
            if visible_count == 0:
                QMessageBox.information(self.main_window, "Filter", 
                                    "No rows match the filter criteria.")
            else:
                print(f"Filter successful: {visible_count}/{total_count} rows visible")
                
        except Exception as e:
            print(f"Error applying filter: {e}")
            QMessageBox.critical(self.main_window, "Filter Error", 
                                f"Failed to apply filter: {str(e)}")
    
    def highlight_duplicate_rows(self, websign):
        """
        Highlight all rows with duplicate websign using virtual model styling
        
        Args:
            websign: Websign to check for duplicates
        """
        if websign not in self.websign_tracker:
            return
        
        # Get virtual model
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        model = self.main_window.table.get_model()
        
        # Check if model supports styling
        if not hasattr(model, 'set_row_background'):
            print("Warning: Virtual model doesn't support styling")
            return
        
        duplicate_rows = self.websign_tracker[websign]
        
        if len(duplicate_rows) > 1:
            # Highlight all duplicate rows with light red
            for visible_row in duplicate_rows:
                model.set_row_background(visible_row, '#FFE6E6')  # Light red
            
            print(f"Highlighted {len(duplicate_rows)} duplicate rows for websign: {websign}")

    def reapply_duplicate_highlighting(self):
        """
        Re-apply duplicate highlighting using virtual model styling
        """
        # Get virtual model
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        model = self.main_window.table.get_model()
        
        # Check if model supports styling
        if not hasattr(model, 'clear_row_styles'):
            print("Warning: Virtual model doesn't support styling")
            return
        
        # Clear all existing styling
        model.clear_row_styles()
        
        # Re-apply highlighting for duplicates
        for websign, rows in self.websign_tracker.items():
            if len(rows) > 1:
                # Highlight all duplicate rows with light red
                for visible_row in rows:
                    if hasattr(model, 'set_row_background'):
                        model.set_row_background(visible_row, '#FFE6E6')
        
        print(f"Reapplied duplicate highlighting for {len(self.websign_tracker)} websigns")

    def show_duplicate_warning(self, websign, duplicate_rows):
        """
        Show warning for duplicate websign
        
        Args:
            websign: Duplicate websign
            duplicate_rows: List of row indices with this websign
        
        Returns:
            QMessageBox.StandardButton: User's response
        """
        msg = QMessageBox(self.main_window)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Duplicate Websign Detected")
        
        # Format message
        visible_rows = [str(r + 1) for r in duplicate_rows]
        msg.setText(f"Websign '{websign}' already exists in the table.")
        msg.setInformativeText(f"Found at row(s): {', '.join(visible_rows)}\n\n"
                            f"Do you want to add this duplicate entry?")
        
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.YesToAll
        )
        
        # Set default to No
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        return msg.exec()

    def rebuild_websign_tracker(self):
        """
        Rebuild the websign tracker from virtual model data
        
        Returns:
            dict: Updated websign tracker
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return self.websign_tracker
        
        model = self.main_window.table.get_model()
        self.websign_tracker.clear()
        
        # Check if model supports duplicate finding
        if hasattr(model, 'find_duplicates'):
            # Use model's efficient duplicate finding
            duplicates = model.find_duplicates('websign')
            
            for websign, visible_rows in duplicates.items():
                self.websign_tracker[websign] = visible_rows
                
                # Apply highlighting if there are duplicates
                if len(visible_rows) > 1:
                    self.highlight_duplicate_rows(websign)
        else:
            # Fallback: manual processing
            for visible_row in range(model.rowCount()):
                row_data = model.get_row_data(visible_row)
                websign = row_data.get('websign', '')
                
                if websign:
                    if websign not in self.websign_tracker:
                        self.websign_tracker[websign] = []
                    self.websign_tracker[websign].append(visible_row)
                    
                    # Update duplicate highlighting
                    if len(self.websign_tracker[websign]) > 1:
                        self.highlight_duplicate_rows(websign)
        
        print(f"Rebuilt websign tracker: {len(self.websign_tracker)} unique websigns")
        
        # Report duplicates
        duplicate_count = sum(1 for rows in self.websign_tracker.values() if len(rows) > 1)
        if duplicate_count > 0:
            print(f"Found {duplicate_count} websigns with duplicates")
        
        return self.websign_tracker
    
    def update_progress(self, rows, progress):
        """
        Update progress for rows - using virtual model
        
        Args:
            rows: Single row index or list of row indices
            progress: Progress percentage (0-100)
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        if not isinstance(rows, list):
            rows = [rows]
        
        model = self.main_window.table.get_model()
        
        for row in rows:
            try:
                # Get current row data
                row_data = model.get_row_data(row)
                if not row_data:
                    continue
                
                # Clamp progress value
                progress_value = max(0, min(100, progress))
                
                # Update progress in row data
                row_data['progress'] = progress_value
                
                # Auto-update read status based on progress
                if progress_value == 0:
                    row_data['read_status'] = 'unread'
                elif progress_value == 100:
                    row_data['read_status'] = 'completed'
                else:
                    row_data['read_status'] = 'reading'
                
                # Update row in model
                model.update_row(row, row_data)
                
            except Exception as e:
                print(f"Error updating progress for row {row}: {e}")
    
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

    def batch_update_rows(self, updates):
        """
        Batch update multiple rows efficiently
        
        Args:
            updates: Dict of {row_index: data_dict} updates
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return
        
        model = self.main_window.table.get_model()
        
        if hasattr(model, 'batch_update_rows'):
            model.batch_update_rows(updates)
        else:
            # Fallback: update rows individually
            for row, data in updates.items():
                model.update_row(row, data)

    def get_table_statistics(self):
        """
        Get statistics from virtual model
        
        Returns:
            dict: Statistics including row counts, cache performance, etc.
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return {}
        
        model = self.main_window.table.get_model()
        
        stats = {
            'total_rows': model.get_total_rows(),
            'visible_rows': model.rowCount(),
            'is_filtered': self.is_filtered
        }
        
        # Add performance stats if available
        if hasattr(model, 'get_performance_stats'):
            perf_stats = model.get_performance_stats()
            stats.update(perf_stats)
        
        return stats

    def get_performance_stats(self):
        """
        Get performance statistics from virtual model
        
        Returns:
            dict: Performance statistics
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return {}
        
        model = self.main_window.table.get_model()
        
        stats = {
            'table_controller': {
                'is_filtered': self.is_filtered,
                'websign_tracker_size': len(self.websign_tracker),
                'duplicate_websigns': sum(1 for rows in self.websign_tracker.values() if len(rows) > 1)
            }
        }
        
        # Get model performance stats
        if hasattr(model, 'get_performance_stats'):
            model_stats = model.get_performance_stats()
            stats['virtual_model'] = model_stats
        
        # Get filter info
        stats['filters'] = self.get_filter_info()
        
        return stats

    def print_debug_info(self):
        """
        Print debug information about current state
        """
        print("\n=== TableController Debug Info ===")
        
        # Basic info
        print(f"Filter active: {self.is_filtered}")
        print(f"Visible rows: {self.get_visible_row_count()}")
        print(f"Websign tracker entries: {len(self.websign_tracker)}")
        
        # Duplicate info
        dup_count = sum(1 for rows in self.websign_tracker.values() if len(rows) > 1)
        print(f"Duplicate websigns: {dup_count}")
        
        # Model info
        if hasattr(self.main_window.table, 'get_model'):
            model = self.main_window.table.get_model()
            print(f"Model total rows: {model.get_total_rows()}")
            print(f"Model visible rows: {model.rowCount()}")
        
        # Performance stats
        stats = self.get_performance_stats()
        if stats.get('virtual_model'):
            perf = stats['virtual_model']
            hit_rate = perf.get('cache_hit_rate', 0)
            print(f"Cache hit rate: {hit_rate:.1f}%")
        
        print("================================\n")

    def get_current_filter_info(self):
        """
        Get information about the currently applied filter
        
        Returns:
            dict: Filter information
        """
        if not hasattr(self.main_window.table, 'get_model'):
            return {}
        
        model = self.main_window.table.get_model()
        
        info = {
            'is_filtered': self.is_filtered,
            'visible_rows': self.get_visible_row_count(),
            'total_rows': model.get_total_rows() if hasattr(model, 'get_total_rows') else 0,
            'filter_type': 'none'
        }
        
        # Check what type of filter is active
        if hasattr(model, '_text_filter_active') and model._text_filter_active:
            info['filter_type'] = 'text_filter'
        elif hasattr(model, '_custom_filter_active') and model._custom_filter_active:
            info['filter_type'] = 'custom_filter'
        elif hasattr(model, '_filters') and model._filters:
            info['filter_type'] = 'status_tag_filter'
        
        return info