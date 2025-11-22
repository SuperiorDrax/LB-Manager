from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from models.data_parser import DataParser
import pandas as pd
import json

class FileIO:
    def __init__(self, main_window):
        self.main_window = main_window
    
    def import_from_file(self):
        """Enhanced import method with XLSX support"""
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self.main_window, 
            "Import File", 
            "", 
            "All Supported Files (*.txt *.xlsx *.json);;"
            "Text Files (*.txt);;"
            "Excel Files (*.xlsx);;"
            "JSON Files (*.json);;"
            "All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.xlsx'):
                    self.import_from_xlsx(file_path)
                elif file_path.endswith('.json'):
                    self.import_from_json(file_path)
                else:
                    # Default to TXT format
                    self.import_from_txt(file_path)
                    
            except Exception as e:
                QMessageBox.critical(self.main_window, "Import Error", f"Cannot open file: {str(e)}")

    def import_from_json(self, file_path):
        """Import data from JSON file with tag support"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate JSON structure
            if not isinstance(data, dict) or 'data' not in data:
                QMessageBox.critical(self.main_window, "Import Error", 
                                   "Invalid JSON format: missing 'data' field")
                return
            
            # Check version compatibility
            version = data.get('version', 1)
            if version != 1:
                QMessageBox.warning(self.main_window, "Import Warning", 
                                  f"JSON file version {version} may not be fully compatible")
            
            success_count = 0
            error_rows = []
            
            for index, row_data in enumerate(data['data']):
                try:
                    # Extract fields with fallbacks
                    websign = str(row_data.get('websign', ''))
                    author = str(row_data.get('author', ''))
                    title = str(row_data.get('title', ''))
                    group = str(row_data.get('group', ''))
                    show = str(row_data.get('show', ''))
                    magazine = str(row_data.get('magazine', ''))
                    origin = str(row_data.get('origin', ''))
                    tag = str(row_data.get('tag', ''))
                    read_status = row_data.get('read_status', 'unread')
                    progress = row_data.get('progress', 0)
                    
                    # Validate required fields
                    if not websign or not author or not title:
                        error_rows.append((index + 1, f"Missing required fields: websign='{websign}', author='{author}', title='{title}'"))
                        continue
                    
                    # Add to table with tag
                    self.main_window.table_controller.add_to_table((author, title, group, show, magazine, origin, websign, tag, read_status, progress))
                    success_count += 1
                    
                except Exception as e:
                    error_rows.append((index + 1, str(e)))
            
            # Show import summary
            if error_rows:
                error_msg = f"Successfully imported: {success_count} rows\n\nErrors found in {len(error_rows)} rows:\n"
                for row_num, error in error_rows[:10]:
                    error_msg += f"Row {row_num}: {error}\n"
                
                if len(error_rows) > 10:
                    error_msg += f"... and {len(error_rows) - 10} more errors"
                
                QMessageBox.warning(self.main_window, "Import Summary", error_msg)
            else:
                QMessageBox.information(self.main_window, "Import", 
                                      f"Successfully imported {success_count} rows from JSON file.")
                
        except json.JSONDecodeError as e:
            QMessageBox.critical(self.main_window, "Import Error", f"Invalid JSON file: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Import Error", f"Cannot import JSON file: {str(e)}")

    def import_from_xlsx(self, file_path):
        """Import data from XLSX file with tag support"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name='Data')
            
            # Validate required columns
            required_columns = ['websign', 'author', 'title']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                QMessageBox.critical(self.main_window, "Import Error", 
                                   f"Missing required columns in XLSX file: {', '.join(missing_columns)}")
                return
            
            success_count = 0
            error_rows = []
            
            for index, row in df.iterrows():
                try:
                    # Convert row to tuple format expected by table controller
                    # Order: author, title, group, show, magazine, origin, websign, tag, read_status, progress
                    websign = str(row['websign']) if pd.notna(row['websign']) else ""
                    author = str(row['author']) if pd.notna(row['author']) else ""
                    title = str(row['title']) if pd.notna(row['title']) else ""
                    group = str(row['group']) if 'group' in df.columns and pd.notna(row['group']) else ""
                    show = str(row['show']) if 'show' in df.columns and pd.notna(row['show']) else ""
                    magazine = str(row['magazine']) if 'magazine' in df.columns and pd.notna(row['magazine']) else ""
                    origin = str(row['origin']) if 'origin' in df.columns and pd.notna(row['origin']) else ""
                    tag = str(row['tag']) if 'tag' in df.columns and pd.notna(row['tag']) else ""
                    read_status = str(row['read_status']) if 'read_status' in df.columns and pd.notna(row['read_status']) else "unread"
                    progress = int(row['progress']) if 'progress' in df.columns and pd.notna(row['progress']) else 0
                    
                    # Validate required fields
                    if not websign or not author or not title:
                        error_rows.append((index + 2, f"Missing required fields: websign='{websign}', author='{author}', title='{title}'"))
                        continue
                    
                    # Add to table with tag
                    self.main_window.table_controller.add_to_table((author, title, group, show, magazine, origin, websign, tag, read_status, progress))
                    success_count += 1
                    
                except Exception as e:
                    error_rows.append((index + 2, str(e)))
            
            # Show import summary
            if error_rows:
                error_msg = f"Successfully imported: {success_count} rows\n\nErrors found in {len(error_rows)} rows:\n"
                for row_num, error in error_rows[:10]:
                    error_msg += f"Row {row_num}: {error}\n"
                
                if len(error_rows) > 10:
                    error_msg += f"... and {len(error_rows) - 10} more errors"
                
                QMessageBox.warning(self.main_window, "Import Summary", error_msg)
            else:
                QMessageBox.information(self.main_window, "Import", 
                                      f"Successfully imported {success_count} rows from XLSX file.")
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Import Error", f"Cannot import XLSX file: {str(e)}")

    def import_from_txt(self, file_path):
        """Import data from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            success_count = 0
            error_lines = []
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line:
                    try:
                        parsed_data = DataParser.parse_text(line)
                        if parsed_data is None:
                            error_lines.append((i, line, "Missing required fields (websign, author, title) or format incorrect"))
                        else:
                            self.main_window.table_controller.add_to_table(parsed_data)
                            success_count += 1
                    except Exception as e:
                        error_lines.append((i, line, str(e)))
            
            # Show summary
            if error_lines:
                error_msg = f"Successfully imported: {success_count} lines\n\nErrors found in {len(error_lines)} lines:\n"
                for line_num, line_content, error in error_lines[:10]:
                    error_msg += f"Line {line_num}: {line_content}\nError: {error}\n\n"
                
                if len(error_lines) > 10:
                    error_msg += f"... and {len(error_lines) - 10} more errors"
                
                QMessageBox.warning(self.main_window, "Import Summary", error_msg)
            else:
                QMessageBox.information(self.main_window, "Import", f"Successfully imported {success_count} lines from TXT file.")
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Import Error", f"Cannot open TXT file: {str(e)}")

    def save_to_file(self):
        """Unified save method with format selection"""
        if self.main_window.table.rowCount() == 0:
            QMessageBox.warning(self.main_window, "Save", "No data to save.")
            return
        
        # Check for duplicates before saving
        duplicates = self.check_duplicates_before_save()
        if duplicates and not self.confirm_save_with_duplicates(duplicates):
            return  # User canceled save
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self.main_window,
            "Save File",
            "",
            "All Supported Files (*.txt *.xlsx *.json);;"
            "Text Files (*.txt);;"
            "Excel Files (*.xlsx);;"
            "JSON Files (*.json);;"
            "All Files (*)"
        )
        
        if file_path:
            if file_path.endswith('.txt'):
                # Show warning for TXT format
                reply = QMessageBox.warning(
                    self.main_window,
                    "Tag Data Warning",
                    "Saving as TXT format will lose tag information.\n\n"
                    "Do you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if not file_path.endswith('.txt'):
                        file_path += '.txt'
                    self.save_to_file_txt(file_path)
            elif file_path.endswith('.xlsx'):
                self.save_to_xlsx(file_path)
            elif file_path.endswith('.json'):
                self.save_to_json(file_path)
            else:
                # Default to TXT with warning
                reply = QMessageBox.warning(
                    self.main_window,
                    "Tag Data Warning",
                    "Saving as TXT format will lose tag information.\n\n"
                    "Do you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if not file_path.endswith('.txt'):
                        file_path += '.txt'
                    self.save_to_file_txt(file_path)

    def save_to_json(self, file_path):
        """Save data to JSON format with tag column"""
        try:
            # Prepare data structure
            data = {
                "version": 1,
                "format": "data_table",
                "columns": ['websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag', 'read_status', 'progress'],
                "data": []
            }
            
            for row in range(self.main_window.table.rowCount()):
                row_data = {}
                for col, col_name in enumerate(data["columns"]):
                    item = self.main_window.table.item(row, col)
                    if item:
                        # Handle websign special case
                        if col == 0:  # websign column
                            websign_value = item.data(Qt.ItemDataRole.UserRole)
                            if not websign_value:
                                websign_value = item.text()
                            row_data[col_name] = websign_value
                        elif col == 9:  # progress column
                            progress_value = item.data(Qt.ItemDataRole.UserRole)
                            if progress_value is None:
                                progress_value = 0
                            row_data[col_name] = progress_value
                        else:
                            row_data[col_name] = item.text()
                    else:
                        row_data[col_name] = ""
                data["data"].append(row_data)
            
            # Save to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self.main_window, "Save", 
                                  f"Data saved in JSON format successfully.\n"
                                  f"Rows: {self.main_window.table.rowCount()}")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Save Error", f"Cannot save JSON file: {str(e)}")

    def save_to_xlsx(self, file_path):
        """Save data to XLSX format with tag column"""
        try:
            # Prepare data for DataFrame
            data = []
            column_headers = ['websign', 'author', 'title', 'group', 'show', 'magazine', 'origin', 'tag', 'read_status', 'progress']
            
            for row in range(self.main_window.table.rowCount()):
                row_data = []
                for col in range(8):
                    item = self.main_window.table.item(row, col)
                    if item:
                        # Handle websign special case
                        if col == 0:  # websign column
                            websign_value = item.data(Qt.ItemDataRole.UserRole)
                            if not websign_value:
                                websign_value = item.text()
                            row_data.append(websign_value)
                        elif col == 9:  # progress column
                            progress_value = item.data(Qt.ItemDataRole.UserRole)
                            if progress_value is None:
                                progress_value = 0
                            row_data.append(progress_value)
                        else:
                            row_data.append(item.text())
                    else:
                        row_data.append("")
                data.append(row_data)
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=column_headers)
            
            # Save to Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            QMessageBox.information(self.main_window, "Save", 
                                  f"Data saved in XLSX format successfully.\n"
                                  f"Rows: {self.main_window.table.rowCount()}")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Save Error", f"Cannot save XLSX file: {str(e)}")

    def save_to_file_txt(self, file_path):
        """Save data in TXT format (tag data will be lost)"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                for row in range(self.main_window.table.rowCount()):
                    # Get data - tag column (index 7) is ignored
                    websign_item = self.main_window.table.item(row, 0)
                    if websign_item:
                        websign = websign_item.data(Qt.ItemDataRole.UserRole)
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
                    
                    # Reconstruct the original format (tag is not included)
                    parts = []
                    
                    # Add websign at the beginning
                    if websign:
                        parts.append(websign)

                    # Add show info
                    if show:
                        parts.append(f"({show})")

                    # Build author part
                    author_part = ""
                    if group and author:
                        author_part = f"{group} ({author})"
                    elif author:
                        author_part = author

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

                    file.write(" ".join(parts) + "\n")
            
            QMessageBox.information(self.main_window, "Save", 
                                  f"Data saved in TXT format successfully.\n"
                                  f"Rows: {self.main_window.table.rowCount()}\n"
                                  f"Note: Tag information was not saved in TXT format.")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Save Error", f"Cannot save file: {str(e)}")

    def check_duplicates_before_save(self):
        """Check for duplicate websign values before saving"""
        websign_map = {}
        duplicates = []
        
        for row in range(self.main_window.table.rowCount()):
            websign_item = self.main_window.table.item(row, 0)
            if websign_item and websign_item.text():
                websign = websign_item.text()
                if websign not in websign_map:
                    websign_map[websign] = []
                websign_map[websign].append(row + 1)  # Store 1-based row numbers for user display
        
        # Find duplicates (websign with more than one row)
        for websign, rows in websign_map.items():
            if len(rows) > 1:
                duplicates.append({
                    'websign': websign,
                    'rows': rows,
                    'count': len(rows)
                })
        
        return duplicates

    def confirm_save_with_duplicates(self, duplicates):
        """Ask user confirmation to save with duplicates"""
        total_duplicates = sum(dup['count'] - 1 for dup in duplicates)  # Total duplicate entries
        unique_duplicates = len(duplicates)  # Number of unique websigns with duplicates
        
        # Build detailed message
        message = f"Found {unique_duplicates} duplicate websign values affecting {total_duplicates} entries.\n\n"
        message += "Duplicate details:\n"
        
        # Show first few duplicates for context
        for i, dup in enumerate(duplicates[:5]):  # Show first 5 duplicates
            message += f"• Websign '{dup['websign']}': rows {', '.join(map(str, dup['rows']))}\n"
        
        if len(duplicates) > 5:
            message += f"• ... and {len(duplicates) - 5} more duplicates\n"
        
        message += "\nDo you want to save anyway?"
        
        reply = QMessageBox.question(
            self.main_window,
            "Duplicate Values Found",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes