from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QStatusBar, 
                           QMessageBox, QScrollArea, QLineEdit,
                           QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QIntValidator
from models.zip_image_manager import ZipImageManager
import os

class ImageViewer(QMainWindow):
    """
    Main image viewer window for browsing images in ZIP files
    Provides navigation, zoom, and basic image viewing functionality
    """
    
    def __init__(self, parent=None, slide_speed=1.0):
        super().__init__(parent)
        self.image_manager = ZipImageManager()
        self.current_scale = 1.0
        self.fit_timer = QTimer()
        self.fit_timer.setSingleShot(True)
        
        # Slideshow properties
        self.slideshow_timer = QTimer()
        self.slideshow_interval = int(slide_speed * 1000)  # Convert to milliseconds
        self.slideshow_direction = 1
        self.is_slideshow_active = False
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ZIP Image Viewer")
        self.setGeometry(100, 100, 900, 650)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("QLabel { background-color: #2b2b2b; }")
        self.image_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        main_layout.addWidget(self.image_label)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        
        # Jump to section
        jump_layout = QHBoxLayout()
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(40)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999))
        self.total_pages_label = QLabel("/ 0")
        self.jump_button = QPushButton("Jump To")
        
        jump_layout.addWidget(self.page_input)
        jump_layout.addWidget(self.total_pages_label)
        jump_layout.addWidget(self.jump_button)
        
        # Slideshow controls
        self.slideshow_button = QPushButton("Play")
        self.slideshow_button.setCheckable(True)
        
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")
        self.fit_button = QPushButton("Fit")
        self.actual_size_button = QPushButton("Actual Size")
        
        # Set button sizes and focus policy
        for button in [self.prev_button, self.next_button, self.jump_button,
                    self.slideshow_button, self.zoom_in_button, self.zoom_out_button, 
                    self.fit_button, self.actual_size_button]:
            button.setFixedWidth(80)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.next_button)
        control_layout.addLayout(jump_layout)
        control_layout.addWidget(self.slideshow_button)  # Add slideshow button
        control_layout.addStretch()
        control_layout.addWidget(self.zoom_in_button)
        control_layout.addWidget(self.zoom_out_button)
        control_layout.addWidget(self.fit_button)
        control_layout.addWidget(self.actual_size_button)
        
        main_layout.addLayout(control_layout)

        # Control buttons
        edit_layout = QHBoxLayout()

        self.stitch_button = QPushButton("Stitch with Next")
        self.stitch_button.setFixedWidth(120)
        self.stitch_button.setStyleSheet("QPushButton { background-color: #4a90e2; color: white; }")
        self.stitch_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stitch_button.setToolTip("Stitch current image with next image (Ctrl+M)")
        
        self.delete_current_button = QPushButton("Delete Current")
        self.delete_current_button.setFixedWidth(100)
        self.delete_current_button.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        self.delete_current_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.batch_delete_button = QPushButton("Batch Delete...")
        self.batch_delete_button.setFixedWidth(100)
        self.batch_delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.undo_delete_button = QPushButton("Undo")
        self.undo_delete_button.setFixedWidth(80)  # 稍微减小宽度
        self.undo_delete_button.setEnabled(False)
        self.undo_delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_delete_button.setToolTip("Undo last operation (Ctrl+Z)")
        
        self.commit_button = QPushButton("Save Changes")
        self.commit_button.setFixedWidth(100)
        self.commit_button.setStyleSheet("QPushButton { background-color: #51a351; color: white; }")
        self.commit_button.setEnabled(False)
        self.commit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        edit_layout.addWidget(self.stitch_button)
        edit_layout.addWidget(self.delete_current_button)
        edit_layout.addWidget(self.batch_delete_button)
        edit_layout.addWidget(self.undo_delete_button)
        edit_layout.addStretch()
        edit_layout.addWidget(self.commit_button)
        
        main_layout.addLayout(edit_layout)
        
        # Thumbnail navigation bar
        self.create_thumbnail_bar()
        main_layout.addWidget(self.thumbnail_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
    
    def create_thumbnail_bar(self):
        """Create thumbnail navigation bar"""
        self.thumbnail_widget = QWidget()
        self.thumbnail_widget.setFixedHeight(100)
        self.thumbnail_widget.setStyleSheet("QWidget { background-color: #1a1a1a; }")
        
        thumbnail_layout = QHBoxLayout(self.thumbnail_widget)
        thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        thumbnail_layout.setSpacing(3)
        
        # Scroll area for thumbnails
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setFixedHeight(90)
        
        # Container for thumbnail buttons with centered alignment
        self.thumbnail_container = QWidget()
        self.thumbnail_container_layout = QHBoxLayout(self.thumbnail_container)
        self.thumbnail_container_layout.setContentsMargins(2, 2, 2, 2)
        self.thumbnail_container_layout.setSpacing(3)
        self.thumbnail_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Changed to center
        
        self.thumbnail_scroll.setWidget(self.thumbnail_container)
        thumbnail_layout.addWidget(self.thumbnail_scroll)
        
        # Store thumbnail buttons for easy access
        self.thumbnail_buttons = []

    def create_thumbnails(self):
        """Create thumbnail buttons for all images"""
        # Clear existing thumbnails
        for button in self.thumbnail_buttons:
            self.thumbnail_container_layout.removeWidget(button)
            button.deleteLater()
        self.thumbnail_buttons.clear()
        
        if not self.image_manager.has_images():
            return
        
        image_list = self.image_manager.get_image_list()
        
        for index, (_, display_name) in enumerate(image_list):
            thumbnail_btn = QPushButton()
            thumbnail_btn.setFixedSize(70, 70)  # Reduced from 80x80 to 70x70
            thumbnail_btn.setCheckable(True)
            thumbnail_btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #555;
                    background-color: #333;
                }
                QPushButton:checked {
                    border: 2px solid #0078d7;
                }
                QPushButton:hover {
                    border: 2px solid #888;
                }
            """)
            
            # Load thumbnail image
            self.load_thumbnail_image(thumbnail_btn, index, display_name)
            
            # Connect click event
            thumbnail_btn.clicked.connect(lambda checked, idx=index: self.thumbnail_clicked(idx))
            
            self.thumbnail_container_layout.addWidget(thumbnail_btn)
            self.thumbnail_buttons.append(thumbnail_btn)
        
        # Highlight current image
        self.update_thumbnail_selection()

    def create_thumbnail_bar(self):
        """Create thumbnail navigation bar"""
        self.thumbnail_widget = QWidget()
        self.thumbnail_widget.setFixedHeight(100)
        self.thumbnail_widget.setStyleSheet("QWidget { background-color: #1a1a1a; }")
        
        thumbnail_layout = QHBoxLayout(self.thumbnail_widget)
        thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        thumbnail_layout.setSpacing(3)
        
        # Scroll area for thumbnails
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setFixedHeight(90)
        
        # Container for thumbnail buttons with centered alignment
        self.thumbnail_container = QWidget()
        self.thumbnail_container_layout = QHBoxLayout(self.thumbnail_container)
        self.thumbnail_container_layout.setContentsMargins(2, 2, 2, 2)
        self.thumbnail_container_layout.setSpacing(3)
        self.thumbnail_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.thumbnail_scroll.setWidget(self.thumbnail_container)
        thumbnail_layout.addWidget(self.thumbnail_scroll)
        
        # Store thumbnail buttons for easy access
        self.thumbnail_buttons = []

    def load_thumbnail_image(self, button, index, display_name):
        """Load and set thumbnail image for button"""
        # Save current index and temporarily navigate to target image
        current_index = self.image_manager.get_current_index()
        if self.image_manager.navigate_to_image(index):
            pixmap = self.image_manager.get_current_image_pixmap()
            if pixmap and not pixmap.isNull():
                # Scale to thumbnail size
                thumbnail = pixmap.scaled(66, 66, Qt.AspectRatioMode.KeepAspectRatio, 
                                Qt.TransformationMode.SmoothTransformation)
                button.setIcon(QIcon(thumbnail))
                button.setIconSize(thumbnail.size())
        
        # Restore original position
        self.image_manager.navigate_to_image(current_index)
        button.setToolTip(f"{display_name}\nClick to view")

    def thumbnail_clicked(self, index):
        """Handle thumbnail click event"""
        if self.image_manager.navigate_to_image(index):
            self.display_current_image()
            self.update_thumbnail_selection()
            self.update_navigation_buttons()

    def update_thumbnail_selection(self):
        """Update thumbnail selection state and scroll to center"""
        current_index = self.image_manager.get_current_index()
        for i, button in enumerate(self.thumbnail_buttons):
            button.setChecked(i == current_index)
        
        # Scroll to center current thumbnail
        self.scroll_to_current_thumbnail()
    
    def scroll_to_current_thumbnail(self):
        """Scroll to make current thumbnail centered in view"""
        if not self.thumbnail_buttons or self.image_manager.get_current_index() < 0:
            return
        
        current_index = self.image_manager.get_current_index()
        if current_index < len(self.thumbnail_buttons):
            # Calculate scroll position to center the current thumbnail
            scrollbar = self.thumbnail_scroll.horizontalScrollBar()
            thumbnail_width = 70  # Thumbnail button width
            spacing = 3  # Layout spacing
            total_width = thumbnail_width + spacing
            
            # Calculate desired scroll position
            scroll_area_width = self.thumbnail_scroll.width()
            target_scroll = current_index * total_width - (scroll_area_width - total_width) / 2
            
            # Ensure scroll position is within valid range
            max_scroll = len(self.thumbnail_buttons) * total_width - scroll_area_width
            target_scroll = max(0, min(target_scroll, max_scroll))
            
            scrollbar.setValue(int(target_scroll))
       
    def connect_signals(self):
        """Connect signals and slots"""
        # Button connections
        self.prev_button.clicked.connect(self.previous_image)
        self.next_button.clicked.connect(self.next_image)
        self.jump_button.clicked.connect(self.jump_to_input_page)
        self.page_input.returnPressed.connect(self.jump_to_input_page)
        self.slideshow_button.toggled.connect(self.toggle_slideshow)
        
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.fit_button.clicked.connect(self.fit_to_window)
        self.actual_size_button.clicked.connect(self.actual_size)

        # New stitch button connection
        self.stitch_button.clicked.connect(self.stitch_with_next)

        # New delete button connections
        self.delete_current_button.clicked.connect(self.delete_current_image)
        self.batch_delete_button.clicked.connect(self.batch_delete_images)
        self.undo_delete_button.clicked.connect(self.undo_last_deletion)
        self.commit_button.clicked.connect(self.commit_deletions)
        
        # Image manager signals
        self.image_manager.images_loaded.connect(self.on_images_loaded)
        self.image_manager.load_error.connect(self.on_load_error)
        
        # Timer connections
        self.fit_timer.timeout.connect(self.fit_to_window)
        self.slideshow_timer.timeout.connect(self.slideshow_next)
        
    def load_zip_file(self, zip_path: str):
        """Load ZIP file and display images"""
        self.setWindowTitle(f"ZIP Image Viewer - Loading...")
        self.status_bar.showMessage("Loading ZIP file...")
        
        # Load ZIP file
        success = self.image_manager.load_zip_file(zip_path)
        if success:
            self.setWindowTitle(f"ZIP Image Viewer - {os.path.basename(zip_path)}")
        else:
            # Error will be handled by signal
            pass
    
    @pyqtSlot(int)
    def on_images_loaded(self, image_count: int):
        """Handle images loaded signal"""
        if image_count > 0:
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_page_display()
            self.image_label.setFocus()
            
            # Create thumbnails
            self.create_thumbnails()
            
            # Initialize delete buttons
            self.update_delete_buttons()
            
            # Delay fit to window and initial scroll
            self.fit_timer.start(100)
            QTimer.singleShot(150, self.scroll_to_current_thumbnail)
        else:
            QMessageBox.warning(self, "No Images", "No images found in the ZIP file.")
    
    @pyqtSlot(str)
    def on_load_error(self, error_message: str):
        """Handle load error signal"""
        QMessageBox.critical(self, "Load Error", error_message)
        self.status_bar.showMessage("Load failed")
    
    def display_current_image(self):
        """Display current image with current scale"""
        if not self.image_manager.has_images():
            return
            
        pixmap = self.image_manager.get_current_image_pixmap()
        if pixmap and not pixmap.isNull():
            # Scale the pixmap
            if self.current_scale != 1.0:
                scaled_pixmap = pixmap.scaled(
                    int(pixmap.width() * self.current_scale),
                    int(pixmap.height() * self.current_scale),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setPixmap(pixmap)
            
            self.update_status_bar()
        else:
            self.image_label.setText("Failed to load image")
            self.status_bar.showMessage("Failed to load image")
    
    def jump_to_image(self, target_index):
        """Jump to specific image index"""
        if self.image_manager.navigate_to_image(target_index):
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_thumbnail_selection()
            self.image_label.setFocus()
    
    def jump_to_input_page(self):
        """Jump to page number from input field"""
        if not self.image_manager.has_images():
            return
        
        try:
            page_text = self.page_input.text().strip()
            if not page_text:
                return
                
            target_page = int(page_text)
            total_pages = self.image_manager.get_image_count()
            
            if 1 <= target_page <= total_pages:
                self.jump_to_image(target_page - 1)  # Convert to 0-based index
            else:
                QMessageBox.warning(self, "Invalid Page", 
                                f"Please enter a number between 1 and {total_pages}")
                self.update_page_display()  # Reset to current page
        
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number")
            self.update_page_display()  # Reset to current page
    
    def next_image(self):
        """Navigate to next image"""
        if self.image_manager.next_image():
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_thumbnail_selection()
            self.update_page_display()
            # Reset slideshow timer if active
            if self.is_slideshow_active:
                self.slideshow_timer.start(self.slideshow_interval)

    def previous_image(self):
        """Navigate to previous image"""
        if self.image_manager.previous_image():
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_thumbnail_selection()
            self.update_page_display()
            # Reset slideshow timer if active
            if self.is_slideshow_active:
                self.slideshow_timer.start(self.slideshow_interval)
    
    def update_navigation_buttons(self):
        """Update navigation button states"""
        if not self.image_manager.has_images():
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.stitch_button.setEnabled(False)
            return
            
        current_index, total_count, _ = self.image_manager.get_current_image_info()
        self.prev_button.setEnabled(current_index > 1)
        self.next_button.setEnabled(current_index < total_count)
        self.stitch_button.setEnabled(current_index < total_count)
    
    def update_page_display(self):
        """Update the page input and total pages display"""
        if self.image_manager.has_images():
            current_index, total_count, _ = self.image_manager.get_current_image_info()
            self.page_input.setText(str(current_index))
            self.total_pages_label.setText(f"/ {total_count}")
        else:
            self.page_input.setText("")
            self.total_pages_label.setText("/ 0")
    
    def zoom_in(self):
        """Zoom in by 25%"""
        self.current_scale *= 1.25
        self.display_current_image()
        self.status_bar.showMessage(f"Zoom: {self.current_scale:.1%}")
    
    def zoom_out(self):
        """Zoom out by 20%"""
        self.current_scale *= 0.8
        if self.current_scale < 0.1:
            self.current_scale = 0.1
        self.display_current_image()
        self.status_bar.showMessage(f"Zoom: {self.current_scale:.1%}")
    
    def fit_to_window(self):
        """Fit image to window size"""
        if not self.image_manager.has_images():
            return
            
        pixmap = self.image_manager.get_current_image_pixmap()
        if pixmap and not pixmap.isNull():
            # Calculate scale to fit window
            label_size = self.image_label.size()
            pixmap_size = pixmap.size()
            
            scale_x = label_size.width() / pixmap_size.width()
            scale_y = label_size.height() / pixmap_size.height()
            self.current_scale = min(scale_x, scale_y)
            
            self.display_current_image()
            self.status_bar.showMessage(f"Fit to window - Zoom: {self.current_scale:.1%}")
    
    def actual_size(self):
        """Display image at actual size"""
        self.current_scale = 1.0
        self.display_current_image()
        self.status_bar.showMessage("Actual size")
    
    def update_status_bar(self):
        """Update status bar with current image information and deletion status"""
        if self.image_manager.has_images():
            current_index, total_count, filename = self.image_manager.get_current_image_info()
            zoom_info = f"Zoom: {self.current_scale:.1%}"
            image_info = f"Image {current_index} of {total_count} - {filename}"
            
            # Add deletion info if available
            deletion_info = ""
            if hasattr(self.image_manager, 'deletion_history') and self.image_manager.deletion_history:
                deletion_info = f" | {len(self.image_manager.deletion_history)} deletion(s) pending"
            
            cache_info = self.image_manager.get_cache_info()
            cache_status = f"Cache: {cache_info['cache_size']}/{total_count}"
            
            self.status_bar.showMessage(f"{image_info} | {zoom_info} | {cache_status}{deletion_info}")
        else:
            self.status_bar.showMessage("No images loaded")
    
    def toggle_slideshow(self, checked):
        """Toggle slideshow playback"""
        if not self.image_manager.has_images():
            self.slideshow_button.setChecked(False)
            return
        
        if checked:
            self.start_slideshow()
        else:
            self.stop_slideshow()

    def start_slideshow(self):
        """Start slideshow playback"""
        self.is_slideshow_active = True
        self.slideshow_button.setText("Stop")
        self.slideshow_timer.start(self.slideshow_interval)
        self.status_bar.showMessage("Slideshow started - Press Space to pause")

    def stop_slideshow(self):
        """Stop slideshow playback"""
        self.is_slideshow_active = False
        self.slideshow_button.setText("Play")
        self.slideshow_button.setChecked(False)
        self.slideshow_timer.stop()
        self.status_bar.showMessage("Slideshow stopped")

    def slideshow_next(self):
        """Move to next image in slideshow"""
        if not self.is_slideshow_active:
            return
        
        current_index, total_count, _ = self.image_manager.get_current_image_info()
        
        # Check if we've reached the end
        if self.slideshow_direction == 1 and current_index >= total_count:
            self.stop_slideshow()
            return
        elif self.slideshow_direction == -1 and current_index <= 1:
            self.stop_slideshow()
            return
        
        # Navigate to next/previous image
        if self.slideshow_direction == 1:
            self.next_image()
        else:
            self.previous_image()

    def stitch_with_next(self):
        """Stitch current image with the next image"""
        if not self.image_manager.has_images():
            QMessageBox.warning(self, "No Images", "No images available for stitching.")
            return
        
        current_index, total_count, current_filename = self.image_manager.get_current_image_info()
        
        if current_index >= total_count:
            QMessageBox.warning(self, "No Next Image", "This is the last image, cannot stitch with next.")
            return
        
        # Get next image info for confirmation
        next_index = current_index  # current_index is 1-based, next is current_index (0-based in manager)
        next_filename = self.image_manager.image_files[next_index][1] if next_index < len(self.image_manager.image_files) else "Unknown"
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Stitching",
            f"Stitch current image with next image?\n\n"
            f"Current: {current_filename}\n"
            f"Next: {next_filename}\n\n"
            f"This will replace the current image with the stitched result and remove the next image.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message, stitched_image_data = self.image_manager.stitch_current_with_next()
            
            if success:
                # Update UI
                self.display_current_image()
                self.update_navigation_buttons()
                self.update_page_display()
                self.create_thumbnails()
                self.update_delete_buttons()
                
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Stitching Failed", message)

    def undo_last_deletion(self):
        """Undo the last deletion or stitching operation"""
        if not hasattr(self.image_manager, 'deletion_history') or not self.image_manager.deletion_history:
            QMessageBox.warning(self, "No Action", "No operation to undo.")
            return
        
        # Use the unified undo method in zip_image_manager
        if self.image_manager.undo_last_deletion():
            # Remove the operation from history after successful undo
            self.image_manager.deletion_history.pop()
            
            # Update UI
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_page_display()
            self.create_thumbnails()
            self.update_delete_buttons()
            
            QMessageBox.information(self, "Success", "Operation undone!")
        else:
            QMessageBox.critical(self, "Error", "Failed to undo operation.")

    def delete_current_image(self):
        """Delete the currently displayed image"""
        if not self.image_manager.has_images():
            QMessageBox.warning(self, "No Images", "No images to delete.")
            return
        
        current_index, total_count, filename = self.image_manager.get_current_image_info()
        
        # Show confirmation dialog
        dialog = DeleteConfirmationDialog(self, 1, [filename])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.image_manager.delete_current_image():
                # Update UI
                self.display_current_image()
                self.update_navigation_buttons()
                self.update_page_display()
                self.create_thumbnails()
                self.update_delete_buttons()
                
                QMessageBox.information(self, "Success", "Image deleted successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete image.")

    def batch_delete_images(self):
        """Open dialog for batch deleting multiple images"""
        if not self.image_manager.has_images():
            QMessageBox.warning(self, "No Images", "No images to delete.")
            return
        
        total_count = self.image_manager.get_image_count()
        dialog = BatchDeleteDialog(self, total_count)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            start, end = dialog.get_page_range()
            
            if start is None or end is None:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid page numbers.")
                return
            
            if start > end:
                QMessageBox.warning(self, "Invalid Range", "Start page must be less than or equal to end page.")
                return
            
            # Convert to 0-based indices
            start_index = start - 1
            end_index = end - 1
            
            # Get image names for confirmation
            image_names = []
            for i in range(start_index, end_index + 1):
                if i < len(self.image_manager.image_files):
                    image_names.append(self.image_manager.image_files[i][1])
            
            # Show confirmation dialog
            confirm_dialog = DeleteConfirmationDialog(self, end - start + 1, image_names)
            if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
                if self.image_manager.delete_images_by_range(start_index, end_index):
                    # Update UI
                    self.display_current_image()
                    self.update_navigation_buttons()
                    self.update_page_display()
                    self.create_thumbnails()
                    self.update_delete_buttons()
                    
                    QMessageBox.information(self, "Success", 
                                         f"Successfully deleted {end - start + 1} images!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete images.")

    def undo_last_deletion(self):
        """Undo the last deletion operation"""
        if self.image_manager.undo_last_deletion():
            # Update UI
            self.display_current_image()
            self.update_navigation_buttons()
            self.update_page_display()
            self.create_thumbnails()
            self.update_delete_buttons()
            
            QMessageBox.information(self, "Success", "Delete operation undone!")
        else:
            QMessageBox.warning(self, "No Action", "No deletion to undo.")

    def commit_deletions(self):
        """Commit all deletions to ZIP file and close viewer"""
        # Check if there are deletions to save
        if not hasattr(self.image_manager, 'deletion_history') or not self.image_manager.deletion_history:
            QMessageBox.information(self, "No Changes", "No deletions to save.")
            return
        
        deletion_count = len(self.image_manager.deletion_history)
        
        # Show confirmation dialog
        reply = QMessageBox.question(self, "Save Changes",
                                f"Are you sure you want to permanently delete {deletion_count} images from the ZIP file?\n\n"
                                f"This will close the image viewer and save changes.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Close ZIP file first to release file lock
            self.image_manager.close()
            
            # Then commit deletion operations
            if self.image_manager.commit_deletions_to_zip():
                QMessageBox.information(self, "Success", 
                                    f"Successfully deleted {deletion_count} images!\n\n"
                                    f"The image viewer will now close.")
                self.close()  # Close the viewer
            else:
                # If save fails, reload ZIP file
                QMessageBox.critical(self, "Error", "Failed to save changes to ZIP file.")
                # Reload ZIP file to continue viewing
                if self.image_manager.current_zip_path:
                    self.image_manager.load_zip_file(self.image_manager.current_zip_path)

    def update_delete_buttons(self):
        """Update the state of delete-related buttons"""
        # Check if there are deletions to undo or commit
        has_deletions = hasattr(self.image_manager, 'deletion_history') and self.image_manager.deletion_history
        
        self.undo_delete_button.setEnabled(bool(has_deletions))
        self.commit_button.setEnabled(bool(has_deletions))
        
        # Update status bar
        if has_deletions:
            deletion_count = len(self.image_manager.deletion_history)
            self.status_bar.showMessage(f"{deletion_count} deletion(s) pending - Remember to save changes!")
        else:
            self.update_status_bar()
    
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Left:
            self.previous_image()
        elif event.key() == Qt.Key.Key_Right:
            self.next_image()
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_slideshow(not self.is_slideshow_active)
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self.zoom_in()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key.Key_0:
            self.actual_size()
        elif event.key() == Qt.Key.Key_F:
            self.fit_to_window()
        elif event.key() == Qt.Key.Key_Delete:  # Delete current image
            self.delete_current_image()
        elif event.key() == Qt.Key.Key_M and event.modifiers() == Qt.KeyboardModifier.ControlModifier:  # Ctrl+M stitch
            self.stitch_with_next()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:  # Ctrl+Z undo
            self.undo_last_deletion()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
        self.image_label.setFocus()
        # Delay scroll to ensure layout is complete
        QTimer.singleShot(50, self.scroll_to_current_thumbnail)

    def resizeEvent(self, event):
        """Handle window resize event"""
        super().resizeEvent(event)
        # Re-center current thumbnail when window is resized
        QTimer.singleShot(50, self.scroll_to_current_thumbnail)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_slideshow()  # Ensure slideshow is stopped
        self.image_manager.close()
        event.accept()

# Convenience function
def open_zip_image_viewer(zip_path: str, parent=None, slide_speed=1.0):
    """
    Convenience function to open ZIP image viewer
    Args:
        zip_path: Path to ZIP file
        parent: Parent window
        slide_speed: Slide show interval in seconds
    """
    viewer = ImageViewer(parent, slide_speed)
    viewer.load_zip_file(zip_path)
    viewer.show()
    return viewer

class DeleteConfirmationDialog(QDialog):
    """Dialog for confirming image deletion"""
    
    def __init__(self, parent=None, image_count=1, image_names=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Deletion")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        
        # Warning message
        if image_count == 1:
            message = f"Are you sure you want to delete the current image?\n\n"
            if image_names:
                message += f"Image: {image_names[0]}"
        else:
            message = f"Are you sure you want to delete {image_count} images?\n\n"
            if image_names and len(image_names) <= 5:
                message += "Images:\n" + "\n".join(image_names)
            elif image_names:
                message += f"Images: {image_names[0]}, ... and {image_count-1} more"
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        info_label = QLabel("💡 You can undo this action before saving changes.")
        info_label.setStyleSheet("color: #4a90e2; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QDialogButtonBox()
        delete_button = button_layout.addButton("Delete", QDialogButtonBox.ButtonRole.AcceptRole)
        delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
        cancel_button = button_layout.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_layout.accepted.connect(self.accept)
        button_layout.rejected.connect(self.reject)
        layout.addWidget(button_layout)
        
        self.setLayout(layout)

class BatchDeleteDialog(QDialog):
    """Dialog for batch deleting multiple images"""
    
    def __init__(self, parent=None, total_pages=0):
        super().__init__(parent)
        self.setWindowTitle("Batch Delete Images")
        self.setModal(True)
        self.resize(300, 150)
        
        layout = QVBoxLayout()
        
        # Page range input
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Delete pages:"))
        
        self.start_input = QLineEdit()
        self.start_input.setFixedWidth(50)
        self.start_input.setValidator(QIntValidator(1, total_pages))
        
        self.end_input = QLineEdit()
        self.end_input.setFixedWidth(50)
        self.end_input.setValidator(QIntValidator(1, total_pages))
        
        range_layout.addWidget(self.start_input)
        range_layout.addWidget(QLabel("to"))
        range_layout.addWidget(self.end_input)
        range_layout.addWidget(QLabel(f"of {total_pages}"))
        range_layout.addStretch()
        
        layout.addLayout(range_layout)

        info_label = QLabel("💡 You can undo deletions before saving changes.")
        info_label.setStyleSheet("color: #4a90e2; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QDialogButtonBox()
        delete_button = button_layout.addButton("Delete", QDialogButtonBox.ButtonRole.AcceptRole)
        delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
        cancel_button = button_layout.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_layout.accepted.connect(self.accept)
        button_layout.rejected.connect(self.reject)
        layout.addWidget(button_layout)
        
        self.setLayout(layout)
    
    def get_page_range(self):
        """Get the page range to delete"""
        try:
            start = int(self.start_input.text())
            end = int(self.end_input.text())
            return start, end
        except ValueError:
            return None, None