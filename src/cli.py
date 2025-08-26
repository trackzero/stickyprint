#!/usr/bin/env python3
"""
Command Line Interface for Sticky Note Printer
Allows direct printing from the command line
"""

import asyncio
import argparse
import sys
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .config import UniversalConfig
from .ha_integration import StickyPrintService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class StickyPrintCLI:
    """Command line interface for sticky note printing"""
    
    def __init__(self):
        self.service: Optional[StickyPrintService] = None
    
    async def initialize(self, config_path: Optional[str] = None):
        """Initialize the service with configuration"""
        try:
            if config_path and Path(config_path).exists():
                # Load from specific config file
                with open(config_path, 'r') as f:
                    if config_path.endswith('.json'):
                        config_data = json.load(f)
                    else:
                        import yaml
                        config_data = yaml.safe_load(f)
                
                # Create a temporary config file for UniversalConfig
                temp_config = UniversalConfig()
                temp_config.config = temp_config._normalize_standalone_config(config_data)
                config = temp_config.to_dict()
            else:
                # Use default configuration loading
                universal_config = UniversalConfig()
                config = universal_config.to_dict()
            
            self.service = StickyPrintService(config)
            await self.service.initialize()
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def print_text(self, text: str, font: str = "sans-serif", job_name: str = "CLI") -> bool:
        """Print text"""
        if not self.service:
            logger.error("Service not initialized")
            return False
        
        success = await self.service.print_text(text, font, job_name)
        if success:
            logger.info(f"Successfully printed text: {job_name}")
        else:
            logger.error(f"Failed to print text: {job_name}")
        return success
    
    async def print_qr(self, data: str, job_name: str = "CLI-QR") -> bool:
        """Print QR code"""
        if not self.service:
            logger.error("Service not initialized")
            return False
        
        success = await self.service.print_qr_code(data, job_name)
        if success:
            logger.info(f"Successfully printed QR code: {job_name}")
        else:
            logger.error(f"Failed to print QR code: {job_name}")
        return success
    
    async def print_calendar(self, calendar_entity: Optional[str] = None, 
                           font: str = "sans-serif", job_name: str = "CLI-Calendar") -> bool:
        """Print today's calendar events"""
        if not self.service:
            logger.error("Service not initialized")
            return False
        
        success = await self.service.print_calendar_today(calendar_entity, font, job_name)
        if success:
            logger.info(f"Successfully printed calendar: {job_name}")
        else:
            logger.error(f"Failed to print calendar: {job_name}")
        return success
    
    async def print_todo(self, todo_entity: str, font: str = "console", 
                        job_name: str = "CLI-Todo") -> bool:
        """Print todo list"""
        if not self.service:
            logger.error("Service not initialized")
            return False
        
        success = await self.service.print_todo_list(todo_entity, font, job_name)
        if success:
            logger.info(f"Successfully printed todo list: {job_name}")
        else:
            logger.error(f"Failed to print todo list: {job_name}")
        return success
    
    async def discover_printer(self):
        """Discover and show printer information"""
        if not self.service:
            logger.error("Service not initialized")
            return
        
        success = await self.service.rediscover_printer()
        if success:
            status = await self.service.get_status()
            printer_info = status.get('printer', {})
            if printer_info.get('status') == 'connected':
                print(f"✓ Found printer: {printer_info.get('uri')}")
                print(f"  Hostname: {printer_info.get('hostname')}")
                print(f"  Port: {printer_info.get('port')}")
            else:
                print("✗ Printer found but not accessible")
        else:
            print("✗ No printer found")
    
    async def status(self):
        """Show service status"""
        if not self.service:
            logger.error("Service not initialized")
            return
        
        status = await self.service.get_status()
        print(f"Service Status: {status.get('service', 'unknown')}")
        
        printer = status.get('printer', {})
        print(f"Printer Status: {printer.get('status', 'unknown')}")
        
        if printer.get('status') == 'connected':
            print(f"Printer URI: {printer.get('uri', 'unknown')}")
        
        config = status.get('config', {})
        print(f"Auto-discover: {config.get('auto_discover', 'unknown')}")
        if config.get('manual_ip'):
            print(f"Manual IP: {config.get('manual_ip')}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.service:
            self.service.cleanup()

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Sticky Note Printer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stickyprint-cli text "Hello World!"
  stickyprint-cli qr "https://example.com"
  stickyprint-cli calendar
  stickyprint-cli todo todo.shopping
  stickyprint-cli discover
  stickyprint-cli status
  
  # Use custom config file
  stickyprint-cli --config /path/to/config.json text "Hello"
  
  # Use different font
  stickyprint-cli text "Code snippet" --font console
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (JSON or YAML)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Text command
    text_parser = subparsers.add_parser('text', help='Print text')
    text_parser.add_argument('text', help='Text to print')
    text_parser.add_argument('--font', '-f', 
                           choices=['sans-serif', 'console', 'handwriting'],
                           default='sans-serif',
                           help='Font to use')
    text_parser.add_argument('--name', '-n', default='CLI-Text',
                           help='Job name')
    
    # QR code command
    qr_parser = subparsers.add_parser('qr', help='Print QR code')
    qr_parser.add_argument('data', help='Data to encode in QR code')
    qr_parser.add_argument('--name', '-n', default='CLI-QR',
                          help='Job name')
    
    # Calendar command
    calendar_parser = subparsers.add_parser('calendar', help='Print today\'s calendar events')
    calendar_parser.add_argument('--entity', '-e',
                               help='Calendar entity ID (default from config)')
    calendar_parser.add_argument('--font', '-f',
                               choices=['sans-serif', 'console', 'handwriting'],
                               default='sans-serif',
                               help='Font to use')
    calendar_parser.add_argument('--name', '-n', default='CLI-Calendar',
                               help='Job name')
    
    # Todo command
    todo_parser = subparsers.add_parser('todo', help='Print todo list')
    todo_parser.add_argument('entity', help='Todo entity ID')
    todo_parser.add_argument('--font', '-f',
                           choices=['sans-serif', 'console', 'handwriting'],
                           default='console',
                           help='Font to use')
    todo_parser.add_argument('--name', '-n', default='CLI-Todo',
                           help='Job name')
    
    # Discover command
    subparsers.add_parser('discover', help='Discover printers on network')
    
    # Status command  
    subparsers.add_parser('status', help='Show service status')
    
    return parser

async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = StickyPrintCLI()
    
    try:
        # Initialize service
        await cli.initialize(args.config)
        
        # Execute command
        if args.command == 'text':
            success = await cli.print_text(args.text, args.font, args.name)
            return 0 if success else 1
        
        elif args.command == 'qr':
            success = await cli.print_qr(args.data, args.name)
            return 0 if success else 1
        
        elif args.command == 'calendar':
            success = await cli.print_calendar(args.entity, args.font, args.name)
            return 0 if success else 1
        
        elif args.command == 'todo':
            success = await cli.print_todo(args.entity, args.font, args.name)
            return 0 if success else 1
        
        elif args.command == 'discover':
            await cli.discover_printer()
            return 0
        
        elif args.command == 'status':
            await cli.status()
            return 0
        
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        cli.cleanup()

def run_main():
    """Synchronous wrapper for async main"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        return 1

if __name__ == '__main__':
    sys.exit(run_main())
