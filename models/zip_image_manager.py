import zipfile
import os
import io
import logging
from typing import List, Optional, Tuple
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage

class ZipImageManager(QObject):
    """
    Manager for handling ZIP files containing images
    Supports both flat and nested directory structures
    """
    
    # Signals for UI updates
    images_loaded = pyqtSignal(int)  # Emits number of images loaded
    load_error = pyqtSignal(str)     # Emits error messages
    
    def __init__(self):
        super().__init__()
        self.current_zip_path = None
        self.zip_file = None
        self.image_files = []
        self.current_index = -1
        self.logger = logging.getLogger(__name__)
        
        # Cache properties
        self.image_cache = {}  # Dictionary to cache image data
        self.cache_size = 5    # Number of images to cache around current position
        self.preload_next_timer = QTimer()
        self.preload_next_timer.setSingleShot(True)
        self.preload_next_timer.timeout.connect(self.preload_adjacent_images)

        # Deletion properties
        self.deletion_history = []
        
    def load_zip_file(self, zip_path: str) -> bool:
        """Load and parse ZIP file"""
        try:
            # Close previous ZIP file if open
            if self.zip_file:
                self.zip_file.close()
                
            # Validate file
            if not os.path.exists(zip_path):
                self.load_error.emit(f"ZIP file not found: {zip_path}")
                return False
                
            # Open ZIP file
            self.zip_file = zipfile.ZipFile(zip_path, 'r')
            self.current_zip_path = zip_path
            
            # Parse ZIP structure and find images
            self.image_files = self._parse_zip_structure()
            
            if not self.image_files:
                self.load_error.emit("No images found in ZIP file")
                return False
                
            self.current_index = 0
            self.logger.info(f"Loaded ZIP file: {zip_path}, found {len(self.image_files)} images")
            self.images_loaded.emit(len(self.image_files))
            return True
            
        except zipfile.BadZipFile:
            error_msg = "Invalid or corrupted ZIP file"
            self.load_error.emit(error_msg)
            self.logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Failed to load ZIP file: {str(e)}"
            self.load_error.emit(error_msg)
            self.logger.error(error_msg)
            return False
    
    def _parse_zip_structure(self) -> List[Tuple[str, str]]:
        """Parse ZIP file structure and identify image files"""
        image_files = []
        all_files = self.zip_file.namelist()
        
        # Supported image extensions
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        
        # Check for nested structure (folder named '1')
        nested_folder = None
        for file_path in all_files:
            if file_path.startswith('1/') and '/' in file_path:
                nested_folder = '1'
                break
        
        if nested_folder:
            # Nested structure: images are in folder '1/'
            for file_path in all_files:
                if file_path.startswith(f'{nested_folder}/') and not file_path.endswith('/'):
                    filename = os.path.basename(file_path)
                    if self._is_image_file(filename):
                        display_name = filename
                        image_files.append((file_path, display_name))
        else:
            # Flat structure: images are in root
            for file_path in all_files:
                if not file_path.endswith('/'):  # Skip directories
                    filename = os.path.basename(file_path)
                    if self._is_image_file(filename):
                        display_name = filename
                        image_files.append((file_path, display_name))
        
        # Sort images by numeric order (1.png, 2.png, 3.jpg, etc.)
        image_files.sort(key=lambda x: self._extract_image_number(x[1]))
        
        return image_files
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    
    def _extract_image_number(self, filename: str) -> int:
        """Extract numeric part from filename for sorting"""
        try:
            # Remove extension and convert to integer
            name_part = os.path.splitext(filename)[0]
            return int(name_part)
        except (ValueError, TypeError):
            # If not numeric, return a large number to push to end
            return 999999
    
    def get_current_image_data(self) -> Optional[bytes]:
        """Get image data for current image with cache support"""
        if not self.has_images() or self.current_index < 0:
            return None
            
        # Check cache first
        if self.current_index in self.image_cache:
            return self.image_cache[self.current_index]
            
        try:
            image_path, _ = self.image_files[self.current_index]
            image_data = self.zip_file.read(image_path)
            
            # Add to cache
            self.image_cache[self.current_index] = image_data
            
            # Start preloading adjacent images
            self.preload_next_timer.start(100)  # Small delay to prioritize current image
            
            return image_data
        except Exception as e:
            self.logger.error(f"Failed to read image {self.current_index}: {e}")
            return None

    def preload_adjacent_images(self):
        """Preload images adjacent to current position"""
        if not self.has_images():
            return
            
        total_images = len(self.image_files)
        
        # Calculate range of images to preload
        start_idx = max(0, self.current_index - self.cache_size)
        end_idx = min(total_images - 1, self.current_index + self.cache_size)
        
        for idx in range(start_idx, end_idx + 1):
            if idx != self.current_index and idx not in self.image_cache:
                self.preload_single_image(idx)

    def preload_single_image(self, index: int):
        """Preload single image into cache"""
        try:
            if 0 <= index < len(self.image_files):
                image_path, _ = self.image_files[index]
                image_data = self.zip_file.read(image_path)
                self.image_cache[index] = image_data
        except Exception as e:
            self.logger.debug(f"Failed to preload image {index}: {e}")
    
    def get_current_image_pixmap(self) -> Optional[QPixmap]:
        """Get current image as QPixmap"""
        image_data = self.get_current_image_data()
        if not image_data:
            return None
            
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            return pixmap
        except Exception as e:
            self.logger.error(f"Failed to create pixmap: {e}")
            return None
    
    def navigate_to_image(self, index: int) -> bool:
        """Navigate to specific image index and trigger preloading"""
        if 0 <= index < len(self.image_files):
            self.current_index = index
            # Trigger immediate preloading for better responsiveness
            self.preload_next_timer.start(10)
            return True
        return False
    
    def next_image(self) -> bool:
        """Move to next image"""
        if self.has_images() and self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            return True
        return False
    
    def previous_image(self) -> bool:
        """Move to previous image"""
        if self.has_images() and self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def get_current_image_info(self) -> Tuple[int, int, str]:
        """Get current image information"""
        if not self.has_images():
            return (0, 0, "")
        
        current_filename = self.image_files[self.current_index][1]
        return (self.current_index + 1, len(self.image_files), current_filename)
    
    def has_images(self) -> bool:
        """Check if there are images available"""
        return len(self.image_files) > 0 and self.current_index >= 0
    
    def get_image_count(self) -> int:
        """Get total number of images"""
        return len(self.image_files)
    
    def get_current_index(self) -> int:
        """Get current image index"""
        return self.current_index
    
    def get_image_list(self) -> List[Tuple[str, str]]:
        """Get list of all images (path_in_zip, display_name)"""
        return self.image_files.copy()
    
    def close(self):
        """Close ZIP file and cleanup"""
        if self.zip_file:
            self.zip_file.close()
            self.zip_file = None
        # Don't clear current_zip_path to allow reloading
        self.image_files = []
        self.current_index = -1
        self.image_cache.clear()
        self.preload_next_timer.stop()
        # Note: Don't clear deletion_history, need to preserve deletion records
    
    def clear_cache(self):
        """Clear image cache"""
        self.image_cache.clear()

    def set_cache_size(self, size: int):
        """Set cache size (number of images to keep around current position)"""
        self.cache_size = max(1, size)  # Minimum cache size is 1
        # Clear cache if size is reduced
        if len(self.image_cache) > self.cache_size * 2 + 1:
            self.image_cache.clear()

    def get_cache_info(self) -> dict:
        """Get cache statistics"""
        return {
            'cache_size': len(self.image_cache),
            'total_images': len(self.image_files),
            'cache_hit_ratio': self.calculate_cache_hit_ratio()
        }

    def calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio (for monitoring purposes)"""
        # This would need additional tracking for proper calculation
        # Simplified implementation
        total_accesses = len(self.image_files) * 2  # Rough estimate
        cache_hits = len(self.image_cache)
        return cache_hits / total_accesses if total_accesses > 0 else 0
    
    def __del__(self):
        """Destructor to ensure proper cleanup"""
        self.close()
        
    def delete_current_image(self) -> bool:
        """Delete current image from ZIP file"""
        if not self.has_images():
            return False
            
        image_path, display_name = self.image_files[self.current_index]
        
        # Create deletion command
        deletion_cmd = {
            'index': self.current_index,
            'image_path': image_path,
            'display_name': display_name,
            'image_data': self.get_current_image_data()  # Backup image data
        }
        
        # Remove from internal list first
        deleted_item = self.image_files.pop(self.current_index)
        
        # Update cache
        self._update_cache_after_deletion(self.current_index)
        
        # Adjust current index if needed
        if self.current_index >= len(self.image_files):
            self.current_index = max(0, len(self.image_files) - 1)
            
        # Add to deletion history
        self.deletion_history.append(deletion_cmd)
        
        return True
    
    def delete_images_by_range(self, start_index: int, end_index: int) -> bool:
        """Delete multiple images by index range"""
        if not self.has_images() or start_index < 0 or end_index >= len(self.image_files):
            return False
            
        # Collect deletion commands
        deletion_commands = []
        for i in range(end_index, start_index - 1, -1):  # Reverse to maintain indices
            image_path, display_name = self.image_files[i]
            deletion_cmd = {
                'index': i,
                'image_path': image_path,
                'display_name': display_name,
                'image_data': self._get_image_data_by_index(i)
            }
            deletion_commands.append(deletion_cmd)
            
        # Remove from internal list (reverse order to maintain indices)
        for i in range(end_index, start_index - 1, -1):
            self.image_files.pop(i)
            
        # Update cache and current index
        self._update_cache_after_deletion(start_index)
        if self.current_index >= len(self.image_files):
            self.current_index = max(0, len(self.image_files) - 1)
            
        # Add to deletion history as a batch
        self.deletion_history.extend(deletion_commands)
        
        return True
    
    def undo_last_deletion(self) -> bool:
        """Undo the last deletion operation"""
        if not self.deletion_history:
            return False
            
        # Get last deletion command
        deletion_cmd = self.deletion_history[-1]
        
        # Check if it's a stitching operation (has 'type' key)
        if 'type' in deletion_cmd and deletion_cmd['type'] == 'stitch':
            # For stitching operations, use the dedicated undo method
            return self.undo_last_stitch(deletion_cmd)
        else:
            # For regular deletion operations, use original logic
            return self._undo_regular_deletion(deletion_cmd)

    def _undo_regular_deletion(self, deletion_cmd: dict) -> bool:
        """Undo a regular deletion operation"""
        try:
            # Restore to image files list
            self.image_files.insert(deletion_cmd['index'], 
                                (deletion_cmd['image_path'], deletion_cmd['display_name']))
            
            # Update cache
            self.image_cache[deletion_cmd['index']] = deletion_cmd['image_data']
            
            # Sort to maintain order
            self.image_files.sort(key=lambda x: self._extract_image_number(x[1]))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to undo deletion: {e}")
            return False
    
    def _update_cache_after_deletion(self, deleted_index: int):
        """Update cache after deletion"""
        # Remove deleted item from cache
        if deleted_index in self.image_cache:
            del self.image_cache[deleted_index]
            
        # Shift cache entries
        new_cache = {}
        for idx, data in self.image_cache.items():
            if idx > deleted_index:
                new_cache[idx - 1] = data
            elif idx < deleted_index:
                new_cache[idx] = data
        self.image_cache = new_cache

    def stitch_current_with_next(self) -> tuple:
        """
        Stitch current image with the next image vertically
        
        Returns:
            tuple: (success: bool, message: str, stitched_image_data: bytes)
        """
        if not self.has_images() or self.current_index >= len(self.image_files) - 1:
            return False, "No next image available for stitching", None
        
        try:
            # Save complete state before modification for undo
            original_image_files = self.image_files.copy()
            original_cache = self.image_cache.copy()
            
            # Get current and next image data
            current_image_data = self.get_current_image_data()
            next_image_data = self._get_image_data_by_index(self.current_index + 1)
            
            if not current_image_data or not next_image_data:
                return False, "Failed to load image data", None
            
            # Check if images can be stitched
            from utils.helpers import can_stitch_images, stitch_images_vertically
            
            can_stitch, reason, width_match, height_ratio = can_stitch_images(current_image_data, next_image_data)
            
            if not can_stitch:
                return False, f"Images cannot be stitched: {reason}", None
            
            # Perform stitching
            stitched_image_data = stitch_images_vertically(current_image_data, next_image_data)
            
            if not stitched_image_data:
                return False, "Failed to stitch images", None
            
            # Create stitching command for undo with complete state
            stitch_cmd = {
                'type': 'stitch',
                'original_image_files': original_image_files,
                'original_cache': original_cache,
                'current_index': self.current_index,
                'current_path': self.image_files[self.current_index][0],
                'current_display': self.image_files[self.current_index][1],
                'current_data': current_image_data,
                'next_index': self.current_index + 1,
                'next_path': self.image_files[self.current_index + 1][0],
                'next_display': self.image_files[self.current_index + 1][1],
                'next_data': next_image_data,
                'stitched_data': stitched_image_data
            }
            
            # Update internal state
            # Replace current image with stitched image
            current_filename = self.image_files[self.current_index][1]
            stitched_display_name = f"stitched_{current_filename}"
            self.image_files[self.current_index] = (self.image_files[self.current_index][0], stitched_display_name)
            
            # Update cache with stitched image
            self.image_cache[self.current_index] = stitched_image_data
            
            # Remove next image (the bottom part)
            self.image_files.pop(self.current_index + 1)
            
            # Update cache for removed image
            if self.current_index + 1 in self.image_cache:
                del self.image_cache[self.current_index + 1]
            
            # Shift cache entries after the removed index
            self._update_cache_after_deletion(self.current_index + 1)
            
            # Add to deletion history for undo
            self.deletion_history.append(stitch_cmd)
            
            return True, "Images stitched successfully", stitched_image_data
            
        except Exception as e:
            return False, f"Stitching failed: {str(e)}", None

    def undo_last_stitch(self, stitch_cmd: dict) -> bool:
        """
        Undo a stitching operation by restoring complete state
        
        Args:
            stitch_cmd: The stitching command to undo
            
        Returns:
            bool: True if successful
        """
        try:
            # Simply restore the complete original state
            if 'original_image_files' in stitch_cmd:
                self.image_files = stitch_cmd['original_image_files']
                self.image_cache = stitch_cmd['original_cache'].copy()
            else:
                # Fallback to the detailed method
                return self._undo_stitch_detailed(stitch_cmd)
            
            print(f"Undo stitch: restored complete state with {len(self.image_files)} images")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to undo stitch: {e}")
            return False
    
    def _get_image_data_by_index(self, index: int) -> Optional[bytes]:
        """Get image data by index (for backup)"""
        try:
            image_path, _ = self.image_files[index]
            return self.zip_file.read(image_path)
        except:
            return None
    
    def commit_deletions_to_zip(self) -> bool:
        """Physically delete images from ZIP file"""
        if not self.deletion_history:
            return True
            
        try:
            from utils.helpers import delete_from_zip
            
            files_to_delete = [cmd['image_path'] for cmd in self.deletion_history]
            print(f"Attempting to delete {len(files_to_delete)} files from ZIP")
            
            # ZIP file should already be closed to release file lock
            success = delete_from_zip(self.current_zip_path, files_to_delete)
            
            if success:
                self.deletion_history.clear()
                print("Successfully committed deletions")
                return True
            else:
                print("delete_from_zip returned False")
                return False
                
        except Exception as e:
            print(f"Exception in commit_deletions_to_zip: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_cover_image(self, zip_path, size=None):
        """
        Extract first image from ZIP as cover
        
        Args:
            zip_path: Path to ZIP file
            size: Optional tuple (width, height) for scaling. 
                If None, returns original size.
                If provided, scales to fit within size while keeping aspect ratio.
        
        Returns:
            QPixmap of the cover image
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get image files sorted by name
                image_files = [f for f in zip_ref.namelist() 
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))]
                
                if not image_files:
                    return None
                
                # Get first image file
                first_image = sorted(image_files)[0]
                
                # Read image data
                with zip_ref.open(first_image) as image_file:
                    image_data = image_file.read()
                
                # Create QPixmap from image data
                image = QImage()
                if not image.loadFromData(image_data):
                    return None
                
                pixmap = QPixmap.fromImage(image)
                
                # Only scale if size is specified
                if size:
                    # Use KeepAspectRatio to fit within size without cropping
                    scaled_pixmap = pixmap.scaled(
                        size[0], size[1], 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    return scaled_pixmap
                else:
                    return pixmap  # Return original size
                    
        except Exception as e:
            print(f"Error extracting cover from {zip_path}: {e}")
            return None
    
    def get_cover_cache_key(self, zip_path):
        """Generate cache key for cover image"""
        return f"cover_{zip_path}"