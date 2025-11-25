from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class TagCloud(QWidget):
    """Tag cloud widget for displaying and filtering by tags"""
    
    # Signals
    tag_clicked = pyqtSignal(str)  # Emits clicked tag
    clear_tags = pyqtSignal()      # Emits when tags are cleared
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.selected_tags = set()
        self.tag_buttons = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize tag cloud UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title and clear button
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Popular Tags")
        title_label.setStyleSheet("font-weight: bold; color: #34495e;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                color: #7f8c8d;
                border: none;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #e74c3c;
                background-color: #fdf2f2;
                border-radius: 3px;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_selected_tags)
        self.clear_btn.hide()
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # Tags container with grid layout
        self.tags_container = QWidget()
        self.tags_layout = QGridLayout()
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setHorizontalSpacing(6)
        self.tags_layout.setVerticalSpacing(4)
        self.tags_container.setLayout(self.tags_layout)
        
        layout.addWidget(self.tags_container)
        
        self.setLayout(layout)
    
    def update_tags(self, tag_data):
        """Update tag cloud with new tag data"""
        # Clear existing tags
        for button in self.tag_buttons.values():
            button.deleteLater()
        self.tag_buttons.clear()
        
        # Sort tags by frequency (descending) and take top 10
        sorted_tags = sorted(tag_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Add tags to grid layout (2 per row)
        row, col = 0, 0
        for tag, count in sorted_tags:
            button = self.create_tag_button(tag, count)
            self.tags_layout.addWidget(button, row, col)
            self.tag_buttons[tag] = button
            
            # Move to next position
            col += 1
            if col >= 2:  # 2 tags per row
                col = 0
                row += 1
    
    def create_tag_button(self, tag, count):
        """Create a tag button with size based on frequency"""
        # Calculate font size based on frequency (min 9, max 14)
        base_size = 9
        size_increment = min(count / 10, 5)  # Cap the size increase
        font_size = base_size + int(size_increment)
        
        btn = QPushButton(f"{tag} ({count})")
        btn.setProperty("tag", tag)
        btn.setCheckable(True)
        
        # Style based on selection state and frequency
        self.update_tag_button_style(btn, False)
        
        btn.clicked.connect(self.on_tag_clicked)
        
        # Set font size
        font = QFont()
        font.setPointSize(font_size)
        btn.setFont(font)
        
        self.tags_layout.addWidget(btn)
        self.tag_buttons[tag] = btn
    
    def create_tag_button(self, tag, count):
        """Create a tag button with uniform font size"""
        btn = QPushButton(f"{tag} ({count})")
        btn.setProperty("tag", tag)
        btn.setCheckable(True)
        
        # Make buttons expand to fill available space
        btn.setMinimumWidth(80)  # Minimum width for better appearance
        
        self.update_tag_button_style(btn, False)
        
        btn.clicked.connect(self.on_tag_clicked)
        
        # Set uniform font size (removed frequency-based sizing)
        font = QFont()
        font.setPointSize(10)  # Fixed font size
        btn.setFont(font)
        
        return btn

    def update_tag_button_style(self, button, is_selected):
        """Update tag button style based on selection state"""
        tag = button.property("tag")
        if is_selected:
            style = f"""
                QPushButton {{
                    background-color: #3498db;
                    color: white;
                    border: 1px solid #2980b9;
                    border-radius: 12px;
                    padding: 4px 12px;
                }}
                QPushButton:hover {{
                    background-color: #2980b9;
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: 1px solid #bdc3c7;
                    border-radius: 12px;
                    padding: 4px 12px;
                }}
                QPushButton:hover {{
                    background-color: #d5dbdb;
                    border: 1px solid #95a5a6;
                }}
            """
        button.setStyleSheet(style)
    
    def on_tag_clicked(self):
        """Handle tag button clicks"""
        clicked_btn = self.sender()
        tag = clicked_btn.property("tag")
        
        if clicked_btn.isChecked():
            self.selected_tags.add(tag)
            self.update_tag_button_style(clicked_btn, True)
        else:
            self.selected_tags.discard(tag)
            self.update_tag_button_style(clicked_btn, False)
        
        # Show/hide clear button based on whether any tags are selected
        self.clear_btn.setVisible(len(self.selected_tags) > 0)
        
        # Emit signal with selected tags
        if self.selected_tags:
            self.tag_clicked.emit(tag)
    
    def clear_selected_tags(self):
        """Clear all selected tags"""
        for tag in list(self.selected_tags):
            if tag in self.tag_buttons:
                btn = self.tag_buttons[tag]
                btn.setChecked(False)
                self.update_tag_button_style(btn, False)
        
        self.selected_tags.clear()
        self.clear_btn.hide()
        self.clear_tags.emit()
    
    def get_selected_tags(self):
        """Get currently selected tags"""
        return list(self.selected_tags)