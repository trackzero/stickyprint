import asyncio
import tempfile
import os
import logging
from typing import Optional
from PIL import Image
from .discovery import IPPPrinter

logger = logging.getLogger(__name__)

class StickyNotePrinter:
    """Handles printing to sticky note IPP printer"""
    
    def __init__(self, printer: Optional[IPPPrinter] = None):
        self.printer = printer
        self.temp_dir = tempfile.mkdtemp(prefix="stickyprint_")
        logger.info(f"Created temp directory: {self.temp_dir}")
    
    def set_printer(self, printer: IPPPrinter):
        """Set the target printer"""
        self.printer = printer
        logger.info(f"Set printer: {printer}")
    
    async def print_image(self, image: Image.Image, job_name: str = "StickyNote") -> bool:
        """Print an image to the sticky note printer"""
        if not self.printer:
            logger.error("No printer configured")
            return False
        
        try:
            # Save image as BMP3 in temp directory
            temp_bmp = os.path.join(self.temp_dir, f"{job_name}.bmp")
            self._save_as_bmp3(image, temp_bmp)
            
            # Print using ipptool
            success = await self._send_to_printer(temp_bmp, job_name)
            
            # Clean up temp file
            try:
                os.unlink(temp_bmp)
            except:
                pass
                
            return success
            
        except Exception as e:
            logger.error(f"Error printing image: {e}")
            return False
    
    def _save_as_bmp3(self, image: Image.Image, output_path: str):
        """Save image in BMP3 format required by printer"""
        try:
            # Ensure monochrome
            if image.mode != '1':
                image = image.convert('1', dither=Image.FLOYDSTEINBERG)
            
            # Save as BMP with specific parameters for the printer
            image.save(output_path, 'BMP', 
                      compression=0,  # No compression
                      bits_per_pixel=1)  # 1-bit monochrome
            
            logger.debug(f"Saved BMP3: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving BMP3: {e}")
            raise
    
    async def _send_to_printer(self, bmp_path: str, job_name: str) -> bool:
        """Send BMP file to printer using ipptool"""
        try:
            # Create ipptool command
            cmd = [
                'ipptool',
                '-v',           # Verbose
                '-t',           # Test mode
                '-f', bmp_path, # File to print
                self.printer.uri,
                '-d', 'fileType=image/reverse-encoding-bmp',  # File type
                'print-job.test'  # IPP test file
            ]
            
            logger.info(f"Printing to {self.printer.uri}: {job_name}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Execute ipptool
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Print job successful: {job_name}")
                logger.debug(f"ipptool output: {stdout.decode()}")
                return True
            else:
                logger.error(f"Print job failed: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            logger.error("ipptool not found. Make sure CUPS is installed.")
            return False
        except Exception as e:
            logger.error(f"Error sending to printer: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to printer"""
        if not self.printer:
            return False
        
        try:
            # Use ipptool to get printer attributes
            process = await asyncio.create_subprocess_exec(
                'ipptool',
                '-t',
                self.printer.uri,
                'get-printer-attributes.test',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Printer connection test successful: {self.printer.uri}")
                return True
            else:
                logger.warning(f"Printer connection test failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing printer connection: {e}")
            return False
    
    async def get_printer_status(self) -> dict:
        """Get printer status information"""
        if not self.printer:
            return {"status": "no_printer"}
        
        try:
            # Test connection first
            connected = await self.test_connection()
            
            return {
                "status": "connected" if connected else "disconnected",
                "uri": self.printer.uri,
                "hostname": self.printer.hostname,
                "port": self.printer.port
            }
            
        except Exception as e:
            logger.error(f"Error getting printer status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp directory: {e}")

class IPPTestFiles:
    """IPP test file content for ipptool"""
    
    @staticmethod
    def create_print_job_test(output_path: str):
        """Create print-job.test file for ipptool"""
        content = """
# Print job test for sticky note printer
{
    # The name of the test...
    NAME "Print Job Test"
    
    # The operation to use
    OPERATION Print-Job
    
    # Attributes, starting in the operation group...
    GROUP operation-attributes-tag
    ATTR charset attributes-charset utf-8
    ATTR language attributes-natural-language en
    ATTR uri printer-uri $uri
    ATTR name requesting-user-name $user
    ATTR name job-name "Sticky Note Print Job"
    ATTR keyword media-type $filetype
    
    # What statuses are OK?
    STATUS successful-ok
    STATUS successful-ok-ignored-or-substituted-attributes
}
"""
        with open(output_path, 'w') as f:
            f.write(content.strip())

    @staticmethod
    def create_get_printer_attributes_test(output_path: str):
        """Create get-printer-attributes.test file for ipptool"""
        content = """
# Get printer attributes test
{
    # The name of the test...
    NAME "Get Printer Attributes"
    
    # The operation to use
    OPERATION Get-Printer-Attributes
    
    # Attributes, starting in the operation group...
    GROUP operation-attributes-tag
    ATTR charset attributes-charset utf-8
    ATTR language attributes-natural-language en
    ATTR uri printer-uri $uri
    
    # What statuses are OK?
    STATUS successful-ok
}
"""
        with open(output_path, 'w') as f:
            f.write(content.strip())

# Create IPP test files when module is imported
def _create_ipp_test_files():
    """Create necessary IPP test files"""
    try:
        test_dir = "/app"
        
        IPPTestFiles.create_print_job_test(
            os.path.join(test_dir, "print-job.test")
        )
        
        IPPTestFiles.create_get_printer_attributes_test(
            os.path.join(test_dir, "get-printer-attributes.test")
        )
        
        logger.debug("Created IPP test files")
        
    except Exception as e:
        logger.warning(f"Error creating IPP test files: {e}")

# Create test files on import
_create_ipp_test_files()
