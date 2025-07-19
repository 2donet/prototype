

from imagekit.processors import ResizeToFill
from PIL import Image, ImageOps
import os

class SmartAvatarProcessor:
    """
    Custom processor that handles avatar processing with smart cropping and auto-orientation
    """
    
    def __init__(self, width, height, quality=85):
        self.width = width
        self.height = height
        self.quality = quality
    
    def process(self, image):
        # Auto-rotate based on EXIF data
        image = ImageOps.exif_transpose(image)
        
        # Convert to RGB if necessary (for WEBP output)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create a white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Smart crop to square (center focus)
        width, height = image.size
        size = min(width, height)
        
        # Calculate crop box for center crop
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        
        # Crop to square
        image = image.crop((left, top, right, bottom))
        
        # Resize to target dimensions
        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        
        return image


# Alternative approach using django-imagekit's SourceGroupProcessor
from imagekit.specs import SourceGroupSpec
from imagekit.processors import ResizeToFill, Adjust

class AvatarSpec(SourceGroupSpec):
    """
    This approach creates multiple sizes from upload and deletes the original
    """
    processors = [
        ResizeToFill(400, 400),  # Main size
        Adjust(sharpness=1.1),   # Slight sharpening after resize
    ]
    format = 'WEBP'
    options = {'quality': 85}

class AvatarThumbnailSpec(SourceGroupSpec):
    processors = [ResizeToFill(150, 150)]
    format = 'WEBP'
    options = {'quality': 85}

class AvatarSmallSpec(SourceGroupSpec):
    processors = [ResizeToFill(50, 50)]
    format = 'WEBP'
    options = {'quality': 80}