from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from views.tag_cloud import TagCloud

class Sidebar(QWidget):
    """Sidebar for filtering and navigation"""
    
    # Signals for filter changes
    status_filter_changed = pyqtSignal(str)  # Emits status: "all", "unread", "reading", "completed"
    filter_reset = pyqtSignal()
    tag_filter_changed = pyqtSignal(list)
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        """Initialize sidebar UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Filters")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
            }
        """)
        layout.addWidget(title_label)
        
        # Add separator
        layout.addWidget(self.create_separator())
        
        # Status filter section
        status_section = self.create_status_filter_section()
        layout.addWidget(status_section)
        
        # Add separator
        layout.addWidget(self.create_separator())

        # Tag cloud section
        self.tag_cloud = TagCloud(self.main_window)
        layout.addWidget(self.tag_cloud)

        # Add separator
        layout.addWidget(self.create_separator())
        
        # Reset button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        reset_btn.clicked.connect(self.reset_filters)
        layout.addWidget(reset_btn)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        self.setLayout(layout)
        self.setFixedWidth(220)

        # Connect tag cloud signals
        self.tag_cloud.tag_clicked.connect(self.on_tag_clicked)
        self.tag_cloud.clear_tags.connect(self.on_tags_cleared)
    
    def create_separator(self):
        """Create a horizontal separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #bdc3c7;")
        separator.setFixedHeight(1)
        return separator
    
    def create_status_filter_section(self):
        """Create status filter section with radio buttons"""
        section_widget = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(8)
        
        # Section title
        status_title = QLabel("Read Status")
        status_title.setStyleSheet("font-weight: bold; color: #34495e;")
        section_layout.addWidget(status_title)
        
        # Status filter buttons
        self.all_btn = self.create_status_button("All", "all", True)
        self.unread_btn = self.create_status_button("Unread", "unread", False)
        self.reading_btn = self.create_status_button("Reading", "reading", False)
        self.completed_btn = self.create_status_button("Completed", "completed", False)
        
        section_layout.addWidget(self.all_btn)
        section_layout.addWidget(self.unread_btn)
        section_layout.addWidget(self.reading_btn)
        section_layout.addWidget(self.completed_btn)
        
        section_widget.setLayout(section_layout)
        return section_widget
    
    def create_status_button(self, text, status, checked=False):
        """Create a status filter button"""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setProperty("status", status)
        
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QPushButton:checked {
                color: #2c3e50;
                border: 1px solid #2980b9;
            }
        """)
        
        btn.clicked.connect(self.on_status_button_clicked)
        return btn
    
    def on_status_button_clicked(self):
        """Handle status button clicks"""
        clicked_btn = self.sender()
        if clicked_btn.isChecked():
            # Uncheck other buttons
            for btn in [self.all_btn, self.unread_btn, self.reading_btn, self.completed_btn]:
                if btn != clicked_btn:
                    btn.setChecked(False)
            
            # Emit filter signal
            status = clicked_btn.property("status")
            self.status_filter_changed.emit(status)
        else:
            # If no button is checked, check "all"
            clicked_btn.setChecked(True)
    
    def update_status_counts(self, counts):
        """Update button texts with count numbers"""
        self.all_btn.setText(f"All ({counts.get('all', 0)})")
        self.unread_btn.setText(f"Unread ({counts.get('unread', 0)})")
        self.reading_btn.setText(f"Reading ({counts.get('reading', 0)})")
        self.completed_btn.setText(f"Completed ({counts.get('completed', 0)})")

    def on_tag_clicked(self, tag):
        """Handle tag selection"""
        selected_tags = self.tag_cloud.get_selected_tags()
        self.tag_filter_changed.emit(selected_tags)

    def on_tags_cleared(self):
        """Handle tags cleared"""
        self.tag_filter_changed.emit([])
    
    def reset_filters(self):
        """Reset all filters to default"""
        self.all_btn.setChecked(True)
        for btn in [self.unread_btn, self.reading_btn, self.completed_btn]:
            btn.setChecked(False)
        self.tag_cloud.clear_selected_tags()
        self.filter_reset.emit()
    
    def update_tag_cloud(self, tag_data):
        """Update tag cloud with tag frequency data"""
        self.tag_cloud.update_tags(tag_data)