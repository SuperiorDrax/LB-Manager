from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QScrollArea, QGridLayout, QSizePolicy,
                             QPushButton, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont

class ComicCard(QFrame):
    """Individual comic card for grid view"""
    
    clicked = pyqtSignal(int)  # Emits row index when clicked
    double_clicked = pyqtSignal(int)  # Emits row index when double-clicked
    
    def __init__(self, row_index, comic_data, main_window, parent=None):
        super().__init__(parent)
        self.row_index = row_index
        self.comic_data = comic_data
        self.main_window = main_window
        self.is_loading_cover = False
        self.is_selected = False
        
        self.setFixedSize(140, 250)  # Fixed card size
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        
        self.init_ui()
        self.update_style()
        
        # Enable mouse tracking
        self.setMouseTracking(True)

        # Delayed cover loading
        QTimer.singleShot(100, self.load_cover_image)
    
    def init_ui(self):
        """Initialize card UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(120, 170)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.cover_label.setStyleSheet("""
        #     QLabel {
        #         background-color: #f5f7fa;
        #         border: 1px solid #dee2e6;
        #         border-radius: 4px;
        #     }
        # """)
        
        # Title (truncated if too long)
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        self.title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
            }
        """)
        
        # Author info
        self.author_label = QLabel()
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
            }
        """)
        
        # Status indicator
        self.status_label = QLabel()
        self.status_label.setFixedHeight(16)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.cover_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.author_label)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.update_content()
    
    def update_content(self):
        """Update card content with comic data"""
        # Title (truncate if too long)
        title = self.comic_data.get('title', '')
        if len(title) > 10:
            title = title[:8] + '...'
        self.title_label.setText(title)
        
        # Author info
        author = self.comic_data.get('author', '')
        self.author_label.setText(author)
        
        # Status
        status = self.comic_data.get('read_status', 'unread')
        status_text = {
            'unread': 'Unread',
            'reading': 'Reading',
            'completed': 'Completed'
        }.get(status, status)
        
        status_color = {
            'unread': '#e74c3c',
            'reading': '#f39c12',
            'completed': '#27ae60'
        }.get(status, '#95a5a6')
        
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {status_color};
                border-radius: 8px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

        # Load cover image
        self.load_cover_image()

    def load_cover_image(self):
        """Load cover image for this comic card with proper lifecycle handling"""
        # Check if card is still valid and visible
        if not self.isVisible() or not self.parent():
            return
        
        # Get websign from comic data
        websign = self.comic_data.get('websign', '')
        if not websign:
            self.show_no_cover()
            return
        
        try:
            # Check if we have main_window reference
            if not hasattr(self, 'main_window') or not self.main_window:
                self.show_no_cover()
                return
            
            # Get cover image from web controller
            pixmap = self.main_window.web_controller.get_cover_image(
                websign, 
                size=(130, 150)  # Size appropriate for grid cards
            )
            
            # Check if card still exists before setting pixmap
            if not self.isVisible() or not self.parent():
                return  # Card was destroyed while loading
            
            if pixmap and not pixmap.isNull():
                # Scale pixmap to fit label while keeping aspect ratio
                label_size = self.cover_label.size()
                pixmap_size = pixmap.size()
                
                # Calculate scale to fit
                width_ratio = label_size.width() / pixmap_size.width()
                height_ratio = label_size.height() / pixmap_size.height()
                scale_factor = min(width_ratio, height_ratio)
                
                # Calculate new size
                new_width = int(pixmap_size.width() * scale_factor)
                new_height = int(pixmap_size.height() * scale_factor)
                
                # Scale with smooth transformation
                scaled_pixmap = pixmap.scaled(
                    new_width, new_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set pixmap and clear any placeholder text
                self.cover_label.setPixmap(scaled_pixmap)
                self.cover_label.setText("")
                self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                # No pixmap available
                self.show_no_cover()
                
        except AttributeError as e:
            # Handle missing attributes (e.g., web_controller not available)
            print(f"Attribute error loading cover for {websign}: {e}")
            self.show_no_cover()
        except Exception as e:
            # Handle any other errors
            print(f"Error loading cover for {websign}: {e}")
            self.show_no_cover()

    def show_no_cover(self):
        """Show 'No cover' placeholder"""
        if self.isVisible():
            self.cover_label.clear()
            self.cover_label.setText("No cover")
            self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cover_label.setStyleSheet("color: #6c757d; font-style: italic;")

    def deleteLater(self):
        """Override to handle pending cover loads"""
        if self.is_loading_cover:
            # Cancel pending load
            self.is_loading_cover = False
        super().deleteLater()
    
    def set_selected(self, selected):
        """Update selection state"""
        self.is_selected = selected
        self.update_style()
    
    def update_style(self):
        """Update card visual style based on selection state"""
        if self.is_selected:
            self.setStyleSheet("""
                ComicCard {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                ComicCard {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
                ComicCard:hover {
                    background-color: #f8f9fa;
                    border: 1px solid #adb5bd;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+click: toggle selection
                self.clicked.emit(self.row_index)
            elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                # Shift+click: range selection (handled by parent)
                self.clicked.emit(self.row_index)
            else:
                # Normal click: single selection
                self.clicked.emit(self.row_index)
        
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click to open viewer"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.row_index)
        super().mouseDoubleClickEvent(event)

class GridView(QWidget):
    """Grid view for displaying comics as visual cards"""
    
    selection_changed = pyqtSignal()
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.selected_rows = set()
        self.cards = {}  # row_index -> ComicCard
        self.last_clicked_row = -1
        self.current_page = 0
        self.page_size = 20
        self.total_pages = 0
        
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """Initialize grid view UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create container widget for grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)

        # Add pagination controls
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Previous")
        self.page_label = QLabel("Page 1 of 1")
        self.next_button = QPushButton("Next ▶")
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        
        self.pagination_widget.setLayout(pagination_layout)
        main_layout.addWidget(self.pagination_widget)
        
        # Connect signals
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
    
    def connect_signals(self):
        """Connect to main window signals"""
        # Connect to sidebar filter signals
        self.main_window.sidebar.status_filter_changed.connect(self.refresh_grid)
        self.main_window.sidebar.tag_filter_changed.connect(self.refresh_grid)
        self.main_window.sidebar.filter_reset.connect(self.refresh_grid)
        
        # Connect to data update signals
        self.main_window.table_controller.data_added.connect(self.refresh_grid)
        self.main_window.table_controller.data_removed.connect(self.refresh_grid)
        self.main_window.table_controller.filter_state_changed.connect(self.refresh_grid)
    
    def refresh_grid(self):
        """Refresh the entire grid display"""
        # Clear existing cards
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        
        # Get visible rows from table
        visible_rows = []
        for row in range(self.main_window.table.rowCount()):
            if not self.main_window.table.isRowHidden(row):
                visible_rows.append(row)
        
        # Calculate pagination
        self.total_rows = len(visible_rows)
        self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)

        # Ensure current page is valid
        self.current_page = min(self.current_page, self.total_pages - 1)

        # Get data for current page
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_rows)
        current_page_rows = visible_rows[start_idx:end_idx]
        
        # Create cards for visible rows
        for i, row in enumerate(current_page_rows):
            row_data = self.main_window.get_row_data(row)
            card = ComicCard(row, row_data, self.main_window, self)
            
            row_pos = i // 4  # 4-column layout
            col_pos = i % 4
            self.grid_layout.addWidget(card, row_pos, col_pos)
            self.cards[row] = card

            # Set selection state
            card.set_selected(row in self.selected_rows)

            # Load cover AFTER card is fully set up
            QTimer.singleShot(100 * i, card.load_cover_image)  # Stagger the loading
        
        # Connect signals AFTER all cards are created
        QTimer.singleShot(50, self._connect_card_signals)

        # Update pagination display
        self.update_pagination_display()

    def _connect_card_signals(self):
        """Connect signals after cards are fully initialized"""
        for row, card in self.cards.items():
            if card:  # Check if card still exists
                card.clicked.connect(self.on_card_clicked)
                card.double_clicked.connect(self.on_card_double_clicked)
    
    def on_card_clicked(self, row):
        """Handle card click for selection"""
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+click: toggle selection
            if row in self.selected_rows:
                self.selected_rows.remove(row)
            else:
                self.selected_rows.add(row)
        
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift+click: select range
            if self.last_clicked_row >= 0:
                start = min(self.last_clicked_row, row)
                end = max(self.last_clicked_row, row)
                for r in range(start, end + 1):
                    if r in self.cards:  # Only select visible rows
                        self.selected_rows.add(r)
            else:
                self.selected_rows.add(row)
        
        else:
            # Normal click: single selection
            self.selected_rows = {row}
        
        self.last_clicked_row = row
        
        # Update visual selection
        self.update_selection_visuals()
        
        # Sync with table selection
        self.sync_to_table_selection()
        
        # Emit selection changed signal
        self.selection_changed.emit()
    
    def on_card_double_clicked(self, row):
        """Handle card double click to open viewer"""
        # Select the card first
        self.selected_rows = {row}
        self.update_selection_visuals()
        self.sync_to_table_selection()
        
        # Open viewer (same as table double click)
        self.main_window.on_table_double_click(
            self.main_window.table.model().index(row, 0)
        )
    
    def update_selection_visuals(self):
        """Update card visual selection states"""
        for row, card in self.cards.items():
            card.set_selected(row in self.selected_rows)
    
    def sync_to_table_selection(self):
        """Sync grid selection to table selection"""
        # Clear table selection
        self.main_window.table.clearSelection()
        
        # Select rows in table
        for row in self.selected_rows:
            if row < self.main_window.table.rowCount():
                # Select the entire row
                for col in range(self.main_window.table.columnCount()):
                    item = self.main_window.table.item(row, col)
                    if item:
                        item.setSelected(True)
    
    def sync_from_table_selection(self):
        """Sync grid selection from table selection"""
        table_selected = self.main_window.get_selected_rows()
        
        # Update grid selection
        new_selection = set(table_selected)
        if new_selection != self.selected_rows:
            self.selected_rows = new_selection
            self.update_selection_visuals()
            
            # Ensure selected cards are visible
            if self.selected_rows:
                # Scroll to first selected card
                first_selected = min(self.selected_rows)
                if first_selected in self.cards:
                    self.ensure_card_visible(first_selected)
    
    def ensure_card_visible(self, row):
        """Ensure the card at given row is visible in scroll area"""
        if row in self.cards:
            card = self.cards[row]
            # Scroll to make card visible
            self.parent().ensureWidgetVisible(card)
    
    def get_selected_rows(self):
        """Get currently selected rows in grid"""
        return sorted(list(self.selected_rows))

    def next_page(self):
        """Go to next page and preload the page after"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.refresh_grid()
            
            # Preload next page after showing current one
            QTimer.singleShot(100, self.preload_next_page)

    def prev_page(self):
        """Go to previous page and preload the page before"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_grid()
            QTimer.singleShot(100, self.preload_prev_page)

    def update_pagination_display(self):
        """Update pagination controls"""
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)

    def preload_next_page(self):
        """Preload covers for next page in background"""
        if self.current_page >= self.total_pages - 1:
            return  # No next page
        
        next_page_num = self.current_page + 1
        visible_rows = self.get_all_visible_rows()
        start_idx = next_page_num * self.page_size
        end_idx = min(start_idx + self.page_size, len(visible_rows))
        next_page_rows = visible_rows[start_idx:end_idx]
        
        # Preload covers for next page in background
        for row in next_page_rows:
            websign = self.main_window.get_cell_text(row, 0)  # Get websign
            if websign:
                # Request cover to cache it
                self.main_window.web_controller.get_cover_image(
                    websign, 
                    size=(130, 150)  # Appropriate size for grid cards
                )

    def get_all_visible_rows(self):
        """Get all visible row indices from table"""
        visible_rows = []
        for row in range(self.main_window.table.rowCount()):
            if not self.main_window.table.isRowHidden(row):
                visible_rows.append(row)
        return visible_rows

    def preload_prev_page(self):
        """Preload covers for previous page"""
        if self.current_page <= 0:
            return
        
        prev_page_num = self.current_page - 1
        visible_rows = self.get_all_visible_rows()
        start_idx = prev_page_num * self.page_size
        end_idx = min(start_idx + self.page_size, len(visible_rows))
        prev_page_rows = visible_rows[start_idx:end_idx]
        
        for row in prev_page_rows:
            websign = self.main_window.get_cell_text(row, 0)
            if websign:
                self.main_window.web_controller.get_cover_image(
                    websign, 
                    size=(130, 150)
                )