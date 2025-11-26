from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QMessageBox, QFileDialog, 
                           QProgressDialog, QTableWidgetItem)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
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

        # Cover image cache
        self.cover_cache = {}
        self.max_cache_size = 100
    
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

    def get_cover_image(self, websign):
        """Get cover image for websign"""
        try:
            # Check cache first
            cache_key = str(websign)
            if cache_key in self.cover_cache:
                return self.cover_cache[cache_key]
            
            # Find ZIP file path
            zip_path = self.find_zip_file_by_websign(websign)
            if not zip_path:
                return None
            
            # Extract cover image
            from models.zip_image_manager import ZipImageManager
            zip_manager = ZipImageManager()
            cover_pixmap = zip_manager.extract_cover_image(zip_path)
            
            if cover_pixmap:
                # Add to cache (with basic cache management)
                if len(self.cover_cache) >= self.max_cache_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self.cover_cache))
                    del self.cover_cache[oldest_key]
                
                self.cover_cache[cache_key] = cover_pixmap
            
            return cover_pixmap
            
        except Exception as e:
            print(f"Error getting cover image for {websign}: {e}")
            return None

    def find_zip_file_by_websign(self, websign):
        """Find ZIP file path by websign number"""
        lib_path = self.config_manager.get_lib_path()
        if not lib_path or not os.path.exists(lib_path):
            return None
        
        # Search for ZIP file with websign as filename
        zip_filename = f"{websign}.zip"
        
        for root, dirs, files in os.walk(lib_path):
            if zip_filename in files:
                return os.path.join(root, zip_filename)
        
        return None

    def view_online(self, rows):
        """View rows online - supports both single row and multiple rows"""
        if not isinstance(rows, list):
            rows = [rows]  # Convert single row to list
        
        for row in rows:
            try:
                # Existing single row logic
                websign_item = self.main_window.table.item(row, 0)
                if not websign_item:
                    continue
                    
                websign = websign_item.data(Qt.ItemDataRole.UserRole)
                if not websign:
                    websign = websign_item.text()
                    
                if not websign:
                    continue
                    
                jm_website = self.config_manager.get_jm_website()
                if not jm_website:
                    QMessageBox.warning(self.main_window, "View Error", "JM website is not configured.")
                    continue
                    
                url = f"https://{jm_website}/album/{websign}"
                webbrowser.open(url)
                
            except Exception as e:
                print(f"Error viewing online for row {row}: {e}")

    def view_zip_images(self, rows):
        """View ZIP images for rows - supports both single row and multiple rows"""
        if not isinstance(rows, list):
            rows = [rows]  # Convert single row to list
        
        # For multiple rows, open the first one (or could implement multi-viewer)
        if rows:
            self._view_single_zip_image(rows[0])

    def _view_single_zip_imag(self, row):
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
            
            # 6. Connect progress tracking signals
            self.setup_progress_tracking(viewer, row, zip_path)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "View Error", f"Failed to view ZIP images: {str(e)}")

    def setup_progress_tracking(self, viewer, row, zip_path):
        """Setup automatic progress tracking for the image viewer"""
        # Store the row index for progress updates
        viewer.row_index = row
        
        # Monkey patch the key methods to include progress updates
        original_next_image = viewer.next_image
        original_previous_image = viewer.previous_image
        original_jump_to_image = viewer.jump_to_image
        original_close_event = viewer.closeEvent
        original_display_current_image = viewer.display_current_image
        
        def patched_next_image():
            result = original_next_image()
            self.update_viewer_progress(viewer)
            return result
        
        def patched_previous_image():
            result = original_previous_image()
            self.update_viewer_progress(viewer)
            return result
        
        def patched_jump_to_image(target_index):
            result = original_jump_to_image(target_index)
            self.update_viewer_progress(viewer)
            return result
        
        def patched_display_current_image():
            result = original_display_current_image()
            self.update_viewer_progress(viewer)
            return result
        
        def patched_close_event(event):
            # Save final progress before closing
            self.update_viewer_progress(viewer, is_final=True)
            original_close_event(event)
        
        # Apply the patches
        viewer.next_image = patched_next_image
        viewer.previous_image = patched_previous_image
        viewer.jump_to_image = patched_jump_to_image
        viewer.display_current_image = patched_display_current_image
        viewer.closeEvent = patched_close_event
        
        # Initial progress update
        self.update_viewer_progress(viewer)

    def update_viewer_progress(self, viewer, is_final=False):
        """Update reading progress based on current viewer state"""
        try:
            if not hasattr(viewer, 'row_index'):
                return
            
            row = viewer.row_index
            image_manager = viewer.image_manager
            
            if image_manager.has_images():
                current_index = image_manager.get_current_index()
                total_images = image_manager.get_image_count()
                
                if total_images > 0:
                    # Calculate progress percentage (integer only)
                    progress = int((current_index / total_images) * 100)
                    
                    # Update progress in table
                    self.main_window.table_controller.update_progress(row, progress)
                    
                    # If this is the final update and user reached the end, mark as completed
                    if is_final and current_index == total_images - 1:
                        self.main_window.table_controller.update_progress(row, 100)
                        
        except Exception as e:
            print(f"Error updating viewer progress: {e}")
    
    def update_tag_for_row(self, rows):
        """Update tags for rows using universal thread class"""
        if not isinstance(rows, list):
            rows = [rows]
        
        if not rows:
            return
        
        is_batch = len(rows) > 1
        
        try:
            # Configure progress dialog based on operation type
            if is_batch:
                progress_text = f"Fetching tags for {len(rows)} items..."
                progress_dialog = QProgressDialog(progress_text, "Cancel", 0, len(rows), self.main_window)
            else:
                progress_text = f"Fetching tags for websign {self.get_websign_from_row(rows[0])}..."
                progress_dialog = QProgressDialog(progress_text, "Cancel", 0, 0, self.main_window)
            
            progress_dialog.setWindowTitle("Updating Tags" if is_batch else "Updating Tag")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()
            
            # Create and start universal thread
            self.tag_fetch_thread = TagFetchThread(rows, self.main_window, self.config_manager, is_batch)
            
            # Connect signals based on operation type
            if is_batch:
                self.tag_fetch_thread.progress_updated.connect(progress_dialog.setValue)
                self.tag_fetch_thread.batch_finished.connect(lambda: self.on_batch_tags_finished(progress_dialog))
            else:
                self.tag_fetch_thread.single_finished.connect(lambda row, tags: self.on_single_tag_finished(row, tags, progress_dialog))
            
            self.tag_fetch_thread.error.connect(lambda error: self.on_tag_fetch_error(error, progress_dialog, is_batch))
            self.tag_fetch_thread.start()
            
            # Connect cancel button for batch operations
            if is_batch:
                progress_dialog.canceled.connect(self.tag_fetch_thread.cancel)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Update Tag Error", f"Failed to start tag update: {str(e)}")

    def on_single_tag_finished(self, row, tags, progress_dialog):
        """Handle single tag fetch completion"""
        progress_dialog.close()
        
        if tags:
            tag_text = ", ".join(tags)
            tag_item = QTableWidgetItem(tag_text)
            self.main_window.table.setItem(row, 7, tag_item)
            QMessageBox.information(self.main_window, "Update Tag", 
                                f"Successfully updated tags for websign {self.get_websign_from_row(row)}:\n\n{tag_text}")
        else:
            QMessageBox.information(self.main_window, "Update Tag", 
                                f"No tags found for websign {self.get_websign_from_row(row)}")

    def on_batch_tags_finished(self, progress_dialog):
        """Handle batch tag update completion"""
        progress_dialog.close()
        QMessageBox.information(self.main_window, "Update Tags", "Batch tag update completed!")

    def on_tag_fetch_error(self, error_msg, progress_dialog, is_batch):
        """Handle tag fetch error"""
        progress_dialog.close()
        operation_type = "batch tag update" if is_batch else "tag update"
        QMessageBox.critical(self.main_window, "Update Tag Error", f"Failed to {operation_type}: {error_msg}")

    def get_websign_from_row(self, row):
        """Helper method to get websign from row"""
        websign_item = self.main_window.table.item(row, 0)
        if websign_item:
            websign = websign_item.data(Qt.ItemDataRole.UserRole)
            if not websign:
                websign = websign_item.text()
            return websign
        return ""

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

class TagFetchThread(QThread):
    """Universal tag fetching thread, supports both single row and batch operations"""
    progress_updated = pyqtSignal(int)  # Progress update
    single_finished = pyqtSignal(int, list)  # Single row completed: row index, tag list
    batch_finished = pyqtSignal()  # Batch completed
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, rows, main_window, config_manager, is_batch=False):
        super().__init__()
        self.rows = rows if isinstance(rows, list) else [rows]
        self.main_window = main_window
        self.config_manager = config_manager
        self.is_batch = is_batch
        self.cancelled = False
    
    def run(self):
        """Main execution method"""
        try:
            jm_website = self.config_manager.get_jm_website()
            if not jm_website:
                self.error.emit("JM website is not configured.")
                return
            
            for i, row in enumerate(self.rows):
                if self.cancelled:
                    break
                    
                # Get websign for current row
                websign_item = self.main_window.table.item(row, 0)
                if not websign_item:
                    continue
                    
                websign = websign_item.data(Qt.ItemDataRole.UserRole)
                if not websign:
                    websign = websign_item.text()
                
                if not websign:
                    continue
                
                # Fetch tags from website
                url = f"https://{jm_website}/album/{websign}"
                tags = self.fetch_tags_from_url(url)
                
                if self.is_batch:
                    # Batch mode: update table directly
                    if tags:
                        tag_text = ", ".join(tags)
                        tag_item = QTableWidgetItem(tag_text)
                        self.main_window.table.setItem(row, 7, tag_item)
                else:
                    # Single mode: emit signal for UI update
                    self.single_finished.emit(row, tags if tags else [])
                
                # Update progress
                self.progress_updated.emit(i + 1)
                
                # Small delay to avoid overwhelming the server
                if self.is_batch and i < len(self.rows) - 1:
                    self.msleep(500)
            
            # Emit completion signal
            if self.is_batch:
                self.batch_finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
    
    def fetch_tags_from_url(self, url):
        """Fetch tags from website using CSS selector"""
        try:
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extract tags using CSS selector
            soup = BeautifulSoup(response.text, 'html.parser')
            tag_elements = soup.select('span[data-type="tags"] a.btn.phone-tags-tag')
            
            tags = []
            for tag_element in tag_elements:
                tag_text = tag_element.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            
            return tags
            
        except Exception as e:
            print(f"Error fetching tags from {url}: {e}")
            return None
    
    def cancel(self):
        """Cancel the operation"""
        self.cancelled = True