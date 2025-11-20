from PyQt6.QtCore import QTimer

class StateManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        # Initialize timers for debounced saving
        self.save_table_timer = QTimer()
        self.save_table_timer.setSingleShot(True)
        self.save_table_timer.timeout.connect(self.save_table_geometry)
        
        self.save_column_timer = QTimer()
        self.save_column_timer.setSingleShot(True)
        self.save_column_timer.timeout.connect(self.save_column_config)
    
    def save_window_state(self):
        """Save current window and table state"""
        # Save window geometry (only if not maximized)
        if not self.main_window.isMaximized():
            geometry = self.main_window.geometry()
            geo_str = f"{geometry.x()},{geometry.y()},{geometry.width()},{geometry.height()}"
        else:
            # Keep last normal geometry when maximized
            window_state = self.config_manager.get_window_state()
            geo_str = window_state['geometry']
        
        # Save table geometry - dynamic column count
        table_geometry = []
        current_column_count = self.main_window.table.columnCount()
        for i in range(current_column_count):
            table_geometry.append(str(self.main_window.table.columnWidth(i)))
        
        self.config_manager.set_window_state(
            geo_str,
            self.main_window.isMaximized(),
            ','.join(table_geometry)
        )
    
    def restore_window_state(self):
        """Restore window and table geometry from config"""
        window_state = self.config_manager.get_window_state()
        
        # Check if this is first run (no saved geometry)
        is_first_run = not window_state['geometry']
        
        # Restore window geometry only if previously saved
        if window_state['geometry']:
            try:
                geometry = list(map(int, window_state['geometry'].split(',')))
                if len(geometry) == 4:
                    self.main_window.setGeometry(*geometry)
            except ValueError:
                pass  # Keep default larger size
        
        # Restore maximized state
        if window_state['maximized']:
            self.main_window.showMaximized()
        
        # Restore table column widths after UI initialization
        self.restore_table_geometry_timer = QTimer()
        self.restore_table_geometry_timer.setSingleShot(True)
        self.restore_table_geometry_timer.timeout.connect(self.restore_table_geometry)
        self.restore_table_geometry_timer.start(100)
    
    def save_table_geometry(self):
        """Save only table geometry (called on column resize)"""
        window_state = self.config_manager.get_window_state()
        table_geometry = []
        current_column_count = self.main_window.table.columnCount()
        for i in range(current_column_count):
            table_geometry.append(str(self.main_window.table.columnWidth(i)))
        
        self.config_manager.set_window_state(
            window_state['geometry'],
            window_state['maximized'],
            ','.join(table_geometry)
        )

    def restore_table_geometry(self):
        """Restore table column widths - dynamic column count"""
        window_state = self.config_manager.get_window_state()
        if window_state['table_geometry']:
            try:
                widths = list(map(int, window_state['table_geometry'].split(',')))
                current_column_count = self.main_window.table.columnCount()
                
                # Apply saved widths for available columns
                for i, width in enumerate(widths):
                    if i < current_column_count and width >= 20:  # Reasonable minimum width
                        self.main_window.table.setColumnWidth(i, width)
            except ValueError:
                pass  # Use default column widths
    
    def save_column_config(self):
        """Save column visibility and order configuration - dynamic column count"""
        # Get current visibility
        visible = []
        current_column_count = self.main_window.table.columnCount()
        for i in range(current_column_count):
            visible.append(not self.main_window.table.isColumnHidden(i))
        
        # Get current visual order
        order = []
        for i in range(current_column_count):
            order.append(self.main_window.table.horizontalHeader().visualIndex(i))
        
        self.config_manager.set_column_config(visible, order)

    def restore_table_state(self, window_state, column_config):
        """Restore table geometry and column configuration with dynamic column count support"""
        current_column_count = self.main_window.table.columnCount()
        
        # Restore column widths
        self.restore_column_widths(window_state, current_column_count)
        
        # Restore column visibility and order
        self.restore_column_visibility_and_order(column_config, current_column_count)

    def restore_column_widths(self, window_state, current_column_count):
        """Restore column widths from saved configuration"""
        if window_state and window_state.get('table_geometry'):
            try:
                widths = list(map(int, window_state['table_geometry'].split(',')))
                
                # Apply saved widths for available columns
                for i, width in enumerate(widths):
                    if i < current_column_count and width >= 20:  # Reasonable minimum width
                        self.main_window.table.setColumnWidth(i, width)
                        
                # Set default width for any new columns that weren't in saved config
                default_width = 100
                for i in range(len(widths), current_column_count):
                    self.main_window.table.setColumnWidth(i, default_width)
                    
            except (ValueError, AttributeError):
                # Use default column widths if saved config is invalid
                self.set_default_column_widths(current_column_count)

    def restore_column_visibility_and_order(self, column_config, current_column_count):
        """Restore column visibility and order from saved configuration"""
        if not column_config:
            # No saved configuration, set all columns visible in default order
            self.set_all_columns_visible(current_column_count)
            return
        
        saved_visible = column_config.get('visible', [])
        saved_order = column_config.get('order', [])
        
        # Restore column visibility
        self.restore_column_visibility(saved_visible, current_column_count)
        
        # Restore column order
        self.restore_column_order(saved_order, current_column_count)

    def restore_column_visibility(self, saved_visible, current_column_count):
        """Restore column visibility settings"""
        if saved_visible:
            # Apply saved visibility for available columns
            for i, visible in enumerate(saved_visible):
                if i < current_column_count:
                    self.main_window.table.setColumnHidden(i, not visible)
            
            # Set new columns (beyond saved config) to visible by default
            for i in range(len(saved_visible), current_column_count):
                self.main_window.table.setColumnHidden(i, False)
        else:
            # No saved visibility, set all columns visible
            self.set_all_columns_visible(current_column_count)

    def restore_column_order(self, saved_order, current_column_count):
        """Restore column order from saved configuration"""
        if saved_order and len(saved_order) >= current_column_count:
            try:
                # Create mapping from logical to visual index
                visual_to_logical = {}
                for logical_index in range(current_column_count):
                    if logical_index < len(saved_order):
                        visual_index = saved_order[logical_index]
                        if visual_index < current_column_count:
                            visual_to_logical[visual_index] = logical_index
                
                # Move columns to their saved positions
                for visual_index in range(current_column_count):
                    if visual_index in visual_to_logical:
                        logical_index = visual_to_logical[visual_index]
                        if logical_index < current_column_count:
                            current_visual = self.main_window.table.horizontalHeader().visualIndex(logical_index)
                            if current_visual != visual_index:
                                self.main_window.table.horizontalHeader().moveSection(current_visual, visual_index)
                                
            except (IndexError, ValueError):
                # If there's any error in restoring order, use default order
                self.reset_column_order(current_column_count)
        else:
            # Saved order doesn't match current column count, reset to default
            self.reset_column_order(current_column_count)

    def set_all_columns_visible(self, column_count):
        """Set all columns to visible"""
        for i in range(column_count):
            self.main_window.table.setColumnHidden(i, False)

    def set_default_column_widths(self, column_count):
        """Set default column widths"""
        default_widths = {
            0: 80,   # websign
            1: 120,  # author
            2: 200,  # title
            3: 100,  # group
            4: 100,  # show
            5: 120,  # magazine
            6: 120,  # origin
            7: 150   # tag
        }
        
        for i in range(column_count):
            width = default_widths.get(i, 100)  # Default to 100 for any additional columns
            self.main_window.table.setColumnWidth(i, width)

    def reset_column_order(self, column_count):
        """Reset column order to default logical order"""
        for logical_index in range(column_count):
            current_visual = self.main_window.table.horizontalHeader().visualIndex(logical_index)
            if current_visual != logical_index:
                self.main_window.table.horizontalHeader().moveSection(current_visual, logical_index)

    def on_column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        """Handle column reordering with debounced saving"""
        if hasattr(self, 'save_column_timer'):
            self.save_column_timer.start(500)
        else:
            self.save_column_timer = QTimer()
            self.save_column_timer.setSingleShot(True)
            self.save_column_timer.timeout.connect(self.save_column_config)
    
    def on_column_resized(self, logicalIndex, oldSize, newSize):
        """Handle column resize with debounced saving"""
        if hasattr(self, 'save_table_timer'):
            self.save_table_timer.start(500)  # Save after 500ms of no resizing
        else:
            self.save_table_timer = QTimer()
            self.save_table_timer.setSingleShot(True)
            self.save_table_timer.timeout.connect(self.save_table_geometry)