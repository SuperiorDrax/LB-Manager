import os
import re
import zipfile
import os
import shutil
from typing import List
from PIL import Image
import io

def fetch_zip_numbers_from_directory(lib_path):
    """Recursively scan directory and extract integers from ZIP filenames"""
    numbers = set()
    
    def scan_directory(directory):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            if os.path.isfile(item_path) and item.lower().endswith('.zip'):
                # Extract number from filename
                name_without_ext = os.path.splitext(item)[0]
                match = re.match(r'^(\d+)$', name_without_ext)
                if match:
                    try:
                        numbers.add(int(match.group(1)))
                    except ValueError:
                        continue
            elif os.path.isdir(item_path):
                scan_directory(item_path)
    
    scan_directory(lib_path)
    return sorted(numbers)

def save_numbers_to_file(numbers, filepath='./nums.txt'):
    """Save number list to file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for number in numbers:
            f.write(f"{number}\n")

def delete_from_zip(zip_path: str, files_to_delete: List[str]) -> bool:
    """
    Delete files from ZIP by creating a new ZIP without the specified files
    """
    import tempfile
    
    try:
        print(f"Starting deletion from {zip_path}")
        print(f"Files to delete: {files_to_delete}")
        
        # Check if source file exists and is accessible
        if not os.path.exists(zip_path):
            print(f"Error: Source file does not exist: {zip_path}")
            return False
            
        if not os.access(zip_path, os.R_OK):
            print(f"Error: No read permission for: {zip_path}")
            return False
            
        # Create temporary file in same directory
        temp_dir = os.path.dirname(zip_path) or '.'
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip', dir=temp_dir) as temp_file:
            temp_path = temp_file.name
        
        print(f"Created temp file: {temp_path}")
        
        # Create new ZIP without deleted files
        files_copied = 0
        files_skipped = 0
        
        with zipfile.ZipFile(zip_path, 'r') as zip_read:
            with zipfile.ZipFile(temp_path, 'w') as zip_write:
                for item in zip_read.infolist():
                    if item.filename not in files_to_delete:
                        data = zip_read.read(item.filename)
                        zip_write.writestr(item, data)
                        files_copied += 1
                    else:
                        files_skipped += 1
                        print(f"Skipping file: {item.filename}")
        
        print(f"Files copied: {files_copied}, Files skipped: {files_skipped}")
        
        # Verify new ZIP file
        if not os.path.exists(temp_path):
            print("Error: Temporary file was not created")
            return False
            
        # Check file size to ensure it's valid
        if os.path.getsize(temp_path) == 0:
            print("Error: Temporary file is empty")
            return False
            
        # Replace original file
        print(f"Replacing original file with temp file")
        os.replace(temp_path, zip_path)
        print("Successfully replaced file")
        
        return True
        
    except zipfile.BadZipFile as e:
        print(f"Bad ZIP file error: {e}")
        return False
    except PermissionError as e:
        print(f"Permission error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temporary file if it still exists
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
                print("Cleaned up temp file")
        except:
            pass

def get_zip_backup_path(zip_path: str) -> str:
    """Get backup file path for a ZIP file"""
    return zip_path + '.backup'

def restore_zip_from_backup(zip_path: str) -> bool:
    """Restore ZIP file from backup"""
    backup_path = get_zip_backup_path(zip_path)
    if os.path.exists(backup_path):
        os.replace(backup_path, zip_path)
        return True
    return False

def stitch_images_vertically(image1_data: bytes, image2_data: bytes) -> bytes:
    """
    Stitch two images vertically (image1 on top, image2 on bottom)
    
    Args:
        image1_data: Top image data bytes
        image2_data: Bottom image data bytes
        
    Returns:
        bytes: Combined image data in PNG format
    """
    try:
        # Open images from bytes
        image1 = Image.open(io.BytesIO(image1_data))
        image2 = Image.open(io.BytesIO(image2_data))
        
        # Ensure both images have the same width
        width = max(image1.width, image2.width)
        
        # Resize images to have same width while maintaining aspect ratio
        if image1.width != width:
            ratio = width / image1.width
            new_height = int(image1.height * ratio)
            image1 = image1.resize((width, new_height), Image.Resampling.LANCZOS)
        
        if image2.width != width:
            ratio = width / image2.width
            new_height = int(image2.height * ratio)
            image2 = image2.resize((width, new_height), Image.Resampling.LANCZOS)
        
        # Calculate total height
        total_height = image1.height + image2.height
        
        # Create new image
        combined_image = Image.new('RGB', (width, total_height))
        
        # Paste images (image1 on top, image2 on bottom)
        combined_image.paste(image1, (0, 0))
        combined_image.paste(image2, (0, image1.height))
        
        # Convert to bytes
        output_buffer = io.BytesIO()
        combined_image.save(output_buffer, format='PNG')
        
        return output_buffer.getvalue()
        
    except Exception as e:
        raise Exception(f"Failed to stitch images: {str(e)}")

def can_stitch_images(image1_data: bytes, image2_data: bytes) -> tuple:
    """
    Check if two images can be stitched and return compatibility info
    
    Returns:
        tuple: (can_stitch: bool, reason: str, width_match: bool, height_ratio: float)
    """
    try:
        image1 = Image.open(io.BytesIO(image1_data))
        image2 = Image.open(io.BytesIO(image2_data))
        
        width_match = image1.width == image2.width
        height_ratio = image1.height / image2.height if image2.height > 0 else 0
        
        # Consider images stitchable if width difference is small or heights are similar
        can_stitch = (abs(image1.width - image2.width) / max(image1.width, image2.width) < 0.1 or
                     abs(height_ratio - 1.0) < 0.3)
        
        reason = ""
        if not can_stitch:
            reason = f"Size mismatch: {image1.width}x{image1.height} vs {image2.width}x{image2.height}"
        
        return can_stitch, reason, width_match, height_ratio
        
    except Exception as e:
        return False, f"Error checking images: {str(e)}", False, 0