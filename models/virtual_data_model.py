"""
Virtual data model optimized for 2500+ records
Uses memory-efficient data structures and lazy evaluation
"""
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant
from PyQt6.QtGui import QColor
from typing import List, Dict, Any, Optional, Union
import time
from enum import Enum


class ReadStatus(Enum):
    """Enum for read status to avoid string comparisons"""
    UNREAD = 0
    READING = 1
    COMPLETED = 2
    
    @classmethod
    def from_string(cls, status_str: str) -> 'ReadStatus':
        """Convert string to enum"""
        status_str = status_str.lower().strip()
        if status_str == 'reading':
            return cls.READING
        elif status_str == 'completed':
            return cls.COMPLETED
        else:
            return cls.UNREAD
    
    def to_string(self) -> str:
        """Convert enum to display string"""
        return self.name.capitalize()
    
    def to_color(self) -> str:
        """Get color for this status"""
        colors = {
            ReadStatus.UNREAD: '#e74c3c',     # Red
            ReadStatus.READING: '#f39c12',    # Orange
            ReadStatus.COMPLETED: '#27ae60'   # Green
        }
        return colors.get(self, '#95a5a6')


class VirtualDataModel(QAbstractTableModel):
    """
    Virtual data model optimized for large datasets (2500+ records)
    Uses memory-efficient storage and lazy evaluation
    """
    
    # Column definitions with metadata
    COLUMNS = [
        {'name': 'websign', 'display': 'Websign', 'type': 'str', 'width': 80},
        {'name': 'author', 'display': 'Author', 'type': 'str', 'width': 120},
        {'name': 'title', 'display': 'Title', 'type': 'str', 'width': 200},
        {'name': 'group', 'display': 'Group', 'type': 'str', 'width': 100},
        {'name': 'show', 'display': 'Show', 'type': 'str', 'width': 100},
        {'name': 'magazine', 'display': 'Magazine', 'type': 'str', 'width': 120},
        {'name': 'origin', 'display': 'Origin', 'type': 'str', 'width': 120},
        {'name': 'tag', 'display': 'Tag', 'type': 'str', 'width': 150},
        {'name': 'read_status', 'display': 'Read Status', 'type': 'status', 'width': 80},
        {'name': 'progress', 'display': 'Progress', 'type': 'progress', 'width': 80},
        {'name': 'file_path', 'display': 'File Path', 'type': 'str', 'width': 100},
    ]
    
    # Create reverse lookup for column names
    COLUMN_INDEX = {col['name']: idx for idx, col in enumerate(COLUMNS)}
    
    def __init__(self):
        super().__init__()
        
        # Core data storage
        self._raw_data = []
        self._row_count = 0
        
        # Filtering and visibility
        self._visible_rows = []
        self._filter_active = False
        self._filters = {}
        
        # Text search filter
        self._text_filter_options = {}
        self._text_filter_active = False
        self._text_filter_matches = set()
        
        # Custom filter
        self._custom_filter = None
        self._custom_filter_active = False
        
        # Styling
        self._row_styles = {}
        
        # Caches
        self._display_cache = {}
        self._user_data_cache = {}
        self._sort_cache = {}
        
        # Performance monitoring
        self._access_stats = {'hits': 0, 'misses': 0, 'filter_rebuilds': 0}
        self._last_filter_rebuild = 0
        
        # Initialize visible rows
        self._rebuild_visible_rows()
    
    # ==================== Qt Model Interface ====================
    
    def rowCount(self, parent: QModelIndex = None) -> int:
        """Return number of visible rows"""
        if parent and parent.isValid():
            return 0
        return len(self._visible_rows)
    
    def columnCount(self, parent: QModelIndex = None) -> int:
        """Return number of columns"""
        if parent and parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get data for given index and role"""
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._visible_rows) or col < 0 or col >= len(self.COLUMNS):
            return QVariant()
        
        # Get actual row index in raw data
        actual_row = self._visible_rows[row]
        
        # Check cache first
        cache_key = f"{actual_row}_{col}_{role}"
        if cache_key in self._display_cache:
            self._access_stats['hits'] += 1
            return self._display_cache[cache_key]
        
        self._access_stats['misses'] += 1
        
        # Get raw data
        raw_value = self._get_raw_value(actual_row, col)
        
        # Process based on role
        if role in [Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole]:
            # Handle styling roles
            result = self._process_style_data(actual_row, col, role)
        else:
            # Handle other roles
            result = self._process_data(raw_value, col, role)
        
        # Cache the result (except for styling roles which may change)
        if role not in [Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole]:
            self._display_cache[cache_key] = result
        
        return result

    def _process_style_data(self, actual_row: int, col: int, role: int) -> Any:
        """
        Process styling data for a cell
        
        Args:
            actual_row: Actual row index in raw data
            col: Column index
            role: Style role (BackgroundRole or ForegroundRole)
        
        Returns:
            QBrush or QVariant: Style data
        """
        if not hasattr(self, '_row_styles') or actual_row not in self._row_styles:
            return QVariant()
        
        row_style = self._row_styles[actual_row]
        
        if role == Qt.ItemDataRole.BackgroundRole and 'background' in row_style:
            from PyQt6.QtGui import QBrush
            return QBrush(row_style['background'])
        elif role == Qt.ItemDataRole.ForegroundRole and 'foreground' in row_style:
            from PyQt6.QtGui import QBrush
            return QBrush(row_style['foreground'])
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get header data"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self.COLUMNS):
                    return self.COLUMNS[section]['display']
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        
        elif role == Qt.ItemDataRole.UserRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self.COLUMNS):
                    return self.COLUMNS[section]['name']
        
        return QVariant()
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Get item flags"""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        flags = super().flags(index)
        flags |= Qt.ItemFlag.ItemIsSelectable
        flags |= Qt.ItemFlag.ItemIsEnabled
        
        # Make certain columns editable if needed
        if index.column() in [1, 2, 3, 7]:  # Author, Title, Group, Tag
            flags |= Qt.ItemFlag.ItemIsEditable
        
        return flags
    
    # ==================== Data Management ====================
    
    def add_row(self, row_data: Dict[str, Any]) -> None:
        """Add a new row to the model"""
        # Convert dict to tuple for efficient storage
        tuple_data = self._dict_to_tuple(row_data)
        
        # Add to raw data
        self._raw_data.append(tuple_data)
        self._row_count += 1
        
        # Update visible rows if needed
        if self._should_row_be_visible(tuple_data):
            position = len(self._visible_rows)
            self.beginInsertRows(QModelIndex(), position, position)
            self._visible_rows.append(self._row_count - 1)
            self.endInsertRows()
        else:
            # Just add to visible rows without emitting signals
            self._visible_rows.append(self._row_count - 1)
        
        # Clear relevant caches
        self._invalidate_caches()
    
    def add_rows(self, rows_data: List[Dict[str, Any]]) -> None:
        """Add multiple rows efficiently"""
        if not rows_data:
            return
        
        # Batch insertion for better performance
        start_pos = len(self._visible_rows)
        new_visible_indices = []
        new_tuples = []
        
        for row_data in rows_data:
            tuple_data = self._dict_to_tuple(row_data)
            new_tuples.append(tuple_data)
            self._row_count += 1
            
            if self._should_row_be_visible(tuple_data):
                new_visible_indices.append(self._row_count - 1)
        
        # Add to raw data
        self._raw_data.extend(new_tuples)
        
        # Update visible rows
        if new_visible_indices:
            end_pos = start_pos + len(new_visible_indices) - 1
            self.beginInsertRows(QModelIndex(), start_pos, end_pos)
            self._visible_rows.extend(new_visible_indices)
            self.endInsertRows()
        else:
            self._visible_rows.extend(new_visible_indices)
        
        # Clear caches
        self._invalidate_caches()
    
    def remove_row(self, row: int) -> None:
        """Remove a row by visible index"""
        if row < 0 or row >= len(self._visible_rows):
            return
        
        actual_row = self._visible_rows[row]
        
        # Remove from raw data
        if 0 <= actual_row < len(self._raw_data):
            # Mark as removed (we'll just filter it out)
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._visible_rows[row]
            self.endRemoveRows()
            
            # Note: We don't actually remove from _raw_data to preserve indices
            # Instead, we'll filter it out in _should_row_be_visible
        
        self._invalidate_caches()
    
    def get_row_data(self, visible_row: int) -> Dict[str, Any]:
        """Get row data as dictionary"""
        if visible_row < 0 or visible_row >= len(self._visible_rows):
            return {}
        
        actual_row = self._visible_rows[visible_row]
        if actual_row >= len(self._raw_data):
            return {}
        
        return self._tuple_to_dict(self._raw_data[actual_row])
    
    def get_raw_row_index(self, visible_row: int) -> int:
        """Get actual row index in raw data from visible row index"""
        if visible_row < 0 or visible_row >= len(self._visible_rows):
            return -1
        return self._visible_rows[visible_row]

    # ==================== Sorting ====================

    def sort(self, column, order):
        """
        Sort data by specified column
        
        Args:
            column: Column index to sort by (0-based)
            order: Qt.SortOrder.AscendingOrder or Qt.SortOrder.DescendingOrder
        """
        # Emit signal that layout is about to change
        self.layoutAboutToBeChanged.emit()
        
        try:
            # Get column info
            if column >= len(self.COLUMNS):
                print(f"[ERROR] Invalid column index: {column}")
                return
                
            column_name = self.COLUMNS[column]['name']
            column_type = self.COLUMNS[column]['type']
            
            # Define sort key function based on column type
            def sort_key(row_idx):
                """Extract value for sorting from tuple data"""
                tuple_data = self._raw_data[row_idx]
                
                if column >= len(tuple_data):
                    # Return appropriate default based on column
                    if column == 0:  # websign
                        return 0  # Default to 0 for int columns
                    elif column_type == 'progress':
                        return 0
                    elif column_type == 'status':
                        return 0  # unread
                    else:
                        return ""
                    
                value = tuple_data[column]
                
                # Special handling for websign column (column 0)
                if column == 0:  # websign column
                    # Treat as integer
                    try:
                        if value is None or value == "":
                            return 0
                        # Convert to int
                        return int(value)
                    except (ValueError, TypeError):
                        # If can't convert to int, try to extract numbers from string
                        try:
                            import re
                            numbers = re.findall(r'\d+', str(value))
                            if numbers:
                                return int(numbers[0])
                            return 0
                        except:
                            return 0
                
                # Handle different column types for other columns
                elif column_type == 'progress':
                    # Sort numerically for progress
                    try:
                        return int(value) if value is not None else 0
                    except (ValueError, TypeError):
                        return 0
                        
                elif column_type == 'status':
                    # Sort by status order: unread < reading < completed
                    status_order = {'unread': 0, 'reading': 1, 'completed': 2}
                    status = str(value).lower() if value else 'unread'
                    return status_order.get(status, 3)
                    
                else:  # 'str' type or others
                    # String comparison (case-insensitive)
                    if value is None:
                        return ""
                    elif isinstance(value, (int, float)):
                        # For numeric values in string columns
                        return str(value).zfill(10)  # Pad with zeros for proper numeric sorting
                    else:
                        return str(value).lower()
            
            # Determine what to sort
            if self._filter_active:
                # When filtering, we need to sort the actual data array
                all_indices = list(range(len(self._raw_data)))
                
                # Sort all data
                reverse = (order == Qt.SortOrder.DescendingOrder)
                all_indices.sort(key=sort_key, reverse=reverse)
                
                # Reorder raw data
                self._raw_data = [self._raw_data[i] for i in all_indices]
                
                # Rebuild visible rows (will respect filters)
                self._rebuild_visible_rows()
                
            else:
                # No filter - sort visible rows (which are all rows)
                rows_to_sort = self._visible_rows.copy()
                
                reverse = (order == Qt.SortOrder.DescendingOrder)
                rows_to_sort.sort(key=sort_key, reverse=reverse)
                
                # Update visible rows order
                self._visible_rows = rows_to_sort
            
            # Clear caches since order changed
            self._display_cache.clear()
            self._user_data_cache.clear()
            self._sort_cache.clear()
            
        except Exception as e:
            print(f"[ERROR] Sorting failed: {e}")
        
        # Emit signal that layout has changed
        self.layoutChanged.emit()
    
    # ==================== Filtering ====================
    
    def set_status_filter(self, status: str) -> None:
        """Filter by read status"""
        if status == 'all':
            if 'status' in self._filters:
                del self._filters['status']
        else:
            self._filters['status'] = status
        
        self._apply_filters()
    
    def set_tag_filter(self, tags: List[str]) -> None:
        """Filter by tags"""
        if not tags:
            if 'tags' in self._filters:
                del self._filters['tags']
        else:
            self._filters['tags'] = tags
        
        self._apply_filters()
    
    def clear_filters(self) -> None:
        """Clear all filters"""
        self._filters.clear()
        self._apply_filters()
    
    def _apply_filters(self) -> None:
        """Apply all active filters"""
        old_count = len(self._visible_rows)
        
        self.beginResetModel()
        self._rebuild_visible_rows()
        self.endResetModel()
        
        new_count = len(self._visible_rows)
        self._access_stats['filter_rebuilds'] += 1
        self._last_filter_rebuild = time.time()
        
        # Emit signal if row count changed
        if old_count != new_count:
            self.layoutChanged.emit()
    
    def _rebuild_visible_rows(self):
        """Rebuild list of visible rows based on all active filters"""
        if not self._filters and not self._text_filter_active and not self._custom_filter_active:
            # No filters, all rows visible
            self._visible_rows = list(range(len(self._raw_data)))
            self._filter_active = False
            return
        
        self._visible_rows = []
        self._filter_active = True
        
        for i, row_data in enumerate(self._raw_data):
            # Check all filters
            if self._should_row_be_visible(row_data, i):
                self._visible_rows.append(i)
        
        print(f"Rebuilt visible rows: {len(self._visible_rows)}/{len(self._raw_data)} visible")

    def _is_row_in_text_filter(self, row_index: int, row_data: tuple) -> bool:
        """
        Check if a row should be visible based on text filter
        
        Args:
            row_index: Raw row index
            row_data: Row data as tuple
        
        Returns:
            bool: True if row should be visible with text filter
        """
        if not self._text_filter_active:
            return True
        
        if not hasattr(self, '_text_filter_options') or not self._text_filter_options:
            return True
        
        # Get search options
        condition1 = self._text_filter_options.get('condition1')
        condition2 = self._text_filter_options.get('condition2')
        logic = self._text_filter_options.get('logic', 'AND').upper()
        case_sensitive = self._text_filter_options.get('case_sensitive', False)
        use_regex = self._text_filter_options.get('use_regex', False)
        
        if not condition1:
            return True
        
        # Check first condition
        matches_cond1 = self._check_row_condition(row_data, condition1, case_sensitive, use_regex)
        
        # Check second condition if present
        if condition2:
            matches_cond2 = self._check_row_condition(row_data, condition2, case_sensitive, use_regex)
            
            # Apply logic
            if logic == 'AND':
                matches = matches_cond1 and matches_cond2
            else:  # 'OR'
                matches = matches_cond1 or matches_cond2
        else:
            matches = matches_cond1
        
        return matches
    
    def _should_row_be_visible(self, row_data: tuple, row_index: int = -1) -> bool:
        """
        Check if a row should be visible with all active filters
        
        Args:
            row_data: Row data as tuple
            row_index: Actual row index in raw data
        
        Returns:
            bool: True if row should be visible
        """
        # No filters active
        if not self._filters and not self._text_filter_active and not self._custom_filter_active:
            return True
        
        # Check status filter
        if 'status' in self._filters:
            row_dict = self._tuple_to_dict(row_data)
            if row_dict.get('read_status', '').lower() != self._filters['status']:
                return False
        
        # Check tag filter
        if 'tags' in self._filters:
            row_dict = self._tuple_to_dict(row_data)
            row_tags = [tag.strip() for tag in row_dict.get('tag', '').split(',') if tag.strip()]
            filter_tags = self._filters['tags']
            
            if not any(tag in filter_tags for tag in row_tags):
                return False
        
        # Check text filter
        if self._text_filter_active:
            if not self._is_row_in_text_filter(row_index, row_data):
                return False
        
        # Check custom filter
        if self._custom_filter_active and hasattr(self, '_custom_filter') and self._custom_filter:
            if not self._custom_filter(row_data, row_index):
                return False
        
        return True
    
    # ==================== Performance Optimizations ====================
    
    def _get_raw_value(self, row: int, col: int) -> Any:
        """Get raw value from storage"""
        if row < 0 or row >= len(self._raw_data) or col < 0 or col >= len(self.COLUMNS):
            return None
        
        return self._raw_data[row][col]
    
    def _process_data(self, raw_value: Any, col: int, role: int) -> Any:
        """Process raw value based on column and role"""
        column_type = self.COLUMNS[col]['type']
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_display_value(raw_value, column_type)
        
        elif role == Qt.ItemDataRole.UserRole:
            return self._format_user_value(raw_value, column_type)
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if column_type == 'progress':
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            if column_type == 'status' and raw_value:
                status = ReadStatus.from_string(raw_value)
                return QColor(status.to_color())
        
        return QVariant()
    
    def _format_display_value(self, value: Any, column_type: str) -> str:
        """Format value for display"""
        if value is None:
            return ""
        
        if column_type == 'progress':
            # Add % sign for display
            try:
                progress = int(value)
                return f"{progress}%"
            except (ValueError, TypeError):
                return "0%"
        
        elif column_type == 'status':
            # Capitalize status for display
            if isinstance(value, str):
                return value.capitalize()
        
        return str(value)
    
    def _format_user_value(self, value: Any, column_type: str) -> Any:
        """Format value for UserRole (internal storage)"""
        if value is None:
            return ""
        
        if column_type == 'progress':
            # Remove % sign for storage
            if isinstance(value, str):
                value = value.replace('%', '')
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        elif column_type == 'status':
            # Convert to lowercase for consistent comparison
            if isinstance(value, str):
                return value.lower()
        
        return value
    
    def _dict_to_tuple(self, row_data: Dict[str, Any]) -> tuple:
        """Convert dictionary to tuple for efficient storage"""
        # Ensure all columns are present in the correct order
        values = []
        for col in self.COLUMNS:
            col_name = col['name']
            value = row_data.get(col_name, "")
            
            # Special handling for certain columns
            if col['type'] == 'progress':
                if isinstance(value, str):
                    value = value.replace('%', '')
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = 0
            
            elif col['type'] == 'status':
                if isinstance(value, str):
                    value = value.lower()
            
            values.append(value)
        
        return tuple(values)
    
    def _tuple_to_dict(self, row_tuple: tuple) -> Dict[str, Any]:
        """Convert tuple back to dictionary"""
        if len(row_tuple) != len(self.COLUMNS):
            return {}
        
        result = {}
        for i, col in enumerate(self.COLUMNS):
            result[col['name']] = row_tuple[i]
        
        return result
    
    def _invalidate_caches(self) -> None:
        """Invalidate performance caches"""
        self._display_cache.clear()
        self._user_data_cache.clear()
        self._sort_cache.clear()
    
    # ==================== Public API ====================
    
    def get_total_rows(self) -> int:
        """Get total number of rows (including filtered out)"""
        return len(self._raw_data)
    
    def get_visible_rows(self) -> List[int]:
        """Get list of visible row indices"""
        return self._visible_rows.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'total_rows': len(self._raw_data),
            'visible_rows': len(self._visible_rows),
            'cache_hits': self._access_stats['hits'],
            'cache_misses': self._access_stats['misses'],
            'cache_hit_rate': (
                self._access_stats['hits'] / (self._access_stats['hits'] + self._access_stats['misses']) * 100
                if (self._access_stats['hits'] + self._access_stats['misses']) > 0 else 0
            ),
            'filter_rebuilds': self._access_stats['filter_rebuilds'],
            'last_filter_rebuild': self._last_filter_rebuild,
        }
    
    def clear_all_data(self) -> None:
        """Clear all data from the model"""
        self.beginResetModel()
        self._raw_data.clear()
        self._row_count = 0
        self._visible_rows.clear()
        self._filters.clear()
        self._invalidate_caches()
        self.endResetModel()
    
    def load_from_list(self, data_list: List[Dict[str, Any]]) -> None:
        """Load data from list of dictionaries"""
        self.beginResetModel()
        self.clear_all_data()
        self.add_rows(data_list)
        self.endResetModel()

    def update_row(self, visible_row: int, row_data: Dict[str, Any]) -> bool:
        """
        Update an existing row with new data
        
        Args:
            visible_row: Visible row index (after filtering)
            row_data: Dictionary with new row data
        
        Returns:
            bool: True if successful, False otherwise
        """
        if visible_row < 0 or visible_row >= len(self._visible_rows):
            return False
        
        # Get actual row index in raw data
        actual_row = self._visible_rows[visible_row]
        
        if actual_row < 0 or actual_row >= len(self._raw_data):
            return False
        
        try:
            # Convert dict to tuple
            new_tuple = self._dict_to_tuple(row_data)
            
            # Update raw data
            self._raw_data[actual_row] = new_tuple
            
            # Invalidate caches for this row
            self._invalidate_row_caches(actual_row)
            
            # Emit dataChanged signal for all columns of this row
            top_left = self.createIndex(visible_row, 0)
            bottom_right = self.createIndex(visible_row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [])
            
            return True
            
        except Exception as e:
            print(f"Error updating row {visible_row}: {e}")
            return False

    def _invalidate_row_caches(self, actual_row: int):
        """
        Invalidate caches for a specific row
        
        Args:
            actual_row: Actual row index in raw data
        """
        # Invalidate display cache
        keys_to_remove = []
        for key in self._display_cache:
            if key.startswith(f"{actual_row}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._display_cache[key]
        
        # Invalidate user data cache
        keys_to_remove = []
        for key in self._user_data_cache:
            if key.startswith(f"{actual_row}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._user_data_cache[key]
        
        # Invalidate sort cache if exists
        if hasattr(self, '_sort_cache'):
            keys_to_remove = []
            for key in self._sort_cache:
                if key.startswith(f"{actual_row}_"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._sort_cache[key]

    def batch_update_rows(self, updates: Dict[int, Dict[str, Any]]) -> bool:
        """
        Update multiple rows efficiently in one operation
        
        Args:
            updates: Dictionary mapping visible_row -> new_data
        
        Returns:
            bool: True if all updates successful, False otherwise
        """
        if not updates:
            return True
        
        # Group updates by actual row indices
        actual_updates = {}
        for visible_row, row_data in updates.items():
            if 0 <= visible_row < len(self._visible_rows):
                actual_row = self._visible_rows[visible_row]
                actual_updates[actual_row] = row_data
        
        if not actual_updates:
            return False
        
        try:
            # Apply updates
            for actual_row, row_data in actual_updates.items():
                if 0 <= actual_row < len(self._raw_data):
                    new_tuple = self._dict_to_tuple(row_data)
                    self._raw_data[actual_row] = new_tuple
            
            # Invalidate caches for all updated rows
            for actual_row in actual_updates.keys():
                self._invalidate_row_caches(actual_row)
            
            # Emit data changed signals
            self._emit_batch_update_signals(updates.keys())
            
            return True
            
        except Exception as e:
            print(f"Error in batch update: {e}")
            return False

    def _emit_batch_update_signals(self, updated_visible_rows):
        """
        Emit dataChanged signals for batch updates
        
        Args:
            updated_visible_rows: List of visible row indices that were updated
        """
        if not updated_visible_rows:
            return
        
        # Group consecutive rows to minimize signals
        sorted_rows = sorted(updated_visible_rows)
        current_range = None
        
        for row in sorted_rows:
            if current_range is None:
                current_range = [row, row]
            elif row == current_range[1] + 1:
                # Consecutive row, extend range
                current_range[1] = row
            else:
                # Non-consecutive, emit signal for previous range
                top_left = self.createIndex(current_range[0], 0)
                bottom_right = self.createIndex(current_range[1], self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right, [])
                current_range = [row, row]
        
        # Emit signal for last range
        if current_range:
            top_left = self.createIndex(current_range[0], 0)
            bottom_right = self.createIndex(current_range[1], self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [])

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Set data at the given index - required for editable cells
        
        Args:
            index: Model index to update
            value: New value
            role: Data role (EditRole for editing)
        
        Returns:
            bool: True if successful
        """
        if not index.isValid():
            return False
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._visible_rows) or col < 0 or col >= len(self.COLUMNS):
            return False
        
        # Get actual row index
        actual_row = self._visible_rows[row]
        
        # Convert current row to dict
        current_data = self._tuple_to_dict(self._raw_data[actual_row])
        
        # Update the specific field
        column_name = self.COLUMNS[col]['name']
        current_data[column_name] = value
        
        # Convert back to tuple
        new_tuple = self._dict_to_tuple(current_data)
        self._raw_data[actual_row] = new_tuple
        
        # Invalidate caches
        self._invalidate_row_caches(actual_row)
        
        # Emit data changed signal
        self.dataChanged.emit(index, index, [role])
        
        return True

    def get_all_tags(self) -> Dict[str, int]:
        """
        Get all tags and their frequencies from visible rows
        
        Returns:
            Dict[str, int]: Tag -> frequency count
        """
        tag_frequency = {}
        
        for i in range(self.rowCount()):
            row_data = self.get_row_data(i)
            tag_text = row_data.get('tag', '')
            if tag_text:
                tags = [tag.strip() for tag in tag_text.split(',') if tag.strip()]
                for tag in tags:
                    tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
        
        return tag_frequency

    def get_status_counts(self) -> Dict[str, int]:
        """
        Get counts for each read status from visible rows
        
        Returns:
            Dict[str, int]: Status -> count
        """
        counts = {
            "all": self.get_total_rows(),
            "unread": 0,
            "reading": 0,
            "completed": 0
        }
        
        for i in range(self.rowCount()):
            row_data = self.get_row_data(i)
            status = row_data.get('read_status', '').lower()
            if status in counts:
                counts[status] += 1
        
        return counts

    def search_rows(self, search_options: Dict[str, Any]) -> List[int]:
        """
        Search for rows matching given criteria
        
        Args:
            search_options: Dictionary with search parameters
        
        Returns:
            List[int]: List of visible row indices that match the search
        """
        if not search_options or 'condition1' not in search_options:
            return []
        
        # Validate search options
        if not self._validate_search_options(search_options):
            return []
        
        condition1 = search_options['condition1']
        condition2 = search_options.get('condition2')
        logic = search_options.get('logic', 'AND').upper()
        case_sensitive = search_options.get('case_sensitive', False)
        use_regex = search_options.get('use_regex', False)
        
        matching_rows = []
        
        # Search through currently visible rows only
        for visible_row, actual_row in enumerate(self._visible_rows):
            if actual_row >= len(self._raw_data):
                continue
                
            row_data = self._raw_data[actual_row]
            
            # Check conditions
            matches_cond1 = self._check_row_condition(row_data, condition1, case_sensitive, use_regex)
            
            if condition2:
                matches_cond2 = self._check_row_condition(row_data, condition2, case_sensitive, use_regex)
                
                if logic == 'AND':
                    matches = matches_cond1 and matches_cond2
                else:  # 'OR'
                    matches = matches_cond1 or matches_cond2
            else:
                matches = matches_cond1
            
            if matches:
                matching_rows.append(visible_row)
        
        return matching_rows

    def _validate_search_options(self, search_options: Dict[str, Any]) -> bool:
        """
        Validate search options
        
        Args:
            search_options: Search options dictionary
        
        Returns:
            bool: True if valid
        """
        if not isinstance(search_options, dict):
            return False
        
        # Check condition1
        condition1 = search_options.get('condition1')
        if not condition1 or not isinstance(condition1, dict):
            return False
        
        column1 = condition1.get('column')
        text1 = condition1.get('text')
        
        if column1 not in self.COLUMN_INDEX or not isinstance(text1, str):
            return False
        
        # Check condition2 if present
        condition2 = search_options.get('condition2')
        if condition2:
            if not isinstance(condition2, dict):
                return False
            
            column2 = condition2.get('column')
            text2 = condition2.get('text')
            
            if column2 not in self.COLUMN_INDEX or not isinstance(text2, str):
                return False
        
        # Check logic
        logic = search_options.get('logic', 'AND')
        if logic not in ['AND', 'OR']:
            return False
        
        return True

    def _validate_search_condition(self, condition: Dict[str, Any]) -> bool:
        """
        Validate a search condition
        
        Args:
            condition: Condition dictionary
        
        Returns:
            bool: True if condition is valid
        """
        if not isinstance(condition, dict):
            return False
        
        column = condition.get('column')
        text = condition.get('text')
        
        if not column or not isinstance(text, str):
            return False
        
        # Check if column exists
        if column not in self.COLUMN_INDEX:
            return False
        
        return True

    def _check_row_condition(self, row_data: tuple, condition: Dict[str, Any], 
                            case_sensitive: bool, use_regex: bool) -> bool:
        """
        Check if a row matches a search condition
        
        Args:
            row_data: Row data as tuple
            condition: Condition dictionary
            case_sensitive: Whether to consider case
            use_regex: Whether to use regex matching
        
        Returns:
            bool: True if row matches condition
        """
        column_name = condition['column']
        search_text = condition['text']
        
        # Get column index
        col_index = self.COLUMN_INDEX.get(column_name)
        if col_index is None or col_index >= len(row_data):
            return False
        
        # Get cell value
        cell_value = str(row_data[col_index])
        
        if not case_sensitive:
            cell_value = cell_value.lower()
            search_text = search_text.lower()
        
        if use_regex:
            try:
                import re
                pattern = re.compile(search_text, 0 if case_sensitive else re.IGNORECASE)
                return pattern.search(cell_value) is not None
            except re.error:
                # Invalid regex, fall back to substring search
                return search_text in cell_value
        else:
            return search_text in cell_value

    def apply_text_filter(self, search_options: Dict[str, Any]) -> None:
        """
        Apply text-based filter to show only matching rows
        
        Args:
            search_options: Search options dictionary
        """
        # Store filter options for later use
        self._text_filter_options = search_options.copy() if search_options else {}
        self._text_filter_active = bool(search_options)
        
        # Rebuild visible rows
        self._rebuild_visible_rows()
        
        print(f"Applied text filter: {self._text_filter_active}")

    def clear_text_filter(self) -> None:
        """
        Clear text-based filter
        """
        if hasattr(self, '_text_filter_options'):
            self._text_filter_options = {}
        self._text_filter_active = False
        self._rebuild_visible_rows()
        
        print("Cleared text filter")

    def set_row_background(self, visible_row: int, color: Union[str, QColor]) -> bool:
        """
        Set background color for a specific row
        
        Args:
            visible_row: Visible row index
            color: Color as string ('#RRGGBB') or QColor
        
        Returns:
            bool: True if successful
        """
        if visible_row < 0 or visible_row >= len(self._visible_rows):
            return False
        
        actual_row = self._visible_rows[visible_row]
        
        # Initialize styling cache if needed
        if not hasattr(self, '_row_styles'):
            self._row_styles = {}
        
        # Convert string color to QColor if needed
        if isinstance(color, str):
            from PyQt6.QtGui import QColor
            color = QColor(color)
        
        # Store style
        if actual_row not in self._row_styles:
            self._row_styles[actual_row] = {}
        
        self._row_styles[actual_row]['background'] = color
        
        # Emit data changed signal for the entire row
        top_left = self.createIndex(visible_row, 0)
        bottom_right = self.createIndex(visible_row, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.BackgroundRole])
        
        return True

    def set_row_foreground(self, visible_row: int, color: Union[str, QColor]) -> bool:
        """
        Set foreground (text) color for a specific row
        
        Args:
            visible_row: Visible row index
            color: Color as string ('#RRGGBB') or QColor
        
        Returns:
            bool: True if successful
        """
        if visible_row < 0 or visible_row >= len(self._visible_rows):
            return False
        
        actual_row = self._visible_rows[visible_row]
        
        # Initialize styling cache if needed
        if not hasattr(self, '_row_styles'):
            self._row_styles = {}
        
        # Convert string color to QColor if needed
        if isinstance(color, str):
            from PyQt6.QtGui import QColor
            color = QColor(color)
        
        # Store style
        if actual_row not in self._row_styles:
            self._row_styles[actual_row] = {}
        
        self._row_styles[actual_row]['foreground'] = color
        
        # Emit data changed signal for the entire row
        top_left = self.createIndex(visible_row, 0)
        bottom_right = self.createIndex(visible_row, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.ForegroundRole])
        
        return True

    def clear_row_styles(self, visible_row: Optional[int] = None):
        """
        Clear styling for a specific row or all rows
        
        Args:
            visible_row: Optional visible row index. If None, clear all styles.
        """
        if not hasattr(self, '_row_styles') or not self._row_styles:
            return
        
        if visible_row is None:
            # Clear all styles
            rows_to_clear = list(self._row_styles.keys())
            self._row_styles.clear()
        else:
            if visible_row < 0 or visible_row >= len(self._visible_rows):
                return
            
            actual_row = self._visible_rows[visible_row]
            if actual_row in self._row_styles:
                del self._row_styles[actual_row]
                rows_to_clear = [actual_row]
            else:
                return
        
        # Emit data changed signals
        for actual_row in rows_to_clear:
            # Find visible row index
            try:
                visible_row = self._visible_rows.index(actual_row)
                top_left = self.createIndex(visible_row, 0)
                bottom_right = self.createIndex(visible_row, self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right, 
                                    [Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole])
            except ValueError:
                # Row not in visible rows (filtered out)
                pass

    def apply_advanced_filter(self, filter_func: callable) -> None:
        """
        Apply custom filter function
        
        Args:
            filter_func: Function that takes (row_data: dict, row_index: int) 
                        and returns bool (True to keep row)
        """
        self._custom_filter = filter_func
        self._custom_filter_active = True
        self._rebuild_visible_rows()

    def clear_advanced_filter(self) -> None:
        """Clear custom filter"""
        self._custom_filter = None
        self._custom_filter_active = False
        self._rebuild_visible_rows()

    def filter_by_range(self, column: str, min_value=None, max_value=None) -> None:
        """
        Filter rows by value range
        
        Args:
            column: Column name to filter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
        """
        if column not in self.COLUMN_INDEX:
            return
        
        def range_filter(row_data, row_index):
            col_index = self.COLUMN_INDEX[column]
            if col_index >= len(row_data):
                return False
            
            value = row_data[col_index]
            
            # Try to convert to number for numeric comparison
            try:
                if isinstance(value, str):
                    num_value = float(value) if '.' in value else int(value)
                else:
                    num_value = float(value)
                
                if min_value is not None and num_value < min_value:
                    return False
                if max_value is not None and num_value > max_value:
                    return False
                
                return True
            except (ValueError, TypeError):
                # For non-numeric values, use string comparison
                str_value = str(value)
                str_min = str(min_value) if min_value is not None else None
                str_max = str(max_value) if max_value is not None else None
                
                if str_min is not None and str_value < str_min:
                    return False
                if str_max is not None and str_value > str_max:
                    return False
                
                return True
        
        self.apply_advanced_filter(range_filter)

    def get_filter_state(self) -> Dict[str, Any]:
        """
        Get current filter state
        
        Returns:
            dict: Information about active filters
        """
        return {
            'has_status_filter': 'status' in self._filters,
            'has_tag_filter': 'tags' in self._filters,
            'has_text_filter': self._text_filter_active,
            'has_custom_filter': self._custom_filter_active,
            'visible_rows': len(self._visible_rows),
            'total_rows': len(self._raw_data)
        }

    def export_visible_data(self) -> List[Dict[str, Any]]:
        """
        Export all visible data as list of dictionaries
        
        Returns:
            List[Dict]: Visible rows as dictionaries
        """
        result = []
        for visible_row in range(self.rowCount()):
            row_data = self.get_row_data(visible_row)
            result.append(row_data)
        return result

    def find_duplicates(self, column: str) -> Dict[str, List[int]]:
        """
        Find duplicate values in a column
        
        Args:
            column: Column name to check for duplicates
        
        Returns:
            dict: value -> list of visible row indices with that value
        """
        if column not in self.COLUMN_INDEX:
            return {}
        
        col_index = self.COLUMN_INDEX[column]
        value_map = {}
        
        for visible_row in range(self.rowCount()):
            actual_row = self._visible_rows[visible_row]
            if actual_row < len(self._raw_data):
                value = self._raw_data[actual_row][col_index]
                if value not in value_map:
                    value_map[value] = []
                value_map[value].append(visible_row)
        
        # Filter to only duplicates (more than one occurrence)
        duplicates = {k: v for k, v in value_map.items() if len(v) > 1}
        return duplicates

    def validate_integrity(self) -> Dict[str, Any]:
        """
        Validate model integrity
        
        Returns:
            dict: Validation results
        """
        results = {
            'valid': True,
            'issues': [],
            'statistics': {}
        }
        
        # Check raw data consistency
        results['statistics']['total_rows'] = len(self._raw_data)
        results['statistics']['visible_rows'] = len(self._visible_rows)
        
        # Validate visible rows indices
        for i, actual_row in enumerate(self._visible_rows):
            if actual_row < 0 or actual_row >= len(self._raw_data):
                results['valid'] = False
                results['issues'].append(f"Visible row {i} references invalid raw row {actual_row}")
        
        # Check filter state consistency
        if self._filter_active and len(self._visible_rows) == len(self._raw_data):
            results['issues'].append("Filter active but all rows visible")
        
        # Check cache consistency
        results['statistics']['display_cache_size'] = len(self._display_cache)
        results['statistics']['user_cache_size'] = len(self._user_data_cache)
        
        return results

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about model state
        
        Returns:
            dict: Debug information
        """
        info = {
            'data': {
                'total_rows': len(self._raw_data),
                'visible_rows': len(self._visible_rows),
                'filtered_out': len(self._raw_data) - len(self._visible_rows)
            },
            'filters': {
                'active': self._filter_active,
                'status_filter': 'status' in self._filters,
                'tag_filter': 'tags' in self._filters,
                'text_filter': self._text_filter_active,
                'custom_filter': self._custom_filter_active
            },
            'performance': self.get_performance_stats(),
            'cache': {
                'display_cache': len(self._display_cache),
                'user_cache': len(self._user_data_cache),
                'row_styles': len(self._row_styles) if hasattr(self, '_row_styles') else 0
            }
        }
        
        return info