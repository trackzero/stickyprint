import asyncio
import subprocess
import re
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IPPPrinter:
    """Represents a discovered IPP printer"""
    uri: str
    hostname: str
    port: int
    path: str
    
    def __str__(self):
        return f"IPP Printer at {self.uri}"

class PrinterDiscovery:
    """Handles IPP printer discovery using ippfind"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        
    async def discover_printers(self) -> List[IPPPrinter]:
        """Discover IPP printers on the local network"""
        logger.info("Starting IPP printer discovery...")
        
        try:
            # Run ippfind command to discover printers
            process = await asyncio.create_subprocess_exec(
                'ippfind',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.warning("Printer discovery timed out")
                return []
            
            if process.returncode != 0:
                logger.error(f"ippfind failed: {stderr.decode()}")
                return []
            
            # Parse the output
            printers = self._parse_ippfind_output(stdout.decode())
            logger.info(f"Discovered {len(printers)} IPP printers")
            return printers
            
        except FileNotFoundError:
            logger.error("ippfind command not found. Make sure CUPS is installed.")
            return []
        except Exception as e:
            logger.error(f"Error during printer discovery: {e}")
            return []
    
    def _parse_ippfind_output(self, output: str) -> List[IPPPrinter]:
        """Parse ippfind output to extract printer information"""
        printers = []
        
        # Pattern to match IPP URLs like: ipp://hostname.local:631/ipp/print
        ipp_pattern = r'ipp://([^:]+):(\d+)(/.*)'
        
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = re.match(ipp_pattern, line)
            if match:
                hostname = match.group(1)
                port = int(match.group(2))
                path = match.group(3)
                
                printer = IPPPrinter(
                    uri=line,
                    hostname=hostname,
                    port=port,
                    path=path
                )
                printers.append(printer)
                logger.debug(f"Found printer: {printer}")
        
        return printers
    
    async def find_sticky_note_printer(self) -> Optional[IPPPrinter]:
        """Find the first available sticky note printer"""
        printers = await self.discover_printers()
        
        if not printers:
            logger.warning("No IPP printers found")
            return None
        
        # For now, return the first printer found
        # In the future, we could add logic to identify sticky note printers specifically
        printer = printers[0]
        logger.info(f"Selected printer: {printer}")
        return printer
    
    async def verify_printer(self, uri: str) -> bool:
        """Verify that a printer URI is accessible"""
        try:
            # Use ipptool to check printer status
            process = await asyncio.create_subprocess_exec(
                'ipptool',
                '-t',
                uri,
                'get-printer-attributes.test',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Printer {uri} is accessible")
                return True
            else:
                logger.warning(f"Printer {uri} verification failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying printer {uri}: {e}")
            return False

    def create_manual_printer(self, ip_address: str, port: int = 631, path: str = "/ipp/print") -> IPPPrinter:
        """Create a printer object from manual configuration"""
        uri = f"ipp://{ip_address}:{port}{path}"
        return IPPPrinter(
            uri=uri,
            hostname=ip_address,
            port=port,
            path=path
        )
