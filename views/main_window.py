from PyQt6.QtWidgets import (QSplitter, QMainWindow, QWidget,
                             QVBoxLayout, QHBoxLayout,
                             QPushButton, QMessageBox, QMenu, QDialog,
                             QTabBar, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer
from views.detail_panel import DetailPanel
from models.config_manager import ConfigManager
from models.data_parser import DataParser
from views.dialogs import InsertDialog, SearchDialog, EditDialog
from controllers.file_io import FileIO
from controllers.table_controller import TableController
from controllers.state_manager import StateManager
from controllers.web_controller import WebController
from controllers.table_visual_manager import TableVisualManager
from views.virtual_table_view import VirtualTableView
from views.sidebar import Sidebar
# from views.paged_virtual_grid_view import PagedVirtualGridView
from views.virtual_grid_view import VirtualGridView
import os
import re

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LB Manager")
        self.resize(1150, 700)
        
        # Step 1: Basic managers
        self.config_manager = ConfigManager()
        self.data_parser = DataParser()
        self.file_io = FileIO(self)
        self.data = []
        
        # Load settings
        self.jm_website_value = self.config_manager.get_jm_website()
        self.dist_website_value = self.config_manager.get_dist_website()
        self.lib_path_value = self.config_manager.get_lib_path()
        
        # Step 2: Setup basic UI (without menu bar)
        self.setup_basic_ui()
        
        # Step 3: Initialize controllers
        self.table_controller = TableController(self)
        self.state_manager = StateManager(self)
        self.web_controller = WebController(self)
        self.visual_manager = TableVisualManager(self)
        
        # Step 4: Initialize other UI components
        self.detail_panel = DetailPanel(self)
        self.sidebar = Sidebar(self)
        # self.grid_view = PagedVirtualGridView(self)
        self.grid_view = VirtualGridView(self)
        self.grid_view.set_main_window_model()
        
        # Add sidebar and detail panel to splitter
        self.main_splitter.insertWidget(0, self.sidebar)
        self.main_splitter.addWidget(self.detail_panel)
        
        # Step 5: Complete UI initialization
        self.init_ui()
        
        # Step 6: Create menu bar (now web_controller exists)
        self.create_menu_bar()
        
        # Step 7: Restore window state
        self.state_manager.restore_window_state()
        
        # Step 8: Connect signals
        self.sidebar.tag_filter_changed.connect(self.apply_tag_filter)
        self.table_controller.rebuild_websign_tracker()
        self.table_controller.data_added.connect(self.update_sidebar_counts)
        self.table_controller.filter_state_changed.connect(self.on_filter_state_changed)
        # self.grid_view.selection_changed.connect(self.on_grid_selection_changed)
        self.grid_view.selectionModel().selectionChanged.connect(self.on_grid_selection_changed)
        
        # Step 9: Load saved view preference
        self.load_view_preference()

    def setup_basic_ui(self):
        """Setup basic UI components without menu bar"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create middle container for view switching
        middle_container = QWidget()
        middle_layout = QVBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # Create view tab bar
        self.view_tab_bar = QTabBar()
        self.view_tab_bar.addTab("📊 Table View")
        self.view_tab_bar.addTab("🖼️ Grid View")
        self.view_tab_bar.setExpanding(False)
        self.view_tab_bar.currentChanged.connect(self.switch_view)
        
        # Set tab bar style
        self.view_tab_bar.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                border-bottom: 2px solid #2196f3;
                font-weight: bold;
            }
        """)
        
        middle_layout.addWidget(self.view_tab_bar)
        
        # Create stacked widget for views
        self.view_stack = QStackedWidget()
        
        # Create table view container
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_layout.setSpacing(10)
        
        # Create virtual table
        self.table = VirtualTableView()
        
        # Set column widths
        self.table.setColumnWidth(0, 80)   # websign
        self.table.setColumnWidth(1, 120)  # author
        self.table.setColumnWidth(2, 200)  # title
        self.table.setColumnWidth(3, 100)  # group
        self.table.setColumnWidth(4, 100)  # show
        self.table.setColumnWidth(5, 120)  # magazine
        self.table.setColumnWidth(6, 120)  # origin
        self.table.setColumnWidth(7, 150)  # tag
        self.table.setColumnWidth(8, 80)   # read_status
        self.table.setColumnWidth(9, 80)   # progress
        self.table.setColumnWidth(10, 100) # file_path
        
        # Hide file_path column by default
        self.table.setColumnHidden(10, True)
        
        # Create buttons for table view
        button_layout = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.setToolTip("Search (Ctrl+F)")
        self.clear_button = QPushButton("Clear")
        
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        # Add table and buttons to table layout
        table_layout.addWidget(self.table)
        table_layout.addLayout(button_layout)
        
        table_container.setLayout(table_layout)
        
        # Add views to stack
        self.view_stack.addWidget(table_container)
        # Note: grid_view will be added later after initialization
        middle_layout.addWidget(self.view_stack)
        middle_container.setLayout(middle_layout)
        self.main_splitter.addWidget(middle_container)
        
        main_layout.addWidget(self.main_splitter)
        central_widget.setLayout(main_layout)
        
        # Set initial splitter sizes
        self.main_splitter.setSizes([220, 600, 300])
        
        # Set splitter handle style
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #bdc3c7;
            }
            QSplitter::handle:hover {
                background-color: #95a5a6;
            }
        """)

    def init_ui(self):
        """Complete UI initialization (called after all controllers are created)"""
        # Now add grid view to stack (grid_view is initialized in __init__)
        self.view_stack.addWidget(self.grid_view)

        # CRITICAL: Connect grid view model AFTER table is initialized
        QTimer.singleShot(200, self._initialize_grid_view)
        
        # Connect table signals
        self.table.rowDoubleClicked.connect(self.on_table_double_click)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        
        # Connect column signals
        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.visual_manager.show_header_context_menu)
        
        # Connect to state_manager
        self.table.horizontalHeader().sectionResized.connect(self.state_manager.on_column_resized)
        self.table.horizontalHeader().sectionMoved.connect(self.state_manager.on_column_moved)
        
        # Connect button signals
        self.search_button.clicked.connect(self.show_search_dialog)
        self.clear_button.clicked.connect(self.clear_table)
        
        # Connect sidebar signals
        self.sidebar.status_filter_changed.connect(self.apply_status_filter)
        self.sidebar.filter_reset.connect(self.reset_table_filter)

        # Enable context menu for table view
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Update sidebar counts initially
        self.update_sidebar_counts()

    def _initialize_grid_view(self):
        """Initialize grid view with delay to ensure table is ready"""
        if hasattr(self.table, 'get_model'):
            model = self.table.get_model()
            if model:
                print(f"[MainWindow] Setting grid view model with {model.rowCount()} rows")
                
                # Set model to grid view
                self.grid_view.setModel(model)
                
                # Force initial update
                QTimer.singleShot(300, self.grid_view.update_visible_items)
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        insert_action = file_menu.addAction("Insert")
        import_action = file_menu.addAction("Import")
        save_action = file_menu.addAction("Save")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        
        insert_action.triggered.connect(self.show_insert_dialog)
        import_action.triggered.connect(self.file_io.import_from_file)
        save_action.triggered.connect(self.file_io.save_to_file)
        exit_action.triggered.connect(self.close)
        
        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        web_setting_action = settings_menu.addAction("Web Setting")
        lib_setting_action = settings_menu.addAction("Lib Setting")
        view_setting_action = settings_menu.addAction("View Setting")
        
        web_setting_action.triggered.connect(self.web_controller.show_web_setting_dialog)
        lib_setting_action.triggered.connect(self.web_controller.show_lib_setting_dialog)
        view_setting_action.triggered.connect(self.web_controller.show_view_setting_dialog)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about_dialog)

    def switch_view(self, index):
        """Switch between table and grid view without synchronization"""
        if index == 0:  # Table view
            self.view_stack.setCurrentIndex(0)
        else:  # Grid view
            self.view_stack.setCurrentIndex(1)
            # Grid view automatically handles virtualization
        
        # Save view preference
        self.save_view_preference(index)

    def sync_selection_to_table(self, selected_rows):
        """Sync selection from grid to table"""
        self.table.clearSelection()
        for row in selected_rows:
            if row < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setSelected(True)

    def on_grid_selection_changed(self):
        """Handle grid view selection changes"""
        if not hasattr(self, 'grid_view'):
            return
        
        # Get grid selection
        selected_rows = self.grid_view.get_selected_rows()
        
        if not selected_rows:
            self.detail_panel.show_empty_state()
            return
        
        # Update detail panel
        selected_row = selected_rows[0]
        row_data = self.get_row_data(selected_row)
        
        if row_data:
            if len(selected_rows) > 1:
                self.detail_panel.show_multiple_selection_state(len(selected_rows))
            
            self.detail_panel.update_details(row_data)

    def load_view_preference(self):
        """Load saved view preference from config"""
        try:
            view_mode = self.config_manager.get_view_mode()
            if view_mode == "grid":
                self.view_tab_bar.setCurrentIndex(1)
                self.view_stack.setCurrentIndex(1)
            else:
                self.view_tab_bar.setCurrentIndex(0)
                self.view_stack.setCurrentIndex(0)
        except:
            # Default to table view
            self.view_tab_bar.setCurrentIndex(0)
            self.view_stack.setCurrentIndex(0)

    def save_view_preference(self, index):
        """Save view preference to config"""
        view_mode = "grid" if index == 1 else "table"
        # Need to add this method to config_manager
        self.config_manager.set_view_mode(view_mode)

    def show_about_dialog(self):
        """Show about information"""
        QMessageBox.about(self, "About", "Author: Deepseek")

    def show_context_menu(self, position):
        """Show right-click context menu for selected rows"""
        selected_rows = self.get_selected_rows()
        
        if not selected_rows:
            return
            
        # Create context menu
        context_menu = QMenu(self)
        
        # Always show these actions (work for both single and multiple)
        edit_action = context_menu.addAction("Edit")
        view_zip_action = context_menu.addAction("View")
        view_online_action = context_menu.addAction("View online")
        update_tag_action = context_menu.addAction("Update Tag")
        
        # Connect actions - they now handle both single and multiple rows
        view_zip_action.triggered.connect(lambda: self.web_controller.view_zip_images(selected_rows))
        view_online_action.triggered.connect(lambda: self.web_controller.view_online(selected_rows))
        update_tag_action.triggered.connect(lambda: self.web_controller.update_tag_for_row(selected_rows))
        edit_action.triggered.connect(lambda: self.edit_rows(selected_rows))
        
        # Read status submenu
        read_status_menu = context_menu.addMenu("Mark as")
        mark_unread_action = read_status_menu.addAction("Unread")
        mark_reading_action = read_status_menu.addAction("Reading")
        mark_completed_action = read_status_menu.addAction("Completed")
        
        # Progress submenu
        progress_menu = context_menu.addMenu("Set Progress")
        progress_0_action = progress_menu.addAction("0%")
        progress_25_action = progress_menu.addAction("25%")
        progress_50_action = progress_menu.addAction("50%")
        progress_75_action = progress_menu.addAction("75%")
        progress_100_action = progress_menu.addAction("100%")
        
        copy_action = context_menu.addAction("Copy to clipboard")
        delete_action = context_menu.addAction("Delete")
        
        # Connect all actions
        mark_unread_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 0))
        mark_reading_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 50))  # Default reading progress
        mark_completed_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 100))
        
        progress_0_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 0))
        progress_25_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 25))
        progress_50_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 50))
        progress_75_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 75))
        progress_100_action.triggered.connect(lambda: self.table_controller.update_progress(selected_rows, 100))
        
        copy_action.triggered.connect(lambda: self.visual_manager.copy_rows_to_clipboard(selected_rows))
        delete_action.triggered.connect(lambda: self.visual_manager.delete_rows(selected_rows))
        
        # Show menu
        context_menu.exec(self.table.viewport().mapToGlobal(position))
        
    def parse_text(self, text):
        return DataParser.parse_text(text)
    
    def show_insert_dialog(self):
        dialog = InsertDialog(self, self.jm_website_value)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.get_input_text()
            tag_text = dialog.get_tag_text()
            if text:
                parsed_data = DataParser.parse_text(text)
                if parsed_data is not None:
                    data_list = list(parsed_data)
                    data_list[7] = tag_text
                    self.table_controller.add_to_table(tuple(data_list))
    
    def show_search_dialog(self):
        dialog = SearchDialog(self)
        result = dialog.exec()
        
        if result == 1:  # Search Next
            options = dialog.get_search_options()
            if options:
                self.table_controller.search_next(options)
        elif result == 2:  # Filter
            options = dialog.get_search_options()
            if options:
                self.table_controller.apply_search_filter(options)

    def reset_search_filter(self):
        """Reset search filter - called from button click"""
        self.table_controller.reset_search_filter()
    
    def search_next(self, column, search_text):
        self.table_controller.search_next(column, search_text)
    
    def filter_table(self, column, search_text):
        self.table_controller.filter_table(column, search_text)

    def update_search_button_behavior(self):
        """Update search button text based on filter state"""
        if not hasattr(self, 'search_button'):
            return
            
        # Check if filter is active
        model = self.table.get_model()
        if model and hasattr(model, '_filter_active'):
            if model._filter_active:
                # Change to "Clear Filter" when filter is active
                self.search_button.setText("Clear Filter")
                self.search_button.clicked.disconnect()
                self.search_button.clicked.connect(self.reset_search_filter)
            else:
                # Change back to "Search" when no filter
                self.search_button.setText("Search")
                self.search_button.clicked.disconnect()
                self.search_button.clicked.connect(self.show_search_dialog)
        else:
            # Default behavior
            self.search_button.setText("Search")
            self.search_button.clicked.disconnect()
            self.search_button.clicked.connect(self.show_search_dialog)
    
    def clear_table(self):
        """
        Clear all data from virtual table
        """
        reply = QMessageBox.question(
            self, 
            "Clear", 
            "Are you sure you want to clear all data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear virtual table
            self.table.clear()
            
            # Clear grid view
            if hasattr(self.grid_view, 'refresh_current_page'):
                self.grid_view.refresh_current_page()
            
            # Update sidebar counts
            self.update_sidebar_counts()
            
            # Clear detail panel
            self.detail_panel.show_empty_state()
    
    def fetch_zip_numbers(self, lib_path):
        """Recursively scan directory and extract integers from ZIP filenames"""
        numbers = set()  # Use set to avoid duplicates
        
        def scan_directory(directory):
            """Recursively scan directory"""
            try:
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    
                    if os.path.isfile(item_path):
                        # Check if it's a ZIP file and extract number
                        if item.lower().endswith('.zip'):
                            number = self.extract_number_from_filename(item)
                            if number is not None:
                                numbers.add(number)
                    
                    elif os.path.isdir(item_path):
                        # Recursively scan subdirectory
                        scan_directory(item_path)
            
            except PermissionError:
                # Skip directories without permission
                pass
            except Exception as e:
                print(f"Error scanning directory {directory}: {e}")
        
        # Start scanning
        scan_directory(lib_path)
        return sorted(numbers)  # Return sorted list
    
    def extract_number_from_filename(self, filename):
        """Extract integer from filename"""
        # Remove .zip extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Use regex to match pure numbers
        match = re.match(r'^(\d+)$', name_without_ext)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
    
    def save_numbers_to_file(self, numbers):
        """Save number list to nums.txt file"""
        try:
            with open('./nums.txt', 'w', encoding='utf-8') as f:
                for number in numbers:
                    f.write(f"{number}\n")
        except Exception as e:
            raise Exception(f"Failed to save numbers to file: {str(e)}")
    
    def closeEvent(self, event):
        """Ensure thread is properly cleaned up and save layout"""
        # Save panel layout
        if hasattr(self, 'state_manager'):
            self.state_manager.save_panel_layout()
        
        if hasattr(self, 'refresh_thread') and self.refresh_thread.isRunning():
            self.refresh_thread.terminate()
            self.refresh_thread.wait()
        event.accept()

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Debounced save of window state
        if hasattr(self, 'save_state_timer'):
            self.save_state_timer.start(500)  # Save after 500ms of no resizing
        else:
            self.save_state_timer = QTimer()
            self.save_state_timer.setSingleShot(True)
            self.save_state_timer.timeout.connect(self.state_manager.save_window_state)
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        if event.key() == Qt.Key.Key_Delete:
            # Get selected rows
            selected_ranges = self.table.selectedRanges()
            rows_to_delete = set()
            
            for selection_range in selected_ranges:
                for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
                    rows_to_delete.add(row)
            
            if rows_to_delete:
                self.visual_manager.delete_rows(list(rows_to_delete))
            event.accept()
        elif event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+F to open search dialog
            self.show_search_dialog()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def update_read_status(self, row, status):
        """Update read status for specified row"""
        try:
            read_status_item = self.table.item(row, 8)
            if read_status_item:
                read_status_item.setData(Qt.ItemDataRole.UserRole, status)
                read_status_item.setText(self.table_controller.get_read_status_display(status))
                self.table_controller.apply_read_status_style(read_status_item, status)
                self.update_sidebar_counts()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update read status: {str(e)}")

    def update_progress(self, row, progress):
        """Update progress for specified row"""
        self.table_controller.update_progress(row, progress)

    def apply_status_filter(self, status):
        """
        Apply status filter to virtual table
        
        Args:
            status: Status to filter by ("all", "unread", "reading", "completed")
        """
        self.table.apply_status_filter(status)
        self.update_sidebar_counts()
        
        # Invalidate grid view cache
        if hasattr(self.grid_view, 'invalidate_caches'):
            self.grid_view.invalidate_caches()

    def reset_table_filter(self):
        """
        Reset all filters in virtual table
        """
        self.table.reset_table_filter()
        self.update_sidebar_counts()
        
        # Invalidate grid view cache
        if hasattr(self.grid_view, 'invalidate_caches'):
            self.grid_view.invalidate_caches()
    
    def update_sidebar_counts(self):
        """
        Update sidebar with current statistics from virtual model
        """
        if not hasattr(self.table, 'get_model'):
            return
        
        model = self.table.get_model()
        
        # Get statistics directly from model
        status_counts = model.get_status_counts()
        tag_frequency = model.get_all_tags()
        
        # Update sidebar
        self.sidebar.update_status_counts(status_counts)
        self.sidebar.update_tag_cloud(tag_frequency)

    def apply_tag_filter(self, selected_tags):
        """
        Apply tag filter to virtual table
        
        Args:
            selected_tags: List of tags to filter by
        """
        self.table.apply_tag_filter(selected_tags)
        self.update_sidebar_counts()
        
        # Invalidate grid view cache
        if hasattr(self.grid_view, 'invalidate_caches'):
            self.grid_view.invalidate_caches()

    def get_current_status_filter(self):
        """Get currently selected status filter"""
        if self.sidebar.all_btn.isChecked():
            return "all"
        elif self.sidebar.unread_btn.isChecked():
            return "unread"
        elif self.sidebar.reading_btn.isChecked():
            return "reading"
        elif self.sidebar.completed_btn.isChecked():
            return "completed"
        return "all"

    def add_data_to_table(self, data):
        """Add data to table and update sidebar counts"""
        self.table_controller.add_to_table(data)
        self.update_sidebar_counts()
        
        # CRITICAL: Refresh grid view if it's active
        if (hasattr(self, 'view_tab_bar') and 
            self.view_tab_bar.currentIndex() == 1 and
            hasattr(self, 'grid_view')):
            
            print("[MainWindow] Refreshing grid view after data addition")
            QTimer.singleShot(100, self.grid_view.refresh)

    def on_filter_state_changed(self, is_filtered):
        """Handle filter state change"""
        self.update_sidebar_counts()
        self.update_search_button_behavior()

    def on_table_double_click(self, index):
        """Handle table double-click to open image viewer"""
        row = index.row()
        if row >= 0 and row < self.table.rowCount():
            # Show loading indicator
            self.setCursor(Qt.CursorShape.WaitCursor)
            
            try:
                # Call the same method as right-click "View" option
                self.web_controller.view_zip_images(row)
            except Exception as e:
                QMessageBox.critical(self, "View Error", f"Failed to open viewer: {str(e)}")
            finally:
                # Restore cursor
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def on_table_selection_changed(self):
        """
        Handle table selection changes and update detail panel
        """
        selected_rows = self.get_selected_rows()
        
        if not selected_rows:
            self.detail_panel.show_empty_state()
        elif len(selected_rows) > 1:
            self.detail_panel.show_multiple_selection_state(len(selected_rows))
            if selected_rows:
                row_data = self.get_row_data(selected_rows[0])
                self.detail_panel.update_details(row_data)
        else:
            row_data = self.get_row_data(selected_rows[0])
            self.detail_panel.update_details(row_data)

    def get_selected_rows(self):
        """
        Get all selected row indices from virtual table
        
        Returns:
            List[int]: List of selected row indices (sorted)
        """
        if not hasattr(self.table, 'get_selected_rows'):
            # Fallback for compatibility
            selected_rows = set()
            model = self.table.get_model()
            
            for row in range(model.rowCount()):
                # Check if any cell in the row is selected
                for col in range(model.columnCount()):
                    index = model.index(row, col)
                    if self.table.selectionModel().isSelected(index):
                        selected_rows.add(row)
                        break
            
            return sorted(list(selected_rows))
        
        # Use VirtualTableView's built-in method
        return self.table.get_selected_rows()

    def edit_rows(self, rows):
        """
        Edit selected rows - for multiple rows, only edit the first one
        
        Args:
            rows: List of row indices to edit (only first one is edited)
        """
        if not rows:
            return
        
        # For multiple rows, only edit the first one
        row_to_edit = rows[0] if isinstance(rows, list) else rows
        
        # Get current row data from virtual model
        row_data = self.get_row_data(row_to_edit)
        if not row_data:
            QMessageBox.warning(self, "Edit Error", "Cannot retrieve row data")
            return
        
        # Open edit dialog
        from views.dialogs import EditDialog
        dialog = EditDialog(self, row_data)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_data = dialog.get_edited_data()
            
            # Update the row
            self.update_row_data(row_to_edit, edited_data)
            
            # If multiple rows were selected, ask if user wants to apply same changes
            if isinstance(rows, list) and len(rows) > 1:
                reply = QMessageBox.question(
                    self, 
                    "Apply to All", 
                    f"Apply the same changes to all {len(rows)} selected rows?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Create updates for all selected rows
                    updates = {}
                    for row in rows[1:]:  # Skip first row already updated
                        updates[row] = edited_data
                    
                    # Batch update remaining rows
                    self.batch_update_rows(updates)
    
    def get_row_data(self, visible_row):
        """
        Get row data from virtual model
        
        Args:
            visible_row: Visible row index (after filtering)
        
        Returns:
            dict: Row data as dictionary
        """
        if not hasattr(self.table, 'get_model'):
            return {}
        
        model = self.table.get_model()
        if visible_row < 0 or visible_row >= model.rowCount():
            return {}
        
        return model.get_row_data(visible_row)
        
    def get_cell_text(self, row, column):
        """
        Get cell text from virtual model
        
        Args:
            row: Row index
            column: Column index
        
        Returns:
            str: Cell text
        """
        if not hasattr(self.table, 'get_model'):
            return ""
        
        model = self.table.get_model()
        if row < 0 or row >= model.rowCount() or column < 0 or column >= model.columnCount():
            return ""
        
        index = model.index(row, column)
        
        # Special handling for certain columns
        if column == 0:  # websign column
            # Get original websign string from UserRole
            websign = model.data(index, Qt.ItemDataRole.UserRole)
            return str(websign) if websign is not None else ""
        elif column == 8:  # read_status column
            # Get actual status from UserRole
            status = model.data(index, Qt.ItemDataRole.UserRole)
            return str(status) if status is not None else "unread"
        elif column == 9:  # progress column
            # Get numeric progress from UserRole
            progress = model.data(index, Qt.ItemDataRole.UserRole)
            return str(progress) if progress is not None else "0"
        else:
            # Get display text for other columns
            text = model.data(index, Qt.ItemDataRole.DisplayRole)
            return str(text) if text is not None else ""
    
    def update_row_data(self, row, data):
        """
        Update row data in virtual model
        
        Args:
            row: Row index to update
            data: Dictionary with new row data
        """
        if not hasattr(self.table, 'get_model'):
            QMessageBox.critical(self, "Edit Error", "Virtual model not available")
            return
        
        try:
            model = self.table.get_model()
            
            # Get old tag for comparison
            old_tag = self.get_cell_text(row, 7)
            tag_changed = (old_tag != data.get('tag', ''))
            
            # Check for websign changes
            old_websign = self.get_cell_text(row, 0)
            new_websign = data.get('websign', '')
            websign_changed = (old_websign != new_websign)
            
            # Update row in virtual model
            success = model.update_row(row, data)
            
            if not success:
                QMessageBox.critical(self, "Edit Error", "Failed to update row in model")
                return
            
            # Rebuild websign tracker if websign was changed
            if websign_changed and hasattr(self, 'table_controller'):
                self.table_controller.rebuild_websign_tracker()
                
                # If websign changed and there are now duplicates, highlight them
                if new_websign in self.table_controller.websign_tracker:
                    duplicate_rows = self.table_controller.websign_tracker[new_websign]
                    if len(duplicate_rows) > 1:
                        # The highlighting is already done in rebuild_websign_tracker
                        print(f"Websign changed to '{new_websign}' - found duplicates at rows: {duplicate_rows}")
            
            # Update tag cloud if tag was changed
            if tag_changed:
                self.update_sidebar_counts()
            
            # If in grid view, refresh to show updated data
            if hasattr(self, 'view_tab_bar') and self.view_tab_bar.currentIndex() == 1:
                if hasattr(self.grid_view, 'refresh_current_page'):
                    self.grid_view.refresh_current_page()
            
            QMessageBox.information(self, "Edit", "Row data updated successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Failed to update row: {str(e)}")

    def batch_update_rows(self, updates):
        """
        Update multiple rows efficiently
        
        Args:
            updates: Dictionary of {row_index: data_dict} updates
        """
        if not hasattr(self.table, 'get_model'):
            QMessageBox.critical(self, "Update Error", "Virtual model not available")
            return False
        
        try:
            model = self.table.get_model()
            
            # Check if model supports batch updates
            if hasattr(model, 'batch_update_rows'):
                success = model.batch_update_rows(updates)
                
                if not success:
                    QMessageBox.critical(self, "Update Error", "Failed to update rows in model")
                    return False
            else:
                # Fallback: update rows individually
                for row, data in updates.items():
                    success = model.update_row(row, data)
                    if not success:
                        print(f"Warning: Failed to update row {row}")
            
            # Rebuild websign tracker to check for new duplicates
            if hasattr(self, 'table_controller'):
                self.table_controller.rebuild_websign_tracker()
            
            # Update sidebar counts (tags might have changed)
            self.update_sidebar_counts()
            
            # Refresh grid view if active
            if hasattr(self, 'view_tab_bar') and self.view_tab_bar.currentIndex() == 1:
                if hasattr(self.grid_view, 'refresh_current_page'):
                    self.grid_view.refresh_current_page()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to update rows: {str(e)}")
            return False

    def handle_detail_action(self, action_type, row_data):
        """Handle action requests from detail panel"""
        # Get current selected rows (use the row that's being displayed)
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        # Map action types to existing methods
        action_map = {
            'unread': lambda: self.table_controller.update_progress(selected_rows, 0),
            'reading': lambda: self.table_controller.update_progress(selected_rows, 50),
            'completed': lambda: self.table_controller.update_progress(selected_rows, 100),
            'progress_0': lambda: self.table_controller.update_progress(selected_rows, 0),
            'progress_25': lambda: self.table_controller.update_progress(selected_rows, 25),
            'progress_50': lambda: self.table_controller.update_progress(selected_rows, 50),
            'progress_75': lambda: self.table_controller.update_progress(selected_rows, 75),
            'progress_100': lambda: self.table_controller.update_progress(selected_rows, 100),
            'view_zip': lambda: self.web_controller.view_zip_images(selected_rows),
            'view_online': lambda: self.web_controller.view_online(selected_rows),
            'update_tag': lambda: self.web_controller.update_tag_for_row(selected_rows)
        }
        
        if action_type in action_map:
            try:
                action_map[action_type]()
                # Refresh detail panel to show updated status
                self.on_table_selection_changed()
            except Exception as e:
                QMessageBox.critical(self, "Action Error", f"Failed to perform action: {str(e)}")

    def get_virtual_model(self):
        """
        Safely get the virtual data model
        
        Returns:
            VirtualDataModel or None
        """
        if hasattr(self.table, 'get_model'):
            return self.table.get_model()
        return None

    def validate_row_index(self, row):
        """
        Validate if a row index is within bounds
        
        Args:
            row: Row index to validate
        
        Returns:
            bool: True if valid
        """
        model = self.get_virtual_model()
        if not model:
            return False
        
        return 0 <= row < model.rowCount()

    def on_widget_clicked(self, row):
        """Handle widget click from grid view"""
        if hasattr(self, 'grid_view'):
            index = self.grid_view.model().index(row, 0)
            if index.isValid():
                self.grid_view.on_item_clicked(index)
                
    def on_widget_double_clicked(self, row):
        """Handle widget double click from grid view"""
        if hasattr(self, 'grid_view'):
            index = self.grid_view.model().index(row, 0)
            if index.isValid():
                self.grid_view.on_item_double_clicked(index)