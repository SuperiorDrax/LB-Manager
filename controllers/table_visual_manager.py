from PyQt6.QtWidgets import QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

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
        column_names = ['websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag']
        
        for i, name in enumerate(column_names):
            action = QAction(name, self.main_window)
            action.setCheckable(True)
            action.setChecked(not self.main_window.table.isColumnHidden(i))
            action.setData(i)  # Store column index
            action.triggered.connect(lambda checked, idx=i: self.toggle_column_visibility(idx, checked))
            context_menu.addAction(action)
        
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
            for row in rows:
                self.main_window.table.removeRow(row)
                # Update websign tracker if duplicate detection is enabled
                if hasattr(self.main_window.table_controller, 'websign_tracker'):
                    self.main_window.table_controller.on_row_removed(row)
            
            # Re-apply duplicate highlighting after all deletions
            if hasattr(self.main_window.table_controller, 'websign_tracker'):
                self.main_window.table_controller.reapply_duplicate_highlighting()
            
            QMessageBox.information(self.main_window, "Deletion Complete", 
                                f"Successfully deleted {len(rows)} row(s).")
    
    def copy_row_to_clipboard(self, row):
        """Copy specified row data as formatted text to clipboard"""
        try:
        # Get row data - note new column order
            websign_item = self.main_window.table.item(row, 0)
            if websign_item:
                # Handle custom websign item that might have numeric data
                websign = websign_item.data(Qt.ItemDataRole.UserRole)  # Get original string
                if not websign:
                    websign = websign_item.text()
            else:
                websign = ""
                
            author = self.main_window.table.item(row, 1).text() if self.main_window.table.item(row, 1) else ""
            title = self.main_window.table.item(row, 2).text() if self.main_window.table.item(row, 2) else ""
            group = self.main_window.table.item(row, 3).text() if self.main_window.table.item(row, 3) else ""
            show = self.main_window.table.item(row, 4).text() if self.main_window.table.item(row, 4) else ""
            magazine = self.main_window.table.item(row, 5).text() if self.main_window.table.item(row, 5) else ""
            origin = self.main_window.table.item(row, 6).text() if self.main_window.table.item(row, 6) else ""
            
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
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(result_text)
            
            # Show success message
            QMessageBox.information(self.main_window, "Copy Success", "Row data copied to clipboard!")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Copy Error", f"Failed to copy data: {str(e)}")