from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QTableWidget, QTableWidgetItem,
                             QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

class DetailPanel(QWidget):
    """
    Right panel for displaying detailed comic information
    Includes cover image, metadata table, and quick actions
    """
    
    # Signal emitted when user wants to perform an action
    action_requested = pyqtSignal(str, object)  # action_type, row_data
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_row = -1
        self.current_data = None
        
        # Initialize UI
        self.init_ui()
        self.show_empty_state()
    
    def init_ui(self):
        """Initialize the detail panel UI"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # Title section
        title_label = QLabel("Comic Details")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px 0px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Add separator
        main_layout.addWidget(self.create_separator())
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Cover image section
        self.cover_section = self.create_cover_section()
        content_layout.addWidget(self.cover_section)
        
        # Info table section
        self.info_section = self.create_info_section()
        content_layout.addWidget(self.info_section)
        
        # Add stretch to push content to top
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
        
        # Set minimum width
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)
    
    def create_separator(self):
        """Create a horizontal separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #bdc3c7;")
        separator.setFixedHeight(1)
        return separator
    
    def create_cover_section(self):
        """Create cover image display section - larger fixed height, full width"""
        section_widget = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(6)
        
        # Section title
        title_label = QLabel("Cover")
        title_label.setStyleSheet("font-weight: bold; color: #34495e;")
        section_layout.addWidget(title_label)
        
        # Cover container - larger fixed height, full width
        cover_container = QFrame()
        cover_container.setFixedHeight(260)  # Larger fixed height
        cover_container.setStyleSheet("""
            QFrame {
                background-color: #f5f7fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        # Container layout - full width, centered
        container_layout = QHBoxLayout(cover_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Cover image label - with minimum size of 240x240
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setScaledContents(False)  # Disable automatic scaling
        self.cover_label.setMinimumSize(240, 240)  # Minimum 240x240
        
        # Allow label to expand but with reasonable maximum
        self.cover_label.setMaximumSize(400, 400)  # Maximum 400x400
        
        # Default placeholder
        self.cover_label.setText("No cover")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-style: italic;
            }
        """)
        
        container_layout.addWidget(self.cover_label)
        section_layout.addWidget(cover_container)
        
        section_widget.setLayout(section_layout)
        return section_widget
    
    def create_info_section(self):
        """Create information table section with improved styling"""
        section_widget = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(8)
        
        # Section title
        title_label = QLabel("Metadata")
        title_label.setStyleSheet("font-weight: bold; color: #34495e;")
        section_layout.addWidget(title_label)
        
        # Create info table with darker background
        self.info_table = QTableWidget()
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.info_table.horizontalHeader().setStretchLastSection(True)
        self.info_table.verticalHeader().setVisible(False)
        self.info_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.info_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.info_table.setShowGrid(False)
        self.info_table.setAlternatingRowColors(True)
        
        # Set column widths
        self.info_table.setColumnWidth(0, 80)
        
        # Set improved style with darker background
        self.info_table.setStyleSheet("""
            QTableWidget {
                background-color: #f8f9fa;  /* Light gray background instead of white */
                border: 1px solid #dee2e6;
                border-radius: 4px;
                color: #212529;  /* Dark text color */
            }
            QTableWidget::item {
                padding: 6px 8px;
                color: #212529;  /* Ensure text is dark */
            }
            QTableWidget::item:alternate {
                background-color: #e9ecef;  /* Slightly darker for alternating rows */
            }
            QHeaderView::section {
                background-color: #e9ecef;  /* Header background */
                padding: 8px;
                border: none;
                border-bottom: 1px solid #dee2e6;
                color: #495057;  /* Darker header text */
                font-weight: bold;
            }
        """)
        
        section_layout.addWidget(self.info_table)
        section_widget.setLayout(section_layout)
        return section_widget
    
    def update_details(self, row_data):
        """
        Update the detail panel with comic data
        
        Args:
            row_data: Dictionary containing comic information
        """
        self.current_data = row_data
        if not row_data:
            self.show_empty_state()
            return
        self.update_cover_image(row_data.get('websign', ''))
        self.update_info_table(row_data)
    
    def update_cover_image(self, websign):
        """Load and display cover image - with larger size for detail panel"""
        if not websign:
            self.show_no_cover_state()
            return
        
        # Clear current
        self.cover_label.clear()
        self.cover_label.setText("")
        
        try:
            if hasattr(self.main_window, 'web_controller'):
                # Request larger image for detail panel (e.g., 300x400)
                pixmap = self.main_window.web_controller.get_cover_image(
                    websign, 
                    size=(300, 400)  # Larger size for detail panel
                )
                
                if pixmap and not pixmap.isNull():
                    self.display_cover_pixmap(pixmap)
                    return
                else:
                    self.show_no_cover_state()
        
        except Exception as e:
            print(f"Error loading cover image: {e}")
            self.show_error_state()

    def display_cover_pixmap(self, pixmap):
        """Display a pixmap in the cover label with proper scaling"""
        # Remove any text styling
        self.cover_label.setStyleSheet("")
        
        # Get label size (minimum 240x240)
        label_size = self.cover_label.size()
        
        # Ensure minimum size
        if label_size.width() < 240:
            label_size.setWidth(240)
        if label_size.height() < 240:
            label_size.setHeight(240)
        
        pixmap_size = pixmap.size()
        
        # Calculate scale to fit while keeping aspect ratio
        width_ratio = label_size.width() / pixmap_size.width()
        height_ratio = label_size.height() / pixmap_size.height()
        
        # Use the smaller ratio to ensure image fits completely
        scale_factor = min(width_ratio, height_ratio)
        
        # Don't scale up too much if the source image is small
        max_scale = 2.0
        if scale_factor > max_scale:
            scale_factor = max_scale
        
        # Calculate new size
        new_width = int(pixmap_size.width() * scale_factor)
        new_height = int(pixmap_size.height() * scale_factor)
        
        # Ensure minimum dimensions
        if new_width < 50:
            new_width = 50
            scale_factor = new_width / pixmap_size.width()
            new_height = int(pixmap_size.height() * scale_factor)
        
        # Scale if needed
        if scale_factor != 1.0:
            scaled_pixmap = pixmap.scaled(
                new_width, new_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.cover_label.setPixmap(scaled_pixmap)
        else:
            self.cover_label.setPixmap(pixmap)
        
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def show_no_cover_state(self):
        """Show state when no cover is available"""
        self.cover_label.setText("No cover")
        self.cover_label.setStyleSheet("color: #6c757d; font-style: italic;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def show_error_state(self):
        """Show state when there's an error loading cover"""
        self.cover_label.setText("Error loading cover")
        self.cover_label.setStyleSheet("color: #e74c3c; font-style: italic;")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def update_info_table(self, row_data):
        """Update information table with comic data"""
        # Define field display names
        field_names = {
            'websign': 'Websign',
            'author': 'Author',
            'title': 'Title',
            'group': 'Group',
            'show': 'Show',
            'magazine': 'Magazine',
            'origin': 'Origin',
            'tag': 'Tags',
            'read_status': 'Read Status',
            'progress': 'Progress',
            'file_path': 'File Path'
        }
        
        # Filter out empty fields and prepare rows
        rows = []
        for key, display_name in field_names.items():
            value = row_data.get(key, '')
            if value or key in ['websign', 'author', 'title']:  # Always show required fields
                rows.append((display_name, str(value)))
        
        # Update table
        self.info_table.setRowCount(len(rows))
        
        for i, (field, value) in enumerate(rows):
            # Field name cell
            field_item = QTableWidgetItem(field)
            field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.info_table.setItem(i, 0, field_item)
            
            # Value cell
            value_item = QTableWidgetItem(value)
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Special formatting for certain fields
            if field == 'Read Status':
                value_item.setText(self.get_read_status_display(value))
                self.apply_read_status_style(value_item, value)
            elif field == 'Progress':
                value_item.setText(f"{value}%")
            
            self.info_table.setItem(i, 1, value_item)
        
        # Resize rows to content
        self.info_table.resizeRowsToContents()
    
    def get_read_status_display(self, status):
        """Convert status code to display text"""
        status_map = {
            'unread': 'Unread',
            'reading': 'Reading',
            'completed': 'Completed'
        }
        return status_map.get(status, status)
    
    def apply_read_status_style(self, item, status):
        """Apply color coding to read status - ensure visibility on light background"""
        colors = {
            'unread': '#e74c3c',     # Red
            'reading': '#f39c12',    # Orange
            'completed': '#27ae60'   # Green
        }
        
        if status in colors:
            from PyQt6.QtGui import QColor
            # Set foreground color only (text color)
            item.setForeground(QColor(colors[status]))
            # Keep background as defined by table style
    
    def show_empty_state(self):
        """Show empty state - with fixed size cover area"""
        self.current_data = None
        self.cover_label.clear()
        self.cover_label.setText("No cover")
        self.cover_label.setStyleSheet("color: #6c757d; font-style: italic;")
        self.info_table.setRowCount(0)
    
    def show_multiple_selection_state(self, count):
        """Show multiple selection state - with fixed size cover area"""
        self.current_data = None
        self.cover_label.clear()
        self.cover_label.setText(f"{count} selected")
        self.cover_label.setStyleSheet("color: #3498db; font-weight: bold;")
        self.info_table.setRowCount(1)
        message_item = QTableWidgetItem(f"{count} comics selected. Details shown for first selection.")
        message_item.setFlags(message_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        message_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_table.setItem(0, 0, message_item)
        self.info_table.setSpan(0, 0, 1, 2)  # Merge cells
        
        # Disable action buttons (or enable for batch operations?)
        self.set_actions_enabled(False)

    def resizeEvent(self, event):
        """Handle resize events to update cover image scaling"""
        super().resizeEvent(event)
        
        # Update cover image if we have one
        if self.current_data and hasattr(self, 'cover_label'):
            websign = self.current_data.get('websign', '')
            if websign:
                # Force a re-layout and then update the image
                QTimer.singleShot(50, lambda: self.update_cover_image(websign))