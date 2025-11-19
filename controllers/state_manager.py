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
        
        # Save table geometry
        table_geometry = []
        for i in range(self.main_window.table.columnCount()):
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
        for i in range(self.main_window.table.columnCount()):
            table_geometry.append(str(self.main_window.table.columnWidth(i)))
        
        self.config_manager.set_window_state(
            window_state['geometry'],
            window_state['maximized'],
            ','.join(table_geometry)
        )

    def restore_table_geometry(self):
        """Restore table column widths"""
        window_state = self.config_manager.get_window_state()
        if window_state['table_geometry']:
            try:
                widths = list(map(int, window_state['table_geometry'].split(',')))
                if len(widths) == 7:
                    for i, width in enumerate(widths):
                        if width >= 20:  # Reasonable minimum width
                            self.main_window.table.setColumnWidth(i, width)
            except ValueError:
                pass  # Use default column widths
    
    def save_column_config(self):
        """Save column visibility and order configuration"""
        # Get current visibility
        visible = []
        for i in range(self.main_window.table.columnCount()):
            visible.append(not self.main_window.table.isColumnHidden(i))
        
        # Get current visual order
        order = []
        for i in range(self.main_window.table.columnCount()):
            order.append(self.main_window.table.horizontalHeader().visualIndex(i))
        
        self.config_manager.set_column_config(visible, order)

    def restore_table_state(self, window_state, column_config):
        """Restore table geometry and column configuration"""
        # Restore column widths
        if window_state['table_geometry']:
            try:
                widths = list(map(int, window_state['table_geometry'].split(',')))
                if len(widths) == 7:
                    for i, width in enumerate(widths):
                        if width >= 20:
                            self.main_window.table.setColumnWidth(i, width)
            except ValueError:
                pass
        
        # Restore column visibility and order
        if len(column_config['visible']) == 7 and len(column_config['order']) == 7:
            # Apply column visibility
            for i, visible in enumerate(column_config['visible']):
                self.main_window.table.setColumnHidden(i, not visible)
            
            # Apply column order - need to reorder based on saved visual indices
            # Create a mapping from logical to visual index
            visual_to_logical = {}
            for logical_index in range(self.main_window.table.columnCount()):
                visual_index = column_config['order'][logical_index]
                visual_to_logical[visual_index] = logical_index
            
            # Move columns to their saved positions
            for visual_index in range(self.main_window.table.columnCount()):
                if visual_index in visual_to_logical:
                    logical_index = visual_to_logical[visual_index]
                    current_visual = self.main_window.table.horizontalHeader().visualIndex(logical_index)
                    if current_visual != visual_index:
                        self.main_window.table.horizontalHeader().moveSection(current_visual, visual_index)

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