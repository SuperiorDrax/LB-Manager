import os
import logging
from typing import Optional

class FileLocator:
    """Utility class for locating ZIP files in directory trees"""
    def __init__(self, max_depth: int = 3):
        """Initialize FileLocator"""
        self.max_depth = max_depth
        self.logger = logging.getLogger(__name__)
    
    def find_zip_by_websign(self, websign: str, lib_path: str) -> Optional[str]:
        """Recursively search for {websign}.zip in directory tree"""
        # Validate inputs
        if not self._validate_inputs(websign, lib_path):
            return None
        
        zip_filename = f"{websign}.zip"
        self.logger.info(f"Searching for: {zip_filename} in {lib_path}")
        
        # Start recursive search
        found_path = self._search_directory(lib_path, zip_filename, current_depth=0)
        
        if found_path:
            self.logger.info(f"Found ZIP file: {found_path}")
        else:
            self.logger.warning(f"ZIP file not found: {zip_filename}")
            
        return found_path
    
    def _validate_inputs(self, websign: str, lib_path: str) -> bool:
        """Validate input parameters"""
        if not websign or not websign.strip():
            self.logger.error("Websign cannot be empty")
            return False
        
        if not websign.isdigit() or not (1 <= len(websign) <= 7):
            self.logger.error(f"Invalid websign format: {websign}")
            return False
        
        if not lib_path or not os.path.exists(lib_path):
            self.logger.error(f"Library path does not exist: {lib_path}")
            return False
        
        if not os.path.isdir(lib_path):
            self.logger.error(f"Library path is not a directory: {lib_path}")
            return False
        
        return True
    
    def _search_directory(self, directory: str, target_filename: str, current_depth: int) -> Optional[str]:
        """Recursively search directory for target file"""
        # Check depth limit
        if current_depth > self.max_depth:
            return None
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                # Check if it's the target file
                if os.path.isfile(item_path) and item.lower() == target_filename.lower():
                    return item_path
                
                # Recursively search subdirectories
                elif os.path.isdir(item_path):
                    found_path = self._search_directory(item_path, target_filename, current_depth + 1)
                    if found_path:
                        return found_path
                        
        except PermissionError:
            self.logger.warning(f"Permission denied accessing directory: {directory}")
        except Exception as e:
            self.logger.error(f"Error searching directory {directory}: {e}")
        
        return None
    
    def find_multiple_zips(self, websigns: list, lib_path: str) -> dict:
        """Find multiple ZIP files at once"""
        results = {}
        for websign in websigns:
            results[websign] = self.find_zip_by_websign(websign, lib_path)
        return results

# Convenience function for simple usage
def find_zip_by_websign(websign: str, lib_path: str, max_depth: int = 3) -> Optional[str]:
    """Convenience function to find ZIP file by websign"""
    locator = FileLocator(max_depth=max_depth)
    return locator.find_zip_by_websign(websign, lib_path)