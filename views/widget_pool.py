"""
Widget pool for managing reusable comic card widgets
Fixed number of QWidget instances are reused as user scrolls
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
import time
from typing import Dict, List, Tuple, Optional, Set, Any


class ComicCardWidget(QFrame):
    """
    Comic card widget used in widget pool
    
    This is a simplified version of the original ComicCard
    designed for reuse in widget pool
    """
    
    clicked = pyqtSignal(int)  # Emits row index when clicked
    double_clicked = pyqtSignal(int)  # Emits row index when double-clicked
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.current_row = -1
        self.is_selected = False
        
        # Setup fixed size
        self.setFixedSize(140, 250)
        self.setMinimumSize(140, 250)
        self.setMaximumSize(140, 250)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)

        from PyQt6.QtWidgets import QSizePolicy
        size_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setSizePolicy(size_policy)
        
        # Initialize UI
        self.init_ui()
        self.update_style()
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
    def init_ui(self):
        """Initialize card UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(120, 170)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
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
        
        # Author
        self.author_label = QLabel()
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
            }
        """)
        
        # Status
        self.status_label = QLabel()
        self.status_label.setFixedHeight(16)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.cover_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.author_label)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def update_content(self, row_data: Dict[str, str], row_index: int):
        """
        Update widget content with new data
        
        Args:
            row_data: Comic data dictionary
            row_index: Current row index
        """
        self.current_row = row_index
        
        # Title
        title = row_data.get('title', '')
        if len(title) > 10:
            title = title[:8] + '...'
        self.title_label.setText(title)
        
        # Author
        author = row_data.get('author', '')
        self.author_label.setText(author)
        
        # Status
        status = row_data.get('read_status', 'unread')
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
        
        # Schedule cover loading
        QTimer.singleShot(10, self.load_cover_image)
        
    def load_cover_image(self):
        """
        Load cover image for current row
        Uses main window's web_controller with safety checks
        """
        if self.current_row < 0 or not self.isVisible():
            return
            
        # Get row data from model
        if not hasattr(self.main_window, 'table'):
            return
            
        model = self.main_window.table.get_model()
        if not model:
            return
            
        row_data = model.get_row_data(self.current_row)
        if not row_data:
            return
            
        websign = row_data.get('websign', '')
        if not websign:
            self.show_no_cover()
            return
            
        # Load cover using web_controller
        try:
            if hasattr(self.main_window, 'web_controller'):
                pixmap = self.main_window.web_controller.get_cover_image(
                    str(websign),
                    size=(130, 150)
                )
                
                if pixmap and not pixmap.isNull():
                    self.display_cover(pixmap)
                else:
                    self.show_no_cover()
            else:
                self.show_no_cover()
                
        except Exception as e:
            print(f"Error loading cover: {e}")
            self.show_no_cover()
            
    def display_cover(self, pixmap: QPixmap):
        """
        Display cover pixmap with proper scaling
        """
        label_size = self.cover_label.size()
        pixmap_size = pixmap.size()
        
        # Calculate scale to fit
        width_ratio = label_size.width() / pixmap_size.width()
        height_ratio = label_size.height() / pixmap_size.height()
        scale_factor = min(width_ratio, height_ratio)
        
        # Scale
        new_width = int(pixmap_size.width() * scale_factor)
        new_height = int(pixmap_size.height() * scale_factor)
        
        scaled_pixmap = pixmap.scaled(
            new_width, new_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.cover_label.setPixmap(scaled_pixmap)
        self.cover_label.setText("")
        
    def show_no_cover(self):
        """Show 'No cover' placeholder"""
        self.cover_label.clear()
        self.cover_label.setText("No cover")
        self.cover_label.setStyleSheet("color: #6c757d; font-style: italic;")
        
    def set_selected(self, selected: bool):
        """Update selection state"""
        self.is_selected = selected
        self.update_style()
        
    def update_style(self):
        """Update visual style based on selection state"""
        if self.is_selected:
            self.setStyleSheet("""
                ComicCardWidget {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                ComicCardWidget {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
                ComicCardWidget:hover {
                    background-color: #f8f9fa;
                    border: 1px solid #adb5bd;
                }
            """)
            
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton and self.current_row >= 0:
            self.clicked.emit(self.current_row)
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        if event.button() == Qt.MouseButton.LeftButton and self.current_row >= 0:
            self.double_clicked.emit(self.current_row)
        super().mouseDoubleClickEvent(event)
        
    def clear(self):
        """Clear widget content for reuse"""
        self.current_row = -1
        self.is_selected = False
        self.cover_label.clear()
        self.title_label.clear()
        self.author_label.clear()
        self.status_label.clear()
        self.update_style()


class WidgetPool:
    """
    Manages a pool of reusable comic card widgets
    """
    
    def __init__(self, main_window, max_size: int = 50):
        self.main_window = main_window
        self.max_size = max_size
        
        # Pool management
        self._available_widgets: List[ComicCardWidget] = []
        self._in_use_widgets: Dict[int, ComicCardWidget] = {}  # row -> widget
        self._visible_rows: Set[int] = set()
        
        # Performance tracking
        self._stats = {
            'created': 0,
            'reused': 0,
            'released': 0,
            'max_used': 0
        }
        
        # Pre-create some widgets
        self._precreate_widgets(10)
        
    def _precreate_widgets(self, count: int):
        """Pre-create some widgets"""
        for _ in range(min(count, self.max_size)):
            widget = ComicCardWidget(self.main_window)
            self._available_widgets.append(widget)
            self._stats['created'] += 1
            
    def acquire_widget(self, row: int, row_data: Dict[str, str]) -> Optional[ComicCardWidget]:
        """
        Acquire a widget for a specific row
        
        Args:
            row: Row index
            row_data: Data for the row
            
        Returns:
            ComicCardWidget or None if pool is full
        """
        # Check if already has a widget
        if row in self._in_use_widgets:
            widget = self._in_use_widgets[row]
            widget.update_content(row_data, row)
            return widget
            
        # Try to get from available pool
        if self._available_widgets:
            widget = self._available_widgets.pop()
            self._stats['reused'] += 1
        else:
            # Create new widget if pool not full
            if len(self._in_use_widgets) < self.max_size:
                widget = ComicCardWidget(self.main_window)
                self._stats['created'] += 1
            else:
                # Pool is full, can't acquire more
                return None
                
        # Setup widget
        widget.current_row = row
        widget.update_content(row_data, row)
        
        # FIX: Disconnect all previous connections
        try:
            widget.clicked.disconnect()
        except TypeError:
            # If no connections, just pass
            pass
            
        try:
            widget.double_clicked.disconnect()
        except TypeError:
            # If no connections, just pass
            pass
        
        # Connect signals with lambda that captures current row
        widget.clicked.connect(lambda r=row: self._on_widget_clicked(r))
        widget.double_clicked.connect(lambda r=row: self._on_widget_double_clicked(r))
        
        # Add to in-use map
        self._in_use_widgets[row] = widget
        self._visible_rows.add(row)
        
        # Update max used
        current_used = len(self._in_use_widgets)
        if current_used > self._stats['max_used']:
            self._stats['max_used'] = current_used
            
        return widget
        
    def release_widget(self, row: int):
        """
        Release widget for a specific row
        
        Args:
            row: Row index to release
        """
        if row in self._in_use_widgets:
            widget = self._in_use_widgets[row]
            
            # Clear widget
            widget.clear()
            
            # Remove from in-use
            del self._in_use_widgets[row]
            self._visible_rows.discard(row)
            
            # Return to available pool
            self._available_widgets.append(widget)
            self._stats['released'] += 1
            
    def update_visible_range(self, start_row: int, end_row: int):
        """
        Update visible range, managing widget allocation
        
        Args:
            start_row: First visible row
            end_row: Last visible row
        """
        visible_set = set(range(start_row, end_row + 1))
        
        # Release widgets for rows no longer visible
        to_release = self._visible_rows - visible_set
        for row in to_release:
            self.release_widget(row)
            
        self._visible_rows = visible_set
        
    def get_widget_for_row(self, row: int) -> Optional[ComicCardWidget]:
        """
        Get widget for a specific row
        
        Args:
            row: Row index
            
        Returns:
            ComicCardWidget or None if not allocated
        """
        return self._in_use_widgets.get(row)
        
    def get_visible_widgets(self) -> List[Tuple[int, ComicCardWidget]]:
        """
        Get all currently visible widgets
        
        Returns:
            List of (row, widget) tuples
        """
        return [(row, widget) for row, widget in self._in_use_widgets.items()]
        
    def invalidate_all(self):
        """
        Release all widgets
        """
        rows = list(self._in_use_widgets.keys())
        for row in rows:
            self.release_widget(row)
            
    def cleanup(self):
        """
        Clean up all widgets
        """
        self.invalidate_all()
        for widget in self._available_widgets:
            widget.deleteLater()
        self._available_widgets.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics
        
        Returns:
            dict: Statistics
        """
        return {
            **self._stats,
            'available': len(self._available_widgets),
            'in_use': len(self._in_use_widgets),
            'total': len(self._available_widgets) + len(self._in_use_widgets),
            'visible_rows': len(self._visible_rows)
        }

    def _on_widget_clicked(self, row: int):
        """Handle widget click - forward to main window"""
        if hasattr(self.main_window, 'on_widget_clicked'):
            self.main_window.on_widget_clicked(row)