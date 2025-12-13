from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QScrollArea, QGridLayout, QSizePolicy,
                             QPushButton, QApplication, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import time

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

class GridDataModel:
    """Data model: manages visible rows and pagination"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.visible_rows_cache = []
        self.cache_timestamp = 0
        self.needs_rebuild = True
        
    def rebuild_if_needed(self):
        """Rebuild visible rows cache if needed"""
        if not self.needs_rebuild:
            return
            
        self.visible_rows_cache = []
        table = self.main_window.table
        
        # Collect all visible rows
        for row in range(table.rowCount()):
            if not table.isRowHidden(row):
                self.visible_rows_cache.append(row)
        
        self.cache_timestamp = time.time()
        self.needs_rebuild = False
        
    def get_visible_rows(self):
        """Get all visible rows (lazy rebuild)"""
        self.rebuild_if_needed()
        return self.visible_rows_cache
    
    def get_total_visible(self):
        """Get total number of visible rows"""
        self.rebuild_if_needed()
        return len(self.visible_rows_cache)
    
    def get_page_rows(self, page_num, page_size):
        """Get row indices for specific page"""
        self.rebuild_if_needed()
        
        total = len(self.visible_rows_cache)
        start_idx = page_num * page_size
        end_idx = min(start_idx + page_size, total)
        
        if start_idx >= total:
            return []
            
        return self.visible_rows_cache[start_idx:end_idx]
    
    def invalidate_cache(self):
        """Mark cache as needing rebuild"""
        self.needs_rebuild = True


class RowDataCache:
    """Row data cache: reduces table access operations"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.cache = {}  # row -> row_data
        self.hits = 0
        self.misses = 0
        
    def get_row_data(self, row):
        """Get row data, using cache if available"""
        if row in self.cache:
            self.hits += 1
            return self.cache[row]
        
        # Cache miss, fetch from table
        self.misses += 1
        data = self.main_window.get_row_data(row)
        self.cache[row] = data
        return data
    
    def invalidate_row(self, row):
        """Invalidate cache for specific row"""
        if row in self.cache:
            del self.cache[row]
    
    def invalidate_all(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'cache_size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }


class VirtualizedGridView(QWidget):
    """Virtualized grid view: only creates cards for current page"""
    
    selection_changed = pyqtSignal()
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Initialize components
        self.data_model = GridDataModel(main_window)
        self.data_cache = RowDataCache(main_window)
        
        # State management
        self.current_page = 0
        self.page_size = 20
        self.cards = {}  # Only stores cards for current page
        self.selected_rows = set()  # Stores all selected rows (even not on current page)
        self.total_pages = 0
        
        # Initialize UI
        self.init_ui()
        self.connect_signals()
        
        # Performance monitoring
        self.debug_mode = True
        
    def init_ui(self):
        """Initialize the virtualized grid view UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)
        
        # Create scroll area for virtual scrolling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create container widget for grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)
        
        # Create pagination controls
        self.create_pagination_controls()
        main_layout.addWidget(self.pagination_widget)
        
        self.setLayout(main_layout)
        
    def create_pagination_controls(self):
        """Create pagination control widgets"""
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Previous")
        self.page_label = QLabel("Page 1 of 1")
        self.next_button = QPushButton("Next ▶")
        
        # Optional: page size selector
        self.page_size_label = QLabel("Items per page:")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "30", "50"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_size_label)
        pagination_layout.addWidget(self.page_size_combo)
        
        self.pagination_widget.setLayout(pagination_layout)
        
        # Connect signals
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        
    def connect_signals(self):
        """Connect to main window signals for cache invalidation"""
        # Connect to signals that require cache invalidation
        self.main_window.sidebar.status_filter_changed.connect(self.invalidate_caches)
        self.main_window.sidebar.tag_filter_changed.connect(self.invalidate_caches)
        self.main_window.sidebar.filter_reset.connect(self.invalidate_caches)
        
        # Data change signals
        self.main_window.table_controller.data_added.connect(self.on_data_changed)
        self.main_window.table_controller.data_removed.connect(self.on_data_changed)
        self.main_window.table_controller.filter_state_changed.connect(self.on_data_changed)
        
    def invalidate_caches(self):
        """Invalidate all caches when filters change"""
        self.data_model.invalidate_cache()
        self.data_cache.invalidate_all()
        self.refresh_current_page()
        
    def on_data_changed(self):
        """Handle data changes (add, remove, filter)"""
        self.data_model.invalidate_cache()
        self.refresh_current_page()
        
    def on_page_size_changed(self, new_size):
        """Handle page size change"""
        try:
            self.page_size = int(new_size)
            self.refresh_current_page()
        except ValueError:
            pass
            
    def refresh_current_page(self):
        """Refresh only the current page"""
        if self.debug_mode:
            start_time = time.time()
            print(f"[{start_time:.3f}] refresh_current_page called, page {self.current_page}")
        
        # Clear current page cards
        self.clear_current_page_cards()
        
        # Get rows for current page
        page_rows = self.data_model.get_page_rows(self.current_page, self.page_size)
        
        if self.debug_mode:
            print(f"[{time.time():.3f}] Creating {len(page_rows)} cards")
        
        # Create cards only for current page
        for i, row in enumerate(page_rows):
            # Get row data from cache
            row_data = self.data_cache.get_row_data(row)
            
            # Create card
            card = ComicCard(row, row_data, self.main_window, self)
            card.clicked.connect(self.on_card_clicked)
            card.double_clicked.connect(self.on_card_double_clicked)
            
            # Add to grid
            row_pos = i // 4  # 4 columns per row
            col_pos = i % 4
            self.grid_layout.addWidget(card, row_pos, col_pos)
            self.cards[row] = card
            
            # Update selection state
            card.set_selected(row in self.selected_rows)
        
        # Update pagination
        total_visible = self.data_model.get_total_visible()
        self.total_pages = max(1, (total_visible + self.page_size - 1) // self.page_size)
        self.update_pagination_display()
        
        if self.debug_mode:
            end_time = time.time()
            print(f"[{end_time:.3f}] refresh_current_page completed in {end_time - start_time:.3f}s")
            print(f"  Cache stats: {self.data_cache.get_stats()}")
            
        # Preload next page covers
        QTimer.singleShot(200, self.preload_next_page_covers)
        
    def clear_current_page_cards(self):
        """Clear only the cards from current page"""
        if self.debug_mode:
            print(f"[{time.time():.3f}] Clearing {len(self.cards)} cards")
        
        for row, card in self.cards.items():
            card.deleteLater()
        self.cards.clear()
        
        # Clear the grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def update_pagination_display(self):
        """Update pagination controls display"""
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)
        
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.refresh_current_page()
            
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_current_page()
            
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
            # Shift+click: select range (simplified for virtualization)
            self.selected_rows.add(row)
        else:
            # Normal click: single selection
            self.selected_rows = {row}
        
        # Update visual selection for current page cards
        for card_row, card in self.cards.items():
            card.set_selected(card_row in self.selected_rows)
        
        # Sync with table selection
        self.sync_to_table_selection()
        
        # Emit selection changed signal
        self.selection_changed.emit()
        
    def on_card_double_clicked(self, row):
        """Handle card double click"""
        self.selected_rows = {row}
        self.sync_to_table_selection()
        
        # Open viewer
        self.main_window.on_table_double_click(
            self.main_window.table.model().index(row, 0)
        )
        
    def sync_to_table_selection(self):
        """Sync grid selection to table selection"""
        self.main_window.table.clearSelection()
        for row in self.selected_rows:
            if row < self.main_window.table.rowCount():
                for col in range(self.main_window.table.columnCount()):
                    item = self.main_window.table.item(row, col)
                    if item:
                        item.setSelected(True)
                        
    def preload_next_page_covers(self):
        """Preload covers for next page"""
        if self.current_page >= self.total_pages - 1:
            return
            
        next_page_rows = self.data_model.get_page_rows(self.current_page + 1, self.page_size)
        for row in next_page_rows:
            websign = self.main_window.get_cell_text(row, 0)
            if websign:
                # Preload to cache
                self.main_window.web_controller.get_cover_image(
                    websign, 
                    size=(130, 150)
                )
                
    def get_selected_rows(self):
        """Get currently selected rows"""
        return sorted(list(self.selected_rows))