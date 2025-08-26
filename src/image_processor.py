import os
import io
import logging
import textwrap
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from PIL import Image, ImageDraw, ImageFont
import qrcode

logger = logging.getLogger(__name__)

class StickyNoteRenderer:
    """Handles rendering content to sticky note format"""
    
    # Image specifications for sticky note printer
    WIDTH = 576
    BACKGROUND_COLOR = 255  # White
    TEXT_COLOR = 0  # Black
    
    # Font types
    FONT_SANS = "sans-serif"
    FONT_CONSOLE = "console" 
    FONT_HANDWRITING = "handwriting"
    
    def __init__(self, font_size: int = 12, margin: int = 10, line_spacing: float = 1.2):
        self.font_size = font_size
        self.margin = margin
        self.line_spacing = line_spacing
        self.fonts = self._load_fonts()
        
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Load the available fonts"""
        fonts = {}
        font_paths = {
            self.FONT_SANS: "/app/fonts/sans-serif.ttf",
            self.FONT_CONSOLE: "/app/fonts/console.ttf", 
            self.FONT_HANDWRITING: "/app/fonts/handwriting.ttf"
        }
        
        for font_type, path in font_paths.items():
            try:
                if os.path.exists(path):
                    fonts[font_type] = ImageFont.truetype(path, self.font_size)
                    logger.debug(f"Loaded font {font_type}: {path}")
                else:
                    # Fallback to default font
                    fonts[font_type] = ImageFont.load_default()
                    logger.warning(f"Font file not found: {path}, using default")
            except Exception as e:
                logger.error(f"Error loading font {font_type}: {e}")
                fonts[font_type] = ImageFont.load_default()
        
        return fonts
    
    def render_text(self, text: str, font_type: str = FONT_SANS, 
                   max_width: Optional[int] = None) -> Image.Image:
        """Render plain text to an image"""
        if max_width is None:
            max_width = self.WIDTH - (2 * self.margin)
        
        font = self.fonts.get(font_type, self.fonts[self.FONT_SANS])
        
        # Word wrap the text
        wrapped_lines = self._wrap_text(text, font, max_width)
        
        # Calculate image height
        line_height = int(font.getsize("Ay")[1] * self.line_spacing)
        image_height = (len(wrapped_lines) * line_height) + (2 * self.margin)
        
        # Create image
        image = Image.new('L', (self.WIDTH, image_height), self.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)
        
        # Draw text lines
        y_offset = self.margin
        for line in wrapped_lines:
            draw.text((self.margin, y_offset), line, fill=self.TEXT_COLOR, font=font)
            y_offset += line_height
        
        return self._prepare_for_printer(image)
    
    def render_qr_code(self, data: str, size_factor: int = 8) -> Image.Image:
        """Render a QR code"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size_factor,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Resize to fit width if needed
            if qr_img.width > self.WIDTH - (2 * self.margin):
                new_width = self.WIDTH - (2 * self.margin)
                aspect_ratio = qr_img.height / qr_img.width
                new_height = int(new_width * aspect_ratio)
                qr_img = qr_img.resize((new_width, new_height), Image.LANCZOS)
            
            # Create final image with margins
            image_height = qr_img.height + (2 * self.margin)
            image = Image.new('L', (self.WIDTH, image_height), self.BACKGROUND_COLOR)
            
            # Center the QR code
            x_offset = (self.WIDTH - qr_img.width) // 2
            image.paste(qr_img, (x_offset, self.margin))
            
            return self._prepare_for_printer(image)
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            # Fallback to text
            return self.render_text(f"QR: {data[:50]}...")
    
    def render_calendar_events(self, events: List[Dict[str, Any]], 
                             font_type: str = FONT_SANS) -> Image.Image:
        """Render today's calendar events"""
        if not events:
            return self.render_text("No events today", font_type)
        
        # Format events
        content_lines = ["Today's Events:", ""]
        
        for event in events:
            title = event.get('summary', 'Untitled Event')
            start_time = event.get('start', {}).get('dateTime', '')
            
            if start_time:
                try:
                    # Parse and format time
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M")
                    line = f"• {time_str} - {title}"
                except:
                    line = f"• {title}"
            else:
                line = f"• {title}"
            
            content_lines.append(line)
        
        content = "\n".join(content_lines)
        return self.render_text(content, font_type)
    
    def render_todo_list(self, todos: List[Dict[str, Any]], 
                        font_type: str = FONT_CONSOLE) -> Image.Image:
        """Render a todo list with checkboxes"""
        if not todos:
            return self.render_text("No todos", font_type)
        
        content_lines = ["Todo List:", ""]
        
        for todo in todos:
            summary = todo.get('summary', 'Untitled Task')
            completed = todo.get('completed', False)
            checkbox = "☑" if completed else "☐"
            content_lines.append(f"{checkbox} {summary}")
        
        content = "\n".join(content_lines)
        return self.render_text(content, font_type)
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, 
                   max_width: int) -> List[str]:
        """Wrap text to fit within the specified width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            
            # Check if the line fits
            if font.getsize(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word is too long, force it
                    lines.append(word)
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def _prepare_for_printer(self, image: Image.Image) -> Image.Image:
        """Prepare image for sticky note printer (monochrome, flipped)"""
        # Convert to monochrome (1-bit)
        image = image.convert('1', dither=Image.FLOYDSTEINBERG)
        
        # Flip upside down as required by the printer
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        
        return image
    
    def save_as_bmp3(self, image: Image.Image, output_path: str):
        """Save image in BMP3 format for the printer"""
        try:
            # Ensure it's monochrome
            if image.mode != '1':
                image = image.convert('1')
            
            # Save as BMP3
            image.save(output_path, 'BMP', compression=0)
            logger.info(f"Saved BMP3 image: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving BMP3 image: {e}")
            raise
    
    def create_combined_image(self, *images: Image.Image) -> Image.Image:
        """Combine multiple images vertically"""
        if not images:
            return Image.new('L', (self.WIDTH, 100), self.BACKGROUND_COLOR)
        
        if len(images) == 1:
            return images[0]
        
        # Calculate total height
        total_height = sum(img.height for img in images)
        
        # Create combined image
        combined = Image.new('L', (self.WIDTH, total_height), self.BACKGROUND_COLOR)
        
        y_offset = 0
        for img in images:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        
        return combined
