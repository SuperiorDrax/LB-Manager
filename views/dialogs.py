from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QProgressDialog,
                           QLineEdit, QLabel, QMessageBox, QComboBox, QCheckBox, QRadioButton)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import requests
from bs4 import BeautifulSoup
from utils.user_agents import get_random_user_agent

class InsertDialog(QDialog):
    def __init__(self, parent=None, jm_website=""):
        super().__init__(parent)
        self.jm_website = jm_website
        self.setWindowTitle("Insert Data")
        self.setModal(True)
        self.resize(500, 150)
        
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # JM Number input row
        jm_layout = QHBoxLayout()
        jm_label = QLabel("JM number:")
        self.jm_input = QLineEdit()
        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.setFixedWidth(80)
        
        jm_layout.addWidget(jm_label)
        jm_layout.addWidget(self.jm_input)
        jm_layout.addWidget(self.fetch_button)
        
        # Original input field
        self.input_label = QLabel("Or enter text to parse:")
        self.input_field = QLineEdit()

        # Tag input field
        tag_layout = QHBoxLayout()
        tag_label = QLabel("Tags:")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tags manually or use Fetch to auto-fill...")
        
        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.tag_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Confirm")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add all layouts
        layout.addLayout(jm_layout)
        layout.addWidget(self.input_label)
        layout.addWidget(self.input_field)
        layout.addLayout(tag_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.confirm_button.clicked.connect(self.validate_and_accept)
        self.cancel_button.clicked.connect(self.reject)
        self.fetch_button.clicked.connect(self.fetch_website_data)
        self.jm_input.returnPressed.connect(self.fetch_website_data)
    
    def fetch_website_data(self):
        """Fetch data from JM website based on JM number with async operation"""
        jm_number = self.jm_input.text().strip()
        if not jm_number:
            QMessageBox.warning(self, "Input Error", "Please enter a JM number.")
            return
        
        if not self.jm_website:
            QMessageBox.warning(self, "Configuration Error", "JM website is not configured.")
            return
        
        # Disable fetch button during operation
        self.fetch_button.setEnabled(False)
        self.fetch_button.setText("Fetching...")
        
        try:
            # Use QProgressDialog for better lifecycle management
            self.progress_dialog = QProgressDialog(f"Fetching data for JM {jm_number}...", "Cancel", 0, 0, self)
            self.progress_dialog.setWindowTitle("Fetching Data")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.show()
            
            # Create and start background thread
            self.fetch_thread = JMDataFetchThread(jm_number, self.jm_website)
            self.fetch_thread.finished.connect(self.on_fetch_finished)
            self.fetch_thread.error.connect(self.on_fetch_error)
            self.fetch_thread.start()
            
        except Exception as e:
            # Cleanup in case of initialization error
            self.fetch_button.setEnabled(True)
            self.fetch_button.setText("Fetch")
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.close()
            QMessageBox.critical(self, "Fetch Error", f"Failed to start fetch: {str(e)}")
    
    def on_fetch_finished(self, result_data):
        """Handle successful data fetch with error checking"""
        # Ensure progress dialog is closed
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        # Restore button state
        self.fetch_button.setEnabled(True)
        self.fetch_button.setText("Fetch")
        
        if result_data and 'extracted_texts' in result_data and result_data['extracted_texts']:
            try:
                # Use the first extracted text and prepend JM number
                jm_number = self.jm_input.text().strip()
                fetched_text = result_data['extracted_texts'][0]
                combined_text = f"{jm_number} {fetched_text}"
                self.input_field.setText(combined_text)
                
                # Fill tags if available
                if 'tags' in result_data and result_data['tags']:
                    tag_text = ", ".join(result_data['tags'])
                    self.tag_input.setText(tag_text)
                    QMessageBox.information(self, "Success", "Data and tags fetched successfully!")
                else:
                    QMessageBox.information(self, "Success", "Data fetched successfully! (No tags found)")
                    
            except (IndexError, KeyError) as e:
                QMessageBox.warning(self, "Fetch Error", 
                                "Failed to extract data from the webpage. The website structure may have changed.")
        else:
            QMessageBox.warning(self, "No Data", 
                            "Could not extract data from the webpage. Please check the JM number and try again.")
    
    def on_fetch_error(self, error_msg):
        """Handle fetch error"""
        # Ensure progress dialog is closed
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        # Restore button state
        self.fetch_button.setEnabled(True)
        self.fetch_button.setText("Fetch")
        
        QMessageBox.critical(self, "Fetch Error", f"Failed to fetch data: {error_msg}")
    
    def get_input_text(self):
        """Get the final input text from either field"""
        return self.input_field.text().strip()

    def get_tag_text(self):
        """Get the tag text"""
        return self.tag_input.text().strip()
    
    def validate_and_accept(self):
        """Validate input before closing dialog"""
        text = self.get_input_text()
        if not text:
            QMessageBox.warning(self, "Empty Input", "Please enter text to parse.")
            return
        
        from models.data_parser import DataParser
        parsed_data = DataParser.parse_text(text)
        if parsed_data is None:
            QMessageBox.warning(self, "Parse Error", 
                              "Cannot parse the input text. Required fields (websign, author, title) are missing or format is incorrect.\n\nPlease check the format and try again.")
            return
        
        self.accept()

    def closeEvent(self, event):
        """Ensure thread is properly cleaned up when dialog closes"""
        if hasattr(self, 'fetch_thread') and self.fetch_thread.isRunning():
            self.fetch_thread.terminate()
            self.fetch_thread.wait()
        
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        event.accept()

class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Search")
        self.setModal(True)
        self.resize(400, 200)  # Increased size for new layout
        
        layout = QVBoxLayout()
        
        # First condition row
        condition1_layout = QHBoxLayout()
        self.column_combo1 = QComboBox()
        self.column_combo1.addItems(['author', 'title', 'group', 'show', 'magazine', 'origin', 'websign', 'tag'])
        self.search_field1 = QLineEdit()
        self.search_field1.setPlaceholderText("Enter search text...")
        
        condition1_layout.addWidget(self.column_combo1)
        condition1_layout.addWidget(self.search_field1)
        
        # Logic operator row
        logic_layout = QHBoxLayout()
        self.and_radio = QRadioButton("AND")
        self.or_radio = QRadioButton("OR")
        self.and_radio.setChecked(True)  # Default to AND
        
        logic_layout.addWidget(QLabel("Logic:"))
        logic_layout.addWidget(self.and_radio)
        logic_layout.addWidget(self.or_radio)
        logic_layout.addStretch()
        
        # Second condition row
        condition2_layout = QHBoxLayout()
        self.column_combo2 = QComboBox()
        self.column_combo2.addItems(['author', 'title', 'group', 'show', 'magazine', 'origin', 'websign', 'tag'])
        self.search_field2 = QLineEdit()
        self.search_field2.setPlaceholderText("Optional second condition...")
        
        condition2_layout.addWidget(self.column_combo2)
        condition2_layout.addWidget(self.search_field2)
        
        # Regex options
        regex_layout = QHBoxLayout()
        self.regex_checkbox = QCheckBox("Use regular expression")
        self.regex_help_button = QPushButton("Regex Help")
        self.regex_help_button.setFixedWidth(100)
        
        regex_layout.addWidget(self.regex_checkbox)
        regex_layout.addWidget(self.regex_help_button)
        regex_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        self.search_next_button = QPushButton("Search Next")
        self.filter_button = QPushButton("Filter")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.search_next_button)
        button_layout.addWidget(self.filter_button)
        button_layout.addWidget(self.cancel_button)
        
        # Add all layouts
        layout.addWidget(QLabel("First condition:"))
        layout.addLayout(condition1_layout)
        layout.addLayout(logic_layout)
        layout.addWidget(QLabel("Second condition (optional):"))
        layout.addLayout(condition2_layout)
        layout.addLayout(regex_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.search_next_button.clicked.connect(self.accept_search_next)
        self.filter_button.clicked.connect(self.accept_filter)
        self.cancel_button.clicked.connect(self.reject)
        self.regex_help_button.clicked.connect(self.show_regex_help)
        self.search_field1.textChanged.connect(self.update_ui_state)
        self.search_field2.textChanged.connect(self.update_ui_state)
    
    def update_ui_state(self):
        """Update UI state based on input fields"""
        has_condition2 = bool(self.search_field2.text().strip())
        self.and_radio.setEnabled(has_condition2)
        self.or_radio.setEnabled(has_condition2)
        
        # If second condition is empty, ensure AND is selected (for consistency)
        if not has_condition2:
            self.and_radio.setChecked(True)
    
    def show_regex_help(self):
        """Show regex syntax help"""
        help_text = """
Regular Expression Quick Reference:

Basic patterns:
• .       - Any single character
• \\w+     - One or more word characters
• \\d+     - One or more digits
• [abc]   - Any of a, b, or c
• ^start  - Text starting with 'start'
• end$    - Text ending with 'end'

Quantifiers:
• *       - Zero or more
• +       - One or more  
• ?       - Zero or one
• {3}     - Exactly 3
• {2,5}   - Between 2 and 5

Examples:
• ^JM\\d+  - Starts with JM followed by digits
• .*jpg$  - Ends with jpg
• \\d{3}-\\d{4} - Pattern like 123-4567

Leave unchecked for simple text search.
        """
        QMessageBox.information(self, "Regex Help", help_text.strip())
    
    def get_search_options(self):
        """Return search options including both conditions and logic"""
        condition1_text = self.search_field1.text().strip()
        condition2_text = self.search_field2.text().strip()
        
        # Determine if we have single or multiple conditions
        has_condition1 = bool(condition1_text)
        has_condition2 = bool(condition2_text)
        
        if not has_condition1:
            return None  # No valid conditions
        
        options = {
            'condition1': {
                'column': self.column_combo1.currentText(),
                'text': condition1_text
            },
            'use_regex': self.regex_checkbox.isChecked(),
            'logic': 'AND' if self.and_radio.isChecked() else 'OR'
        }
        
        if has_condition2:
            options['condition2'] = {
                'column': self.column_combo2.currentText(),
                'text': condition2_text
            }
        
        return options
    
    def accept_search_next(self):
        options = self.get_search_options()
        if options is None:
            QMessageBox.warning(self, "Input Error", "Please enter at least one search condition.")
            return
        self.done(1)  # Return code 1 for search next

    def accept_filter(self):
        options = self.get_search_options()
        if options is None:
            QMessageBox.warning(self, "Input Error", "Please enter at least one search condition.")
            return
        self.done(2)  # Return code 2 for filter

class EditDialog(QDialog):
    def __init__(self, parent=None, row_data=None):
        super().__init__(parent)
        self.row_data = row_data or {}
        self.setWindowTitle("Edit Row Data")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        self.populate_data()
    
    def init_ui(self):
        """Initialize the edit dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create input fields for editable columns
        self.fields = {}
        
        # Websign field
        websign_layout = QHBoxLayout()
        websign_label = QLabel("websign:")
        websign_label.setFixedWidth(80)
        self.websign_input = QLineEdit()
        websign_layout.addWidget(websign_label)
        websign_layout.addWidget(self.websign_input)
        layout.addLayout(websign_layout)
        self.fields['websign'] = self.websign_input
        
        # Author field
        author_layout = QHBoxLayout()
        author_label = QLabel("author:")
        author_label.setFixedWidth(80)
        self.author_input = QLineEdit()
        author_layout.addWidget(author_label)
        author_layout.addWidget(self.author_input)
        layout.addLayout(author_layout)
        self.fields['author'] = self.author_input
        
        # Title field
        title_layout = QHBoxLayout()
        title_label = QLabel("title:")
        title_label.setFixedWidth(80)
        self.title_input = QLineEdit()
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        self.fields['title'] = self.title_input
        
        # Group field
        group_layout = QHBoxLayout()
        group_label = QLabel("group:")
        group_label.setFixedWidth(80)
        self.group_input = QLineEdit()
        group_layout.addWidget(group_label)
        group_layout.addWidget(self.group_input)
        layout.addLayout(group_layout)
        self.fields['group'] = self.group_input
        
        # Show field
        show_layout = QHBoxLayout()
        show_label = QLabel("show:")
        show_label.setFixedWidth(80)
        self.show_input = QLineEdit()
        show_layout.addWidget(show_label)
        show_layout.addWidget(self.show_input)
        layout.addLayout(show_layout)
        self.fields['show'] = self.show_input
        
        # Magazine field
        magazine_layout = QHBoxLayout()
        magazine_label = QLabel("magazine:")
        magazine_label.setFixedWidth(80)
        self.magazine_input = QLineEdit()
        magazine_layout.addWidget(magazine_label)
        magazine_layout.addWidget(self.magazine_input)
        layout.addLayout(magazine_layout)
        self.fields['magazine'] = self.magazine_input
        
        # Origin field
        origin_layout = QHBoxLayout()
        origin_label = QLabel("origin:")
        origin_label.setFixedWidth(80)
        self.origin_input = QLineEdit()
        origin_layout.addWidget(origin_label)
        origin_layout.addWidget(self.origin_input)
        layout.addLayout(origin_layout)
        self.fields['origin'] = self.origin_input
        
        # Tag field
        tag_layout = QHBoxLayout()
        tag_label = QLabel("tag:")
        tag_label.setFixedWidth(80)
        self.tag_input = QLineEdit()
        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.tag_input)
        layout.addLayout(tag_layout)
        self.fields['tag'] = self.tag_input
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.save_button.clicked.connect(self.validate_and_save)
        self.cancel_button.clicked.connect(self.reject)
    
    def populate_data(self):
        """Populate the form with current row data"""
        if self.row_data:
            self.websign_input.setText(self.row_data.get('websign', ''))
            self.author_input.setText(self.row_data.get('author', ''))
            self.title_input.setText(self.row_data.get('title', ''))
            self.group_input.setText(self.row_data.get('group', ''))
            self.show_input.setText(self.row_data.get('show', ''))
            self.magazine_input.setText(self.row_data.get('magazine', ''))
            self.origin_input.setText(self.row_data.get('origin', ''))
            self.tag_input.setText(self.row_data.get('tag', ''))
    
    def validate_and_save(self):
        """Validate input and save if valid"""
        # Get values
        websign = self.websign_input.text().strip()
        author = self.author_input.text().strip()
        title = self.title_input.text().strip()
        
        # Validate required fields
        if not websign:
            QMessageBox.warning(self, "Validation Error", "websign cannot be empty.")
            return
        
        if not author:
            QMessageBox.warning(self, "Validation Error", "author cannot be empty.")
            return
        
        if not title:
            QMessageBox.warning(self, "Validation Error", "title cannot be empty.")
            return
        
        # Validate websign is positive integer
        try:
            websign_int = int(websign)
            if websign_int <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "websign must be a positive integer.")
            return
        
        # All validations passed
        self.accept()
    
    def get_edited_data(self):
        """Get all edited data"""
        return {
            'websign': self.websign_input.text().strip(),
            'author': self.author_input.text().strip(),
            'title': self.title_input.text().strip(),
            'group': self.group_input.text().strip(),
            'show': self.show_input.text().strip(),
            'magazine': self.magazine_input.text().strip(),
            'origin': self.origin_input.text().strip(),
            'tag': self.tag_input.text().strip()
        }

class JMDataFetchThread(QThread):
    """Background thread for fetching JM data in insert dialog"""
    finished = pyqtSignal(dict)  # Changed to dict to include both extracted_texts and tags
    error = pyqtSignal(str)      # error_message
    
    def __init__(self, jm_number, jm_website):
        super().__init__()
        self.jm_number = jm_number
        self.jm_website = jm_website
    
    def run(self):
        try:
            # Construct URL
            url = f"https://{self.jm_website}/album/{self.jm_number}"
            
            # Fetch webpage content
            html_content = self.fetch_webpage(url)
            if not html_content:
                raise Exception("Failed to fetch webpage content")
            
            # Extract dynamic text
            extracted_texts = self.extract_dynamic_text(html_content)
            
            # Extract tags
            tags = self.extract_tags(html_content)
            
            # Return both data and tags
            result = {
                'extracted_texts': extracted_texts,
                'tags': tags
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def fetch_webpage(self, url, timeout=10, retries=3):
        """Fetch webpage content with random User-Agent"""
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    import time
                    time.sleep(2)
                else:
                    return None
    
    def extract_dynamic_text(self, html_content, fixed_suffix=' Comics - 禁漫天堂'):
        """Extract dynamic text from webpage before fixed suffix"""
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        target_texts = []
        
        # CSS Selectors for both target locations
        selectors = [
            'meta[property="og:title"]',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Extract content based on element type
                if selector == 'meta[property="og:title"]':
                    content = element.get('content', '')
                else:
                    content = element.get_text()
                
                # Check if the fixed suffix exists in the content
                if fixed_suffix in content:
                    target_text = content.split(fixed_suffix)[0].strip()
                    target_texts.append(target_text)
        
        # Remove duplicates while preserving order
        unique_texts = []
        for text in target_texts:
            if text not in unique_texts:
                unique_texts.append(text)
        
        return unique_texts
    
    def extract_tags(self, html_content):
        """Extract tags from HTML using the specified CSS selector"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all tag elements using the specified CSS selector
        tag_elements = soup.select('span[data-type="tags"] a.btn.phone-tags-tag')
        
        # Extract text from each tag element
        tags = []
        for tag_element in tag_elements:
            tag_text = tag_element.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        
        return tags