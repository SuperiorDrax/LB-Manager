from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QPushButton, QMessageBox, QMenu, QDialog, QLineEdit, QFileDialog, QApplication
from PyQt6.QtCore import Qt, QTimer
from models.config_manager import ConfigManager
from models.data_parser import DataParser
from views.dialogs import InsertDialog, SearchDialog
from controllers.file_io import FileIO
from controllers.table_controller import TableController
from controllers.state_manager import StateManager
from controllers.web_controller import WebController
from controllers.table_visual_manager import TableVisualManager
from views.enhanced_table import EnhancedTableWidget
import os
import re
import requests
from bs4 import BeautifulSoup
from utils.user_agents import get_random_user_agent

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set default window size before restoring state
        self.resize(870, 500)  # Larger default size
        
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
        
        # Restore window state (may override default size)
        self.state_manager.restore_window_state()
        
        self.init_ui()

        self.table_controller.rebuild_websign_tracker()
    
    def init_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Main layout
        layout = QVBoxLayout()
        
        # Create table using enhanced version
        self.table = EnhancedTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag'
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
        
        # Enable other table features
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Create buttons
        button_layout = QHBoxLayout()
        self.insert_button = QPushButton("Insert")
        self.search_button = QPushButton("Search")
        self.search_button.setToolTip("Search (Ctrl+F)")
        self.clear_button = QPushButton("Clear")
        
        button_layout.addWidget(self.insert_button)
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        
        # Add widgets to layout
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        
        central_widget.setLayout(layout)

        # Enable sorting and column dragging
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable column reordering and header context menu
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.visual_manager.show_header_context_menu)
        
        # Connect signals
        self.table.horizontalHeader().sectionResized.connect(self.state_manager.on_column_resized)
        self.table.horizontalHeader().sectionMoved.connect(self.state_manager.on_column_moved)
        
        # Connect signals
        self.insert_button.clicked.connect(self.show_insert_dialog)
        self.search_button.clicked.connect(self.show_search_dialog)
        self.clear_button.clicked.connect(self.clear_table)
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        import_action = file_menu.addAction("Import")
        save_action = file_menu.addAction("Save")
        exit_action = file_menu.addAction("Exit")
        
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

    def show_about_dialog(self):
        """Show about information"""
        QMessageBox.about(self, "About", "Author: Deepseek")

    def show_context_menu(self, position):
        """Show right-click context menu"""
        # Get clicked row
        row = self.table.rowAt(position.y())
        if row < 0:
            return
            
        # Create context menu
        context_menu = QMenu(self)
        
        view_zip_action = context_menu.addAction("View")
        view_online_action = context_menu.addAction("View online")
        update_tag_action = context_menu.addAction("Update Tag")
        copy_action = context_menu.addAction("Copy to clipboard")
        delete_action = context_menu.addAction("Delete")
        
        # Connect signals
        copy_action.triggered.connect(lambda: self.visual_manager.copy_row_to_clipboard(row))
        view_online_action.triggered.connect(lambda: self.web_controller.view_online(row))
        view_zip_action.triggered.connect(lambda: self.web_controller.view_zip_images(row))
        delete_action.triggered.connect(lambda: self.visual_manager.delete_rows([row]))
        update_tag_action.triggered.connect(lambda: self.web_controller.update_tag_for_row(row))
        
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
                    data_list[-1] = tag_text
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
                self.table_controller.filter_table(options)
    
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
            # Clear sorting state when table is cleared
            self.table.clear_all_sorting()
    
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
        """Ensure thread is properly cleaned up"""
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