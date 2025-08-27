import asyncio
import subprocess
import re
import logging
import os
import socket
import ipaddress
import netifaces
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
        
        # First try ippfind (mDNS/Bonjour discovery)
        printers = await self._discover_with_ippfind()
        
        if not printers:
            logger.info("ippfind discovery failed, falling back to network scanning...")
            printers = await self._discover_with_network_scan()
        
        logger.info(f"Discovered {len(printers)} IPP printers")
        return printers
    
    async def _discover_with_ippfind(self) -> List[IPPPrinter]:
        """Try to discover printers using ippfind (mDNS/Bonjour)"""
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
                logger.warning(f"ippfind failed: {stderr.decode()}")
                return []
            
            # Parse the output
            printers = self._parse_ippfind_output(stdout.decode())
            logger.info(f"ippfind discovered {len(printers)} IPP printers")
            return printers
            
        except FileNotFoundError:
            logger.warning("ippfind command not found. Make sure CUPS is installed.")
            return []
        except Exception as e:
            logger.warning(f"Error during ippfind discovery: {e}")
            return []
    
    async def _discover_with_network_scan(self) -> List[IPPPrinter]:
        """Discover printers by scanning the local network for IPP services"""
        printers = []
        
        try:
            # Get local network ranges
            networks = self._get_local_networks()
            logger.info(f"Scanning networks: {networks}")
            
            # Create semaphore to limit concurrent connections
            semaphore = asyncio.Semaphore(100)
            
            # Scan all networks concurrently
            tasks = []
            for network in networks:
                for ip in network.hosts():
                    task = self._check_ipp_service(str(ip), semaphore)
                    tasks.append(task)
            
            # Wait for all scans to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful results
            for result in results:
                if isinstance(result, IPPPrinter):
                    printers.append(result)
                elif isinstance(result, Exception):
                    logger.debug(f"Scan error: {result}")
            
            logger.info(f"Network scan discovered {len(printers)} IPP printers")
            return printers
            
        except Exception as e:
            logger.error(f"Error during network scan discovery: {e}")
            return []
    
    def _get_local_networks(self) -> List[ipaddress.IPv4Network]:
        """Get local network ranges to scan"""
        networks = []
        
        try:
            # Get all network interfaces
            interfaces = netifaces.interfaces()
            
            for interface in interfaces:
                # Skip loopback
                if interface == 'lo':
                    continue
                
                addrs = netifaces.ifaddresses(interface)
                
                # Check IPv4 addresses
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get('addr')
                        netmask = addr_info.get('netmask')
                        
                        if ip and netmask and not ip.startswith('127.'):
                            try:
                                # Create network object
                                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                networks.append(network)
                                logger.debug(f"Found network: {network}")
                            except Exception as e:
                                logger.debug(f"Error processing {ip}/{netmask}: {e}")
        
        except Exception as e:
            logger.warning(f"Error getting local networks: {e}")
            # Fallback to common private network ranges (smaller subnets for faster scanning)
            try:
                networks = [
                    ipaddress.IPv4Network('192.168.1.0/24'),
                    ipaddress.IPv4Network('192.168.0.0/24'),
                ]
            except:
                pass
        
        return networks
    
    async def _check_ipp_service(self, ip: str, semaphore: asyncio.Semaphore) -> Optional[IPPPrinter]:
        """Check if a specific IP has an IPP service running on port 631"""
        async with semaphore:
            try:
                # Try to connect to IPP port (631)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, 631),
                    timeout=1.0
                )
                
                writer.close()
                await writer.wait_closed()
                
                # Connection successful, create printer object
                printer = IPPPrinter(
                    uri=f"ipp://{ip}:631/ipp/print",
                    hostname=ip,
                    port=631,
                    path="/ipp/print"
                )
                
                logger.debug(f"Found IPP service at {ip}")
                return printer
                
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                # No service or connection failed
                return None
            except Exception as e:
                logger.debug(f"Error checking {ip}: {e}")
                return None
    
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
            # Find the get-printer-attributes.test file
            # Check current directory first, then /app (for Docker compatibility)
            test_file = None
            for path in ['get-printer-attributes.test', '/app/get-printer-attributes.test']:
                if os.path.exists(path):
                    test_file = path
                    break
            
            if not test_file:
                logger.warning("get-printer-attributes.test file not found")
                return False
            
            # Use ipptool to check printer status
            process = await asyncio.create_subprocess_exec(
                'ipptool',
                '-t',
                uri,
                test_file,
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
                
        except FileNotFoundError:
            logger.error("ipptool command not found. Make sure CUPS is installed.")
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
