import asyncio
import logging
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import aiohttp
import requests
from .image_processor import StickyNoteRenderer
from .printer import StickyNotePrinter
from .discovery import PrinterDiscovery, IPPPrinter

logger = logging.getLogger(__name__)

class HomeAssistantAPI:
    """Interface to Home Assistant API"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    async def get_calendar_events(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get today's events from a calendar entity"""
        try:
            today = date.today().isoformat()
            url = f"{self.base_url}/api/calendars/{entity_id}"
            params = {
                'start': f"{today}T00:00:00",
                'end': f"{today}T23:59:59"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        logger.info(f"Retrieved {len(events)} events from {entity_id}")
                        return events
                    else:
                        logger.error(f"Failed to get calendar events: {resp.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting calendar events: {e}")
            return []
    
    async def get_todo_items(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get todo items from a todo entity"""
        try:
            url = f"{self.base_url}/api/states/{entity_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        state = await resp.json()
                        # Extract todo items from attributes
                        todos = state.get('attributes', {}).get('todos', [])
                        logger.info(f"Retrieved {len(todos)} todo items from {entity_id}")
                        return todos
                    else:
                        logger.error(f"Failed to get todo items: {resp.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting todo items: {e}")
            return []
    
    async def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get state of any entity"""
        try:
            url = f"{self.base_url}/api/states/{entity_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.error(f"Failed to get entity state: {resp.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting entity state: {e}")
            return None

class StickyPrintService:
    """Main service for sticky note printing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ha_api = HomeAssistantAPI(
            base_url=config.get('ha_url', 'http://supervisor/core'),
            token=config.get('ha_token', '')
        )
        
        # Initialize components
        self.renderer = StickyNoteRenderer(
            font_size=config.get('font_size', 12),
            margin=config.get('margin', 10),
            line_spacing=config.get('line_spacing', 1.2)
        )
        
        self.discovery = PrinterDiscovery(
            timeout=config.get('discovery_timeout', 30)
        )
        
        self.printer = StickyNotePrinter()
        
        # Default calendar entity
        self.default_calendar = config.get('calendar_entity', 'calendar.family')
        
        # Printer setup task
        self._printer_setup_task = None
    
    async def initialize(self):
        """Initialize the service"""
        logger.info("Initializing Sticky Print Service")
        
        # Set up printer
        await self._setup_printer()
        
        logger.info("Sticky Print Service initialized")
    
    async def _setup_printer(self):
        """Set up printer connection"""
        try:
            if self.config.get('auto_discover', True):
                logger.info("Auto-discovering printer...")
                printer = await self.discovery.find_sticky_note_printer()
                
                if printer:
                    self.printer.set_printer(printer)
                    logger.info(f"Found and configured printer: {printer}")
                else:
                    logger.warning("No printer found via auto-discovery")
            
            # Check for manual IP configuration
            manual_ip = self.config.get('manual_ip', '').strip()
            if manual_ip and not self.printer.printer:
                logger.info(f"Using manual printer IP: {manual_ip}")
                manual_printer = self.discovery.create_manual_printer(manual_ip)
                
                # Verify the manual printer
                if await self.discovery.verify_printer(manual_printer.uri):
                    self.printer.set_printer(manual_printer)
                    logger.info(f"Configured manual printer: {manual_printer}")
                else:
                    logger.error(f"Manual printer {manual_ip} is not accessible")
            
            if not self.printer.printer:
                logger.warning("No printer configured. Print jobs will fail.")
            
        except Exception as e:
            logger.error(f"Error setting up printer: {e}")
    
    async def print_text(self, text: str, font_type: str = "sans-serif", 
                        job_name: str = "Text") -> bool:
        """Print plain text"""
        try:
            logger.info(f"Printing text: {job_name}")
            image = self.renderer.render_text(text, font_type)
            return await self.printer.print_image(image, job_name)
            
        except Exception as e:
            logger.error(f"Error printing text: {e}")
            return False
    
    async def print_qr_code(self, data: str, job_name: str = "QRCode") -> bool:
        """Print QR code"""
        try:
            logger.info(f"Printing QR code: {job_name}")
            image = self.renderer.render_qr_code(data)
            return await self.printer.print_image(image, job_name)
            
        except Exception as e:
            logger.error(f"Error printing QR code: {e}")
            return False
    
    async def print_calendar_today(self, calendar_entity: Optional[str] = None, 
                                  font_type: str = "sans-serif",
                                  job_name: str = "Calendar") -> bool:
        """Print today's calendar events"""
        try:
            entity_id = calendar_entity or self.default_calendar
            logger.info(f"Printing calendar events from {entity_id}")
            
            events = await self.ha_api.get_calendar_events(entity_id)
            image = self.renderer.render_calendar_events(events, font_type)
            return await self.printer.print_image(image, job_name)
            
        except Exception as e:
            logger.error(f"Error printing calendar: {e}")
            return False
    
    async def print_todo_list(self, todo_entity: str, font_type: str = "console",
                             job_name: str = "TodoList") -> bool:
        """Print todo list"""
        try:
            logger.info(f"Printing todo list from {todo_entity}")
            
            todos = await self.ha_api.get_todo_items(todo_entity)
            image = self.renderer.render_todo_list(todos, font_type)
            return await self.printer.print_image(image, job_name)
            
        except Exception as e:
            logger.error(f"Error printing todo list: {e}")
            return False
    
    async def handle_notification(self, message: str, title: str = "", 
                                 data: Optional[Dict[str, Any]] = None) -> bool:
        """Handle Home Assistant notification"""
        try:
            # Extract parameters from data
            data = data or {}
            font_type = data.get('font', 'sans-serif')
            job_name = title or "Notification"
            
            # Check for special notification types
            if data.get('type') == 'qr':
                return await self.print_qr_code(message, job_name)
            elif data.get('type') == 'calendar':
                calendar_entity = data.get('entity', self.default_calendar)
                return await self.print_calendar_today(calendar_entity, font_type, job_name)
            elif data.get('type') == 'todo':
                todo_entity = data.get('entity')
                if todo_entity:
                    return await self.print_todo_list(todo_entity, font_type, job_name)
                else:
                    logger.error("Todo entity required for todo notifications")
                    return False
            else:
                # Standard text notification
                full_text = f"{title}\n\n{message}" if title else message
                return await self.print_text(full_text, font_type, job_name)
                
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        try:
            printer_status = await self.printer.get_printer_status()
            
            return {
                "service": "running",
                "printer": printer_status,
                "config": {
                    "auto_discover": self.config.get('auto_discover', True),
                    "manual_ip": self.config.get('manual_ip', ''),
                    "default_calendar": self.default_calendar
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "service": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def configure_manual_printer(self, printer_ip: str, port: int = 631, 
                                     path: str = "/ipp/print") -> bool:
        """Configure printer manually by IP address"""
        try:
            logger.info(f"Configuring manual printer at {printer_ip}:{port}{path}")
            
            # Create manual printer configuration
            manual_printer = self.discovery.create_manual_printer(printer_ip, port, path)
            
            # Verify the manual printer is accessible
            if await self.discovery.verify_printer(manual_printer.uri):
                # Set the printer and update config
                self.printer.set_printer(manual_printer)
                logger.info(f"Successfully configured manual printer: {manual_printer}")
                
                # Update config to remember this manual printer
                self.config['manual_ip'] = printer_ip
                if port != 631:
                    self.config['manual_port'] = port
                if path != "/ipp/print":
                    self.config['manual_path'] = path
                    
                return True
            else:
                logger.error(f"Manual printer {printer_ip}:{port}{path} is not accessible")
                return False
                
        except Exception as e:
            logger.error(f"Error configuring manual printer: {e}")
            return False
    
    async def rediscover_printer(self) -> bool:
        """Force rediscovery of printer"""
        try:
            logger.info("Forcing printer rediscovery")
            await self._setup_printer()
            return self.printer.printer is not None
            
        except Exception as e:
            logger.error(f"Error rediscovering printer: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if self.printer:
            self.printer.cleanup()
