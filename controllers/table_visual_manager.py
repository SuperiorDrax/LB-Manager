from PyQt6.QtWidgets import QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QTimer

class TableVisualManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def toggle_column_visibility(self, column_index, is_visible):
        """Toggle visibility of a specific column"""
        self.main_window.table.setColumnHidden(column_index, not is_visible)
        self.main_window.state_manager.save_column_config()
    
    def show_header_context_menu(self, position):
        """Show right-click menu for column headers"""
        # Create context menu
        context_menu = QMenu(self.main_window)
        
        # Add column visibility controls
        column_names = [
            'websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag', 'read_status', 'progress', 'file_path'
        ]
        
        # Add visibility toggle actions for all columns
        for i, column_name in enumerate(column_names):
            if i < self.main_window.table.columnCount():
                action = context_menu.addAction(column_name)
                action.setCheckable(True)
                # file_path column (index 10) is unchecked by default
                is_visible = not self.main_window.table.isColumnHidden(i)
                action.setChecked(is_visible)
                action.triggered.connect(lambda checked, idx=i: self.toggle_column_visibility(idx, checked))
        
        # Show menu at cursor position
        context_menu.exec(self.main_window.table.horizontalHeader().mapToGlobal(position))
    
    def delete_rows(self, rows):
        """Delete specified rows with confirmation"""
        if not rows:
            return
        
        # Sort rows in descending order for safe deletion
        rows.sort(reverse=True)
        
        if len(rows) == 1:
            message = f"Are you sure you want to delete row {rows[0] + 1}?"
        else:
            message = f"Are you sure you want to delete {len(rows)} selected rows?"
        
        reply = QMessageBox.question(
            self.main_window,
            "Confirm Deletion",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            model = self.main_window.table.get_model()
            
            # Store websigns of deleted rows for incremental cleanup
            deleted_websigns = set()
            for row in rows:
                row_data = model.get_row_data(row)
                if row_data:
                    websign = row_data.get('websign', '')
                    if websign:
                        deleted_websigns.add(websign)
            
            # Delete rows
            for row in rows:
                if model.remove_row(row):
                    deleted_count += 1
            
            if deleted_count > 0:
                # Let TableController handle websign tracker cleanup via scheduled rebuild
                if hasattr(self.main_window, 'table_controller'):
                    self.main_window.table_controller._schedule_rebuild()
                
                # Refresh the view
                self.main_window.table.viewport().update()
                
                # Update sidebar counts
                QTimer.singleShot(150, self.main_window.update_sidebar_counts)

                # Optional: Provide immediate visual feedback by refreshing the view
                self.main_window.table.viewport().update()
            
            QMessageBox.information(self.main_window, "Deletion Complete", 
                                f"Successfully deleted {deleted_count} row(s).")
    
    def copy_row_to_clipboard(self, row, return_text=False):
        """Copy specified row data as formatted text to clipboard"""
        try:
            # Get row data - note new column order
            websign = self.main_window.get_cell_text(row, 0)  # Fixed: Use get_cell_text
            
            author = self.main_window.get_cell_text(row, 1)
            title = self.main_window.get_cell_text(row, 2)
            group = self.main_window.get_cell_text(row, 3)
            show = self.main_window.get_cell_text(row, 4)
            magazine = self.main_window.get_cell_text(row, 5)
            origin = self.main_window.get_cell_text(row, 6)
            
            # Reconstruct the original format (format remains the same)
            parts = []
            
            # Add websign at the beginning
            if websign:
                parts.append(websign)

            # Add show info (after websign, before author)
            if show:
                parts.append(f"({show})")

            # Build author part
            author_part = ""
            if author:
                author_part += author
            if group:
                author_part += f"({group})"

            if author_part:
                parts.append(f"[{author_part}]")

            # Add title
            if title:
                parts.append(title)

            # Add origin/magazine
            if magazine:
                parts.append(f"({magazine})")
            elif origin:
                parts.append(f"({origin})")

            # Combine into complete text
            result_text = " ".join(parts)
            
            if return_text:
                return result_text  # Return text instead of copying
            else:
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText(result_text)
                QMessageBox.information(self.main_window, "Copy Success", 
                                    "Row data copied to clipboard!")
                return result_text
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Copy Error", 
                            f"Failed to copy data: {str(e)}")
            return ""

    def copy_rows_to_clipboard(self, rows):
        """Copy multiple rows to clipboard"""
        if not rows:
            return
        
        # Sort rows to maintain order
        rows.sort()
        
        clipboard_text = ""
        for row in rows:
            # Get row text (don't copy individually)
            row_text = self.copy_row_to_clipboard(row, return_text=True)
            if row_text:
                clipboard_text += row_text + "\n"
        
        # Copy all rows at once
        if clipboard_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text.strip())
            
            QMessageBox.information(self.main_window, "Copy", 
                                f"Copied {len(rows)} rows to clipboard")