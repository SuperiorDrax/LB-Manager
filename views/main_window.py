from PyQt6.QtWidgets import (QSplitter, QMainWindow, QWidget, 
                             QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QPushButton, QMessageBox, QMenu, QDialog, 
                             QTableWidgetItem, QTabBar, QStackedWidget)
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
from views.enhanced_table import EnhancedTableWidget
from views.sidebar import Sidebar
from views.vritualized_grid_view import VirtualizedGridView
import os
import re

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window title
        self.setWindowTitle("LB Manager")
        
        # Set default window size before restoring state
        self.resize(1150, 700)  # Larger default size
        
        # Initialize managers and controllers
        self.config_manager = ConfigManager()
        self.data_parser = DataParser()
        self.file_io = FileIO(self)
        self.table_controller = TableController(self)
        self.state_manager = StateManager(self)
        self.web_controller = WebController(self)
        self.visual_manager = TableVisualManager(self)
        
        # Initialize data storage
        self.data = []
        
        # Load settings
        self.jm_website_value = self.config_manager.get_jm_website()
        self.dist_website_value = self.config_manager.get_dist_website()
        self.lib_path_value = self.config_manager.get_lib_path()

        # Initialize detail panel
        self.detail_panel = DetailPanel(self)
        
        # Restore window state (may override default size)
        self.state_manager.restore_window_state()

        # Initialize sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.tag_filter_changed.connect(self.apply_tag_filter)

        # Initialize detail panel
        self.detail_panel = DetailPanel(self)

        # Restore window state
        self.state_manager.restore_window_state()
        
        # Initialize sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.tag_filter_changed.connect(self.apply_tag_filter)

        # Initialize grid view
        self.grid_view = VirtualizedGridView(self)
        
        self.init_ui()

        self.table_controller.rebuild_websign_tracker()
        self.table_controller.data_added.connect(self.update_sidebar_counts)
        self.table_controller.filter_state_changed.connect(self.on_filter_state_changed)
        self.grid_view.selection_changed.connect(self.on_grid_selection_changed)
    
    def init_ui(self):
        """Initialize UI with sidebar and menu bar"""
        # Create menu bar first
        self.create_menu_bar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Add sidebar (fixed width initially)
        self.main_splitter.addWidget(self.sidebar)
        
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
        
        # Create table view container (existing structure)
        table_container = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_layout.setSpacing(10)
        
        # Create table using enhanced version
        self.table = EnhancedTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            'websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag', 'read_status', 'progress', 'file_path'
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 120)
        self.table.setColumnWidth(7, 150)
        self.table.setColumnWidth(8, 80)
        self.table.setColumnWidth(9, 80)
        self.table.setColumnWidth(10, 100)

        # Hide file_path column by default
        self.table.setColumnHidden(10, True)
        
        # Enable table features
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        # Connect table signals
        self.table.doubleClicked.connect(self.on_table_double_click)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        
        # Connect column signals
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.visual_manager.show_header_context_menu)
        self.table.horizontalHeader().sectionResized.connect(self.state_manager.on_column_resized)
        self.table.horizontalHeader().sectionMoved.connect(self.state_manager.on_column_moved)
        
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
        self.view_stack.addWidget(self.grid_view)
        
        middle_layout.addWidget(self.view_stack)
        middle_container.setLayout(middle_layout)
        self.main_splitter.addWidget(middle_container)
        
        # Add detail panel
        self.main_splitter.addWidget(self.detail_panel)
        
        # Set initial splitter sizes (will be overridden by state manager)
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
        
        main_layout.addWidget(self.main_splitter)
        central_widget.setLayout(main_layout)
        
        # Connect signals
        self.search_button.clicked.connect(self.show_search_dialog)
        self.clear_button.clicked.connect(self.clear_table)
        
        # Connect sidebar signals
        self.sidebar.status_filter_changed.connect(self.apply_status_filter)
        self.sidebar.filter_reset.connect(self.reset_table_filter)
        
        # Install event filter for context menu
        self.table.viewport().installEventFilter(self)
        
        # Update sidebar counts initially
        self.update_sidebar_counts()
        
        # Load saved view preference
        self.load_view_preference()
    
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
        """Switch between table and grid view"""
        if index == 0:  # Table view
            self.view_stack.setCurrentIndex(0)
        else:  # Grid view
            self.view_stack.setCurrentIndex(1)
            # Refresh grid to ensure it's up to date
            self.grid_view.refresh_current_page()
        
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
        # Get selected rows from grid
        selected_rows = self.grid_view.get_selected_rows()
        
        # Update detail panel
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

    def eventFilter(self, obj, event):
        """Event filter to handle right-click menu duplicate trigger issue"""
        if obj is self.table.viewport() and event.type() == event.Type.ContextMenu:
            # Handle right-click menu event
            return self.handle_context_menu_event(event)
        return super().eventFilter(obj, event)

    def handle_context_menu_event(self, event):
        """Handle right-click menu event"""
        # Get clicked row
        row = self.table.rowAt(event.pos().y())
        if row < 0:
            return False
            
        # Use original show_context_menu method
        self.show_context_menu(event.pos())
        
        # Mark event as handled to prevent default behavior
        return True

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

    def update_search_button_behavior(self):
        """Update search button connection based on filter state"""
        self.search_button.clicked.disconnect()
        
        if self.table_controller.is_filtered:
            self.search_button.setText(f"Show All ({self.table_controller.get_visible_row_count()} shown)")
            self.search_button.clicked.connect(self.reset_search_filter)
        else:
            self.search_button.setText("Search")
            self.search_button.clicked.connect(self.show_search_dialog)
    
    def search_next(self, column, search_text):
        self.table_controller.search_next(column, search_text)
    
    def filter_table(self, column, search_text):
        self.table_controller.filter_table(column, search_text)
    
    def clear_table(self):
        reply = QMessageBox.question(self, "Clear", 
                                "Are you sure you want to clear all data?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.table.setRowCount(0)
            self.data.clear()
            self.table_controller.websign_tracker.clear()
            self.table.clear_all_sorting()
            self.table_controller.is_filtered = False
            self.table_controller.original_row_visibility = []
            self.table_controller.filter_state_changed.emit(False)
            self.update_sidebar_counts()
            # Clear detail panel
            self.detail_panel.show_empty_state()
            # Refresh grid view
            self.grid_view.refresh_current_page()
    
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
        """Apply status filter to table"""
        if status == "all":
            self.reset_table_filter()
            return
        
        for row in range(self.table.rowCount()):
            read_status_item = self.table.item(row, 8)
            if read_status_item:
                actual_status = read_status_item.data(Qt.ItemDataRole.UserRole)
                should_show = actual_status == status
                self.table.setRowHidden(row, not should_show)
    
    def reset_table_filter(self):
        """Reset table filter to show all rows"""
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
    
    def update_sidebar_counts(self):
        """Update sidebar with current row counts and tag data"""
        counts = {
            "all": self.table.rowCount(),
            "unread": 0,
            "reading": 0,
            "completed": 0
        }
        
        tag_frequency = {}
        
        # Count all rows by their actual status and collect tags
        for row in range(self.table.rowCount()):
            read_status_item = self.table.item(row, 8)
            if read_status_item:
                status = read_status_item.data(Qt.ItemDataRole.UserRole)
                if status in counts:
                    counts[status] += 1
            
            # Collect tags
            tag_item = self.table.item(row, 7)  # tag column
            if tag_item:
                tag_text = tag_item.text()
                if tag_text:
                    # Split tags by comma and count each one
                    tags = [tag.strip() for tag in tag_text.split(',') if tag.strip()]
                    for tag in tags:
                        tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
        
        # Update sidebar with counts and tag data
        self.sidebar.update_status_counts(counts)
        self.sidebar.update_tag_cloud(tag_frequency)

    def apply_tag_filter(self, selected_tags):
        """Apply tag filter to table"""
        if not selected_tags:
            # No tags selected, show all rows (respecting status filter)
            current_status = self.get_current_status_filter()
            self.apply_status_filter(current_status)
            return
        
        for row in range(self.table.rowCount()):
            tag_item = self.table.item(row, 7)  # tag column
            should_show = False
            
            if tag_item:
                tag_text = tag_item.text()
                if tag_text:
                    # Split tags by comma and check if any matches selected tags
                    row_tags = [tag.strip() for tag in tag_text.split(',') if tag.strip()]
                    should_show = any(tag in selected_tags for tag in row_tags)
            
            # Also respect current status filter
            read_status_item = self.table.item(row, 8)
            if read_status_item:
                current_status = self.get_current_status_filter()
                if current_status != "all":
                    actual_status = read_status_item.data(Qt.ItemDataRole.UserRole)
                    should_show = should_show and (actual_status == current_status)
            
            self.table.setRowHidden(row, not should_show)

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
        """Handle table selection changes to update detail panel"""
        selected_rows = self.get_selected_rows()
        
        if not selected_rows:
            # No rows selected
            self.detail_panel.show_empty_state()
        elif len(selected_rows) > 1:
            # Multiple rows selected
            self.detail_panel.show_multiple_selection_state(len(selected_rows))
            # Show details for first selected row
            if selected_rows:
                row_data = self.get_row_data(selected_rows[0])
                self.detail_panel.update_details(row_data)
        else:
            # Single row selected
            row_data = self.get_row_data(selected_rows[0])
            self.detail_panel.update_details(row_data)

    def get_selected_rows(self):
        """Get all selected row indices"""
        selected_ranges = self.table.selectedRanges()
        selected_rows = set()
        
        for selection_range in selected_ranges:
            for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
                selected_rows.add(row)
        
        return sorted(list(selected_rows))

    def edit_rows(self, rows):
        """Edit selected rows - for multiple rows, only edit the first one"""
        if not rows:
            return
        
        # For multiple rows, only edit the first one
        row_to_edit = rows[0] if isinstance(rows, list) else rows
        
        # Get current row data
        row_data = self.get_row_data(row_to_edit)
        
        # Open edit dialog
        dialog = EditDialog(self, row_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_data = dialog.get_edited_data()
            self.update_row_data(row_to_edit, edited_data)
    
    def get_row_data(self, row):
        """Get current data from the specified row"""
        return {
            'websign': self.get_cell_text(row, 0),
            'author': self.get_cell_text(row, 1),
            'title': self.get_cell_text(row, 2),
            'group': self.get_cell_text(row, 3),
            'show': self.get_cell_text(row, 4),
            'magazine': self.get_cell_text(row, 5),
            'origin': self.get_cell_text(row, 6),
            'tag': self.get_cell_text(row, 7),
            'read_status': self.get_cell_text(row, 8),
            'progress': self.get_cell_text(row, 9),
            'file_path': self.get_cell_text(row, 10)
        }
    
    def get_cell_text(self, row, column):
        """Get text from specific cell"""
        item = self.table.item(row, column)
        if item:
            # For websign column, get the original data
            if column == 0:
                websign_data = item.data(Qt.ItemDataRole.UserRole)
                return websign_data if websign_data else item.text()
            # For read_status column, get the actual status from UserRole
            elif column == 8:
                status_data = item.data(Qt.ItemDataRole.UserRole)
                return status_data if status_data else item.text()
            # For progress column, extract number from text
            elif column == 9:
                text = item.text()
                if text.endswith('%'):
                    return text[:-1]  # Remove % sign
                return text
            return item.text()
        return ""
    
    def update_row_data(self, row, data):
        """Update row with edited data"""
        try:
            # Check if tag was actually changed
            old_tag = self.get_cell_text(row, 7)
            tag_changed = (old_tag != data['tag'])
            
            # Update websign (special handling)
            websign_item = self.table.item(row, 0)
            if websign_item:
                websign_item.setData(Qt.ItemDataRole.UserRole, data['websign'])
                if data['websign'].isdigit():
                    websign_item.setData(Qt.ItemDataRole.DisplayRole, int(data['websign']))
                else:
                    websign_item.setText(data['websign'])
            
            # Update other fields
            self.set_cell_text(row, 1, data['author'])
            self.set_cell_text(row, 2, data['title'])
            self.set_cell_text(row, 3, data['group'])
            self.set_cell_text(row, 4, data['show'])
            self.set_cell_text(row, 5, data['magazine'])
            self.set_cell_text(row, 6, data['origin'])
            self.set_cell_text(row, 7, data['tag'])
            
            # Rebuild websign tracker to update duplicates highlighting
            self.table_controller.rebuild_websign_tracker()
            
            # Update tag cloud if tag data was changed
            if tag_changed:
                self.update_sidebar_counts()
            
            QMessageBox.information(self, "Edit", "Row data updated successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Failed to update row: {str(e)}")
    
    def set_cell_text(self, row, column, text):
        """Set text for specific cell"""
        item = self.table.item(row, column)
        if item:
            item.setText(text)
        else:
            new_item = QTableWidgetItem(text)
            self.table.setItem(row, column, new_item)

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