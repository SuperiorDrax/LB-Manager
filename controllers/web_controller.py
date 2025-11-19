from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal
import requests
from bs4 import BeautifulSoup
import webbrowser
import os
from utils.user_agents import get_random_user_agent
from utils.helpers import fetch_zip_numbers_from_directory, save_numbers_to_file

class WebController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        # Initialize settings values
        self.jm_website_value = self.config_manager.get_jm_website()
        self.dist_website_value = self.config_manager.get_dist_website()
        self.lib_path_value = self.config_manager.get_lib_path()
    
    def show_web_setting_dialog(self):
        """Show web setting configuration dialog"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Web Setting")
        dialog.setModal(True)
        dialog.resize(450, 200)
        
        layout = QVBoxLayout()
        
        # Dist Website setting row
        dist_website_layout = QHBoxLayout()
        dist_website_label = QLabel("Dist Website:")
        dist_website_input = QLineEdit()
        dist_website_input.setText(self.dist_website_value)
        
        dist_website_layout.addWidget(dist_website_label)
        dist_website_layout.addWidget(dist_website_input)
        
        # JM Website setting row with refresh button
        jm_website_layout = QHBoxLayout()
        jm_website_label = QLabel("JM Website:")
        jm_website_input = QLineEdit()
        jm_website_input.setText(self.jm_website_value)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.setFixedWidth(80)
        
        jm_website_layout.addWidget(jm_website_label)
        jm_website_layout.addWidget(jm_website_input)
        jm_website_layout.addWidget(refresh_button)
        
        # Buttons
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        
        # Add all layouts to main layout
        layout.addLayout(dist_website_layout)
        layout.addLayout(jm_website_layout)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Connect signals
        def save_settings():
            new_dist_website = dist_website_input.text().strip()
            new_jm_website = jm_website_input.text().strip()
            
            if new_dist_website and new_jm_website:
                self.dist_website_value = new_dist_website
                self.jm_website_value = new_jm_website
                self.config_manager.set_dist_website(new_dist_website)
                self.config_manager.set_jm_website(new_jm_website)
                QMessageBox.information(self.main_window, "Settings Saved", 
                                    f"Dist Website: {new_dist_website}\n"
                                    f"JM Website: {new_jm_website}")
                dialog.accept()
            else:
                QMessageBox.warning(self.main_window, "Invalid Input", "Both website fields cannot be empty.")
        
        def on_refresh_clicked():
            """Fetch website content and extract JM website asynchronously"""
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt
            
            try:
                dist_website = dist_website_input.text().strip()
                if not dist_website:
                    QMessageBox.warning(dialog, "Refresh Error", "Dist Website cannot be empty.")
                    return
                
                # Disable refresh button during operation
                refresh_button.setEnabled(False)
                refresh_button.setText("Refreshing...")
                
                # Use QProgressDialog which automatically manages its lifecycle
                progress_dialog = QProgressDialog("Fetching website content...", "Cancel", 0, 0, dialog)
                progress_dialog.setWindowTitle("Refreshing")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.show()
                
                def on_refresh_finished(message, jm_url):
                    progress_dialog.close()
                    refresh_button.setEnabled(True)
                    refresh_button.setText("Refresh")
                    jm_website_input.setText(jm_url)
                    QMessageBox.information(dialog, "Refresh Success", message)
                
                def on_refresh_error(error_msg):
                    progress_dialog.close()
                    refresh_button.setEnabled(True)
                    refresh_button.setText("Refresh")
                    QMessageBox.critical(dialog, "Refresh Error", error_msg)
                
                # Create and start background thread
                refresh_thread = WebsiteRefreshThread(dist_website)
                refresh_thread.finished.connect(on_refresh_finished)
                refresh_thread.error.connect(on_refresh_error)
                refresh_thread.start()
                
                # Store thread reference
                dialog._refresh_thread = refresh_thread
                
            except Exception as e:
                if 'progress_dialog' in locals():
                    progress_dialog.close()
                refresh_button.setEnabled(True)
                refresh_button.setText("Refresh")
                QMessageBox.critical(dialog, "Refresh Error", f"Failed to start refresh: {str(e)}")
        
        def on_dialog_close():
            """Clean up resources when dialog closes"""
            if hasattr(dialog, 'refresh_thread') and dialog.refresh_thread.isRunning():
                dialog.refresh_thread.terminate()
                dialog.refresh_thread.wait()
            
            if hasattr(dialog, 'progress_msg') and dialog.progress_msg:
                dialog.progress_msg.close()
        
        confirm_button.clicked.connect(save_settings)
        cancel_button.clicked.connect(dialog.reject)
        refresh_button.clicked.connect(on_refresh_clicked)

        dialog.finished.connect(on_dialog_close)
        dialog.exec()

    def show_lib_setting_dialog(self):
        """Show library path setting dialog"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Lib Setting")
        dialog.setModal(True)
        dialog.resize(550, 150)
        
        layout = QVBoxLayout()
        
        # Lib Path setting row
        lib_path_layout = QHBoxLayout()
        lib_path_label = QLabel("Lib Path:")
        lib_path_input = QLineEdit()
        lib_path_input.setText(self.lib_path_value)
        
        browse_button = QPushButton("Browse")
        fetch_button = QPushButton("Fetch")
        
        for button in [browse_button, fetch_button]:
            button.setFixedWidth(80)
        
        lib_path_layout.addWidget(lib_path_label)
        lib_path_layout.addWidget(lib_path_input)
        lib_path_layout.addWidget(browse_button)
        lib_path_layout.addWidget(fetch_button)
        
        # Action buttons
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(lib_path_layout)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Signal connections
        def on_browse_clicked():
            folder_path = QFileDialog.getExistingDirectory(
                dialog, "Select Library Folder", self.lib_path_value or ""
            )
            if folder_path:
                lib_path_input.setText(folder_path)
        
        def on_fetch_clicked():
            """Fetch all integer numbers from ZIP files"""
            lib_path = lib_path_input.text().strip()
            if not lib_path:
                QMessageBox.warning(dialog, "Fetch Error", "Library path cannot be empty.")
                return
            
            try:
                if not os.path.exists(lib_path):
                    raise FileNotFoundError(f"Library path does not exist: {lib_path}")
                
                if not os.path.isdir(lib_path):
                    raise ValueError(f"Library path is not a directory: {lib_path}")
                
                if not os.access(lib_path, os.R_OK):
                    raise PermissionError(f"No read permission for library path: {lib_path}")
                
                numbers = fetch_zip_numbers_from_directory(lib_path)
                save_numbers_to_file(numbers)
                
                QMessageBox.information(dialog, "Fetch Complete", 
                                    f"Successfully fetched {len(numbers)} numbers.\nSaved to: ./nums.txt")
            
            except PermissionError as e:
                QMessageBox.critical(dialog, "Permission Error", 
                                f"Cannot access library path:\n{str(e)}\n\nPlease check folder permissions.")
            except FileNotFoundError as e:
                QMessageBox.critical(dialog, "Path Not Found", 
                                f"Library path not found:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(dialog, "Fetch Error", f"Failed to fetch numbers: {str(e)}")
        
        def save_settings():
            new_lib_path = lib_path_input.text().strip()
            if new_lib_path:
                self.lib_path_value = new_lib_path
                self.config_manager.set_lib_path(new_lib_path)
                QMessageBox.information(self.main_window, "Settings Saved", f"Library path saved:\n{new_lib_path}")
                dialog.accept()
            else:
                QMessageBox.warning(self.main_window, "Invalid Input", "Library path cannot be empty.")
        
        browse_button.clicked.connect(on_browse_clicked)
        fetch_button.clicked.connect(on_fetch_clicked)
        confirm_button.clicked.connect(save_settings)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def show_view_setting_dialog(self):
        """Show view setting configuration dialog"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("View Setting")
        dialog.setModal(True)
        dialog.resize(400, 150)
        
        layout = QVBoxLayout()
        
        # Slide speed setting row
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Slide Speed (seconds):")
        speed_input = QLineEdit()
        # Ensure we get float value and convert to string for display
        current_speed = self.config_manager.get_slide_speed()
        speed_input.setText(str(current_speed))
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(speed_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("Confirm")
        cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        
        # Add all layouts to main layout
        layout.addLayout(speed_layout)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Connect signals
        def save_settings():
            try:
                speed_value = float(speed_input.text().strip())
                if speed_value <= 0:
                    QMessageBox.warning(dialog, "Invalid Input", "Slide speed must be greater than 0.")
                    return
                
                self.config_manager.set_slide_speed(speed_value)
                QMessageBox.information(self.main_window, "Settings Saved", 
                                    f"Slide speed set to: {speed_value} seconds")
                dialog.accept()
                
            except ValueError:
                QMessageBox.warning(dialog, "Invalid Input", "Please enter a valid number.")
        
        confirm_button.clicked.connect(save_settings)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()

    def view_online(self, row):
        """Open selected row data in web browser using JM website and websign"""
        try:
            # Get websign from selected row (now column 0)
            websign_item = self.main_window.table.item(row, 0)  # websign is now first column
            if not websign_item or not websign_item.text():
                QMessageBox.warning(self.main_window, "View Online", "No websign found in selected row.")
                return
            
            websign = websign_item.text()
            
            # Use current website value (loaded from config)
            website = self.jm_website_value
            
            # Construct URL
            url = f"https://{website}/album/{websign}"
            
            # Open URL in default web browser
            webbrowser.open(url)
            
            QMessageBox.information(self.main_window, "View Online", f"Opening URL in browser:\n{url}")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "View Online Error", f"Failed to open URL: {str(e)}")

    def view_zip_images(self, row):
        """Complete ZIP image viewing process with delete option for missing files"""
        try:
            # 1. Get websign
            websign_item = self.main_window.table.item(row, 0)
            if not websign_item or not websign_item.text():
                QMessageBox.warning(self.main_window, "View Error", "No websign found in selected row.")
                return
            
            websign = websign_item.text()
            
            # 2. Check lib path configuration
            if not self.lib_path_value or not os.path.exists(self.lib_path_value):
                QMessageBox.warning(self.main_window, "View Error", 
                                "Library path is not set or does not exist.\nPlease configure it in Lib Settings.")
                return
            
            # 3. Search for ZIP file using FileLocator
            from utils.file_locator import find_zip_by_websign
            zip_path = find_zip_by_websign(websign, self.lib_path_value)
            
            if not zip_path:
                # File not found - ask user if they want to delete the row
                reply = QMessageBox.question(
                    self.main_window,
                    "File Not Found",
                    f"ZIP file '{websign}.zip' not found in library.\n\n"
                    f"Do you want to delete this row from the table?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Call TableVisualManager to delete the row
                    self.main_window.visual_manager.delete_rows([row])
                return
            
            # 4. Get latest slide speed setting from config
            current_slide_speed = self.config_manager.get_slide_speed()
            
            # 5. Launch image viewer with latest settings
            from views.image_viewer import open_zip_image_viewer
            viewer = open_zip_image_viewer(zip_path, self.main_window, current_slide_speed)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "View Error", f"Failed to view ZIP images: {str(e)}")

class WebsiteRefreshThread(QThread):
    """Background thread for website refresh operation"""
    finished = pyqtSignal(str, str)  # success_message, jm_website
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, dist_website):
        super().__init__()
        self.dist_website = dist_website
    
    def run(self):
        try:
            # Fetch website content
            headers = {
                'User-Agent': get_random_user_agent()
            }
            
            url = f"https://{self.dist_website}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            china_section = soup.select_one('div.china span')
            
            if china_section:
                jm_url = china_section.get_text().strip()
                # Extract domain from URL
                if jm_url.startswith('https://'):
                    jm_url = jm_url[8:]
                elif jm_url.startswith('http://'):
                    jm_url = jm_url[7:]
                
                self.finished.emit(f"JM Website updated to: {jm_url}", jm_url)
            else:
                self.error.emit("Could not find the target element on the webpage.")
                
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.error.emit(f"Unexpected error: {str(e)}")

