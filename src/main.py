import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from aiohttp import web, web_request
from aiohttp.web import middleware
from ha_integration import StickyPrintService
from config import UniversalConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StickyPrintServer:
    """HTTP server for sticky note printing service"""
    
    def __init__(self):
        self.app = web.Application(middlewares=[self.cors_middleware])
        self.service: Optional[StickyPrintService] = None
        self.setup_routes()
    
    @middleware
    async def cors_middleware(self, request, handler):
        """Handle CORS for API requests"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    def setup_routes(self):
        """Set up HTTP routes"""
        # API endpoints
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_post('/api/print/text', self.print_text)
        self.app.router.add_post('/api/print/qr', self.print_qr_code)
        self.app.router.add_post('/api/print/calendar', self.print_calendar)
        self.app.router.add_post('/api/print/todo', self.print_todo_list)
        self.app.router.add_post('/api/preview/text', self.preview_text)
        self.app.router.add_post('/api/preview/qr', self.preview_qr_code)
        self.app.router.add_post('/api/preview/calendar', self.preview_calendar)
        self.app.router.add_post('/api/preview/todo', self.preview_todo_list)
        self.app.router.add_post('/api/rediscover', self.rediscover_printer)
        self.app.router.add_post('/api/configure_printer', self.configure_printer)
        
        # Image serving for inline display
        self.app.router.add_get('/api/image/{filename}', self.serve_image)
        
        # Home Assistant notification endpoint
        self.app.router.add_post('/api/notify', self.handle_notification)
        
        # Health check
        self.app.router.add_get('/health', self.health_check)
        
        # Static files (for potential web UI)
        self.app.router.add_get('/', self.serve_index)
    
    async def initialize_service(self):
        """Initialize the sticky print service"""
        try:
            config = self._load_config()
            self.service = StickyPrintService(config)
            await self.service.initialize()
            logger.info("Sticky Print Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration using universal config loader"""
        try:
            universal_config = UniversalConfig()
            
            # Log mode information
            if universal_config.is_ha_addon():
                logger.info("Detected Home Assistant add-on environment")
            else:
                logger.info("Running in standalone mode")
                if not universal_config.has_homeassistant_api():
                    logger.info("No Home Assistant API configured - calendar/todo features disabled")
            
            return universal_config.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return minimal default config
            return {
                'auto_discover': True,
                'manual_ip': '',
                'font_size': 48,
                'margin': 20,
                'line_spacing': 1.3,
                'calendar_entity': 'calendar.family',
                'discovery_timeout': 30,
                'ha_url': '',
                'ha_token': '',
                'port': 8099
            }
    
    # API Handlers
    
    async def get_status(self, request: web_request.Request) -> web.Response:
        """Get service status"""
        try:
            if not self.service:
                return web.json_response({
                    'error': 'Service not initialized'
                }, status=500)
            
            status = await self.service.get_status()
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return web.json_response({
                'error': str(e)
            }, status=500)
    
    async def print_text(self, request: web_request.Request) -> web.Response:
        """Print text endpoint"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            text = data.get('text', '')
            font_type = data.get('font', 'sans-serif')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'Text')
            
            if not text:
                return web.json_response({'error': 'Text is required'}, status=400)
            
            success = await self.service.print_text(text, font_type, job_name, font_size)
            
            # Get the generated image path for inline display
            image_path = None
            if success and self.service.printer:
                temp_path = self.service.printer.get_last_image_path()
                if temp_path:
                    import os
                    image_path = f"/api/image/{os.path.basename(temp_path)}"
            
            return web.json_response({
                'success': success,
                'job_name': job_name,
                'font_type': font_type,
                'image_url': image_path
            })
            
        except Exception as e:
            logger.error(f"Error printing text: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def print_qr_code(self, request: web_request.Request) -> web.Response:
        """Print QR code endpoint"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            qr_data = data.get('data', '')
            job_name = data.get('job_name', 'QRCode')
            
            if not qr_data:
                return web.json_response({'error': 'QR data is required'}, status=400)
            
            success = await self.service.print_qr_code(qr_data, job_name)
            
            # Get the generated image path for inline display
            image_path = None
            if success and self.service.printer:
                temp_path = self.service.printer.get_last_image_path()
                if temp_path:
                    import os
                    image_path = f"/api/image/{os.path.basename(temp_path)}"
            
            return web.json_response({
                'success': success,
                'job_name': job_name,
                'image_url': image_path
            })
            
        except Exception as e:
            logger.error(f"Error printing QR code: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def print_calendar(self, request: web_request.Request) -> web.Response:
        """Print calendar events endpoint"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            calendar_entity = data.get('calendar_entity')
            font_type = data.get('font', 'sans-serif')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'Calendar')
            
            success = await self.service.print_calendar_today(calendar_entity, font_type, job_name, font_size)
            
            # Get the generated image path for inline display
            image_path = None
            if success and self.service.printer:
                temp_path = self.service.printer.get_last_image_path()
                if temp_path:
                    import os
                    image_path = f"/api/image/{os.path.basename(temp_path)}"
            
            return web.json_response({
                'success': success,
                'job_name': job_name,
                'calendar_entity': calendar_entity or self.service.default_calendar,
                'image_url': image_path
            })
            
        except Exception as e:
            logger.error(f"Error printing calendar: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def print_todo_list(self, request: web_request.Request) -> web.Response:
        """Print todo list endpoint"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            todo_entity = data.get('todo_entity', '')
            font_type = data.get('font', 'console')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'TodoList')
            
            if not todo_entity:
                return web.json_response({'error': 'Todo entity is required'}, status=400)
            
            success = await self.service.print_todo_list(todo_entity, font_type, job_name, font_size)
            
            # Get the generated image path for inline display
            image_path = None
            if success and self.service.printer:
                temp_path = self.service.printer.get_last_image_path()
                if temp_path:
                    import os
                    image_path = f"/api/image/{os.path.basename(temp_path)}"
            
            return web.json_response({
                'success': success,
                'job_name': job_name,
                'todo_entity': todo_entity,
                'image_url': image_path
            })
            
        except Exception as e:
            logger.error(f"Error printing todo list: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def rediscover_printer(self, request: web_request.Request) -> web.Response:
        """Rediscover printer endpoint"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            success = await self.service.rediscover_printer()
            
            return web.json_response({
                'success': success,
                'message': 'Printer rediscovery completed' if success else 'No printer found'
            })
            
        except Exception as e:
            logger.error(f"Error rediscovering printer: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def handle_notification(self, request: web_request.Request) -> web.Response:
        """Handle Home Assistant notification"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            message = data.get('message', '')
            title = data.get('title', '')
            notification_data = data.get('data', {})
            
            if not message:
                return web.json_response({'error': 'Message is required'}, status=400)
            
            success = await self.service.handle_notification(message, title, notification_data)
            
            # Get the generated image path for inline display
            image_path = None
            if success and self.service.printer:
                temp_path = self.service.printer.get_last_image_path()
                if temp_path:
                    import os
                    image_path = f"/api/image/{os.path.basename(temp_path)}"
            
            return web.json_response({
                'success': success,
                'message': 'Notification printed' if success else 'Failed to print notification',
                'image_url': image_path
            })
            
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def preview_text(self, request: web_request.Request) -> web.Response:
        """Preview text (generate image without printing)"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            text = data.get('text', '')
            font_type = data.get('font', 'sans-serif')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'Preview')
            
            if not text:
                return web.json_response({'error': 'Text is required'}, status=400)
            
            # Generate image without printing
            image = self.service.renderer.render_text(text, font_type, font_size=font_size)
            
            # Save image for preview in a standard location
            import os
            preview_filename = "preview_text.png"  # Standard name that gets overwritten
            if not self.service.printer:
                return web.json_response({'error': 'Printer service not available'}, status=500)
            
            preview_path = os.path.join(self.service.printer.temp_dir, preview_filename)
            image.save(preview_path, 'PNG')
            
            image_url = f"/api/image/{preview_filename}"
            
            return web.json_response({
                'success': True,
                'job_name': job_name,
                'font_type': font_type,
                'font_size': font_size,
                'image_url': image_url,
                'preview_only': True
            })
            
        except Exception as e:
            logger.error(f"Error previewing text: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def preview_qr_code(self, request: web_request.Request) -> web.Response:
        """Preview QR code (generate image without printing)"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            qr_data = data.get('data', '')
            job_name = data.get('job_name', 'QR-Preview')
            
            if not qr_data:
                return web.json_response({'error': 'QR data is required'}, status=400)
            
            # Generate QR image without printing
            image = self.service.renderer.render_qr_code(qr_data)
            
            # Save image for preview in a standard location
            import os
            preview_filename = "preview_qr.png"  # Standard name that gets overwritten
            if not self.service.printer:
                return web.json_response({'error': 'Printer service not available'}, status=500)
            
            preview_path = os.path.join(self.service.printer.temp_dir, preview_filename)
            image.save(preview_path, 'PNG')
            
            image_url = f"/api/image/{preview_filename}"
            
            return web.json_response({
                'success': True,
                'job_name': job_name,
                'qr_data': qr_data,
                'image_url': image_url,
                'preview_only': True
            })
            
        except Exception as e:
            logger.error(f"Error previewing QR code: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def preview_calendar(self, request: web_request.Request) -> web.Response:
        """Preview calendar (generate image without printing)"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            calendar_entity = data.get('calendar_entity')
            font_type = data.get('font', 'sans-serif')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'Calendar-Preview')
            
            # For preview, we'll use sample calendar data if no HA connection
            if not hasattr(self.service, 'ha_api') or not self.service.ha_api or not calendar_entity:
                # Generate sample calendar preview
                sample_events = [
                    {"summary": "Sample Event 1", "start": {"dateTime": "2025-08-27T10:00:00"}},
                    {"summary": "Sample Event 2", "start": {"dateTime": "2025-08-27T14:30:00"}},
                    {"summary": "All Day Event", "start": {}}
                ]
                image = self.service.renderer.render_calendar_events(sample_events, font_type, font_size=font_size)
            else:
                events = await self.service.ha_api.get_calendar_events(calendar_entity)
                image = self.service.renderer.render_calendar_events(events, font_type, font_size=font_size)
            
            # Save image for preview in a standard location
            import os
            preview_filename = "preview_calendar.png"  # Standard name that gets overwritten
            if not self.service.printer:
                return web.json_response({'error': 'Printer service not available'}, status=500)
            
            preview_path = os.path.join(self.service.printer.temp_dir, preview_filename)
            image.save(preview_path, 'PNG')
            
            image_url = f"/api/image/{preview_filename}"
            
            return web.json_response({
                'success': True,
                'job_name': job_name,
                'font_type': font_type,
                'font_size': font_size,
                'image_url': image_url,
                'preview_only': True
            })
            
        except Exception as e:
            logger.error(f"Error previewing calendar: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def preview_todo_list(self, request: web_request.Request) -> web.Response:
        """Preview todo list (generate image without printing)"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            todo_entity = data.get('todo_entity', '')
            font_type = data.get('font', 'console')
            font_size = data.get('font_size', None)
            job_name = data.get('job_name', 'Todo-Preview')
            
            # For preview, we'll use sample todo data if no entity provided
            if not hasattr(self.service, 'ha_api') or not self.service.ha_api or not todo_entity:
                # Generate sample todo preview
                sample_todos = [
                    {"summary": "Sample Task 1", "completed": False},
                    {"summary": "Completed Task", "completed": True},
                    {"summary": "Another Task", "completed": False}
                ]
                image = self.service.renderer.render_todo_list(sample_todos, font_type, font_size=font_size)
            else:
                todos = await self.service.ha_api.get_todo_items(todo_entity)
                image = self.service.renderer.render_todo_list(todos, font_type, font_size=font_size)
            
            # Save image for preview in a standard location
            import os
            preview_filename = "preview_todo.png"  # Standard name that gets overwritten
            if not self.service.printer:
                return web.json_response({'error': 'Printer service not available'}, status=500)
            
            preview_path = os.path.join(self.service.printer.temp_dir, preview_filename)
            image.save(preview_path, 'PNG')
            
            image_url = f"/api/image/{preview_filename}"
            
            return web.json_response({
                'success': True,
                'job_name': job_name,
                'font_type': font_type,
                'font_size': font_size,
                'image_url': image_url,
                'preview_only': True
            })
            
        except Exception as e:
            logger.error(f"Error previewing todo list: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def configure_printer(self, request: web_request.Request) -> web.Response:
        """Configure printer with manual IP"""
        try:
            if not self.service:
                return web.json_response({'error': 'Service not initialized'}, status=500)
            
            data = await request.json()
            printer_ip = data.get('printer_ip', '').strip()
            port = data.get('port', 631)
            path = data.get('path', '/ipp/print')
            
            if not printer_ip:
                return web.json_response({'error': 'Printer IP is required'}, status=400)
            
            # Configure printer with manual IP
            success = await self.service.configure_manual_printer(printer_ip, port, path)
            
            return web.json_response({
                'success': success,
                'message': f'Printer configured at {printer_ip}:{port}' if success else 'Failed to configure printer'
            })
            
        except Exception as e:
            logger.error(f"Error configuring printer: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def serve_image(self, request: web_request.Request) -> web.Response:
        """Serve generated images for inline display"""
        try:
            filename = request.match_info['filename']
            
            if not self.service or not self.service.printer:
                return web.Response(status=404, text="Service not available")
            
            # Security: only allow PNG files and basic filename validation
            if not filename.endswith('.png') or '/' in filename or '..' in filename:
                return web.Response(status=400, text="Invalid filename")
            
            # Get the temp directory path
            temp_dir = self.service.printer.temp_dir
            file_path = os.path.join(temp_dir, filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                return web.Response(status=404, text="Image not found")
            
            # Serve the image
            with open(file_path, 'rb') as f:
                return web.Response(
                    body=f.read(),
                    content_type='image/png',
                    headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
                )
                
        except Exception as e:
            logger.error(f"Error serving image: {e}")
            return web.Response(status=500, text="Error serving image")
    
    async def health_check(self, request: web_request.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service_initialized': self.service is not None
        })
    
    async def serve_index(self, request: web_request.Request) -> web.Response:
        """Serve enhanced web interface with testing forms"""
        # Get current status
        try:
            status = await self.service.get_status() if self.service else {}
            printer_status = status.get('printer', {}).get('status', 'unknown')
            running_mode = 'Home Assistant Add-on' if status.get('config', {}).get('ha_url') else 'Standalone'
        except:
            printer_status = 'unknown'
            running_mode = 'Unknown'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sticky Note Printer</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
                .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }}
                .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }}
                
                .form-section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .form-section h3 {{ margin-top: 0; }}
                .form-group {{ margin: 10px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input, textarea, select {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; box-sizing: border-box; }}
                textarea {{ height: 80px; resize: vertical; }}
                button {{ background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 3px; cursor: pointer; }}
                button:hover {{ background: #0056b3; }}
                button:disabled {{ background: #ccc; cursor: not-allowed; }}
                
                .button-group {{ display: flex; gap: 10px; }}
                .button-group button[type="button"] {{ background: #6c757d; }}
                .button-group button[type="button"]:hover {{ background: #545b62; }}
                
                .api-section {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .api-section code {{ background: #e9ecef; padding: 2px 5px; border-radius: 3px; }}
                
                .result {{ margin: 10px 0; padding: 10px; border-radius: 3px; font-weight: bold; }}
                .image-preview {{ margin: 10px 0; text-align: center; }}
                .image-preview img {{ max-width: 100%; height: auto; border: 2px solid #007bff; border-radius: 5px; background: white; padding: 10px; }}
                .image-preview p {{ margin: 5px 0; font-style: italic; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🖨️ Sticky Note Printer</h1>
                
                <div class="status {'success' if printer_status == 'connected' else 'error' if printer_status == 'disconnected' else 'warning'}">
                    <h3>Service Status <button onclick="refreshStatus()" style="font-size: 12px; padding: 2px 8px;">🔄 Refresh</button></h3>
                    <p><strong>Mode:</strong> {running_mode}</p>
                    <p><strong>Printer:</strong> <span id="printer-status">{printer_status.title() if printer_status != 'unknown' else 'No Printer Configured'}</span></p>
                    <p><strong>API Endpoint:</strong> <code>/api/notify</code></p>
                    <p><strong>Status:</strong> <a href="/api/status" target="_blank">/api/status</a></p>
                </div>
                
                <!-- Quick Printer Setup - Make this prominent -->
                <div class="form-section" style="border: 2px solid #007bff; background: #f8f9ff;">
                    <h3>🖨️ Printer Setup</h3>
                    <p><em>Configure your sticky note printer to start printing!</em></p>
                    
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <button onclick="discoverPrinter()" style="flex: 1;">🔍 Auto-Discover</button>
                        <button onclick="showManualConfig()" style="flex: 1;">⚙️ Manual Setup</button>
                    </div>
                    
                    <div id="manual-config" style="display: none; padding: 15px; background: white; border: 1px solid #ddd; border-radius: 5px;">
                        <h4>Manual Printer Configuration</h4>
                        <form onsubmit="configurePrinter(event)">
                            <div style="display: flex; gap: 10px; align-items: end;">
                                <div style="flex: 1;">
                                    <label for="printer-ip">Printer IP Address:</label>
                                    <input id="printer-ip" type="text" placeholder="192.168.1.100" required>
                                </div>
                                <div style="width: 100px;">
                                    <label for="printer-port">Port:</label>
                                    <input id="printer-port" type="number" placeholder="631" value="631">
                                </div>
                                <button type="submit" style="height: 38px;">Configure</button>
                            </div>
                            <div style="margin-top: 10px;">
                                <label for="printer-path">IPP Path:</label>
                                <input id="printer-path" type="text" placeholder="/ipp/print" value="/ipp/print">
                            </div>
                        </form>
                    </div>
                    
                    <div id="printer-setup-result" class="result" style="display:none;"></div>
                </div>
                
                <!-- Test Forms -->
                <div class="form-section">
                    <h3>📝 Print Text</h3>
                    <form onsubmit="printText(event)">
                        <div class="form-group">
                            <label for="text-content">Text to Print:</label>
                            <textarea id="text-content" placeholder="Enter text to print..." required></textarea>
                        </div>
                        <div class="form-group">
                            <label for="text-font">Font:</label>
                            <select id="text-font">
                                <option value="sans-serif">Sans-serif (Clean)</option>
                                <option value="console">Console (Monospace)</option>
                                <option value="handwriting">Handwriting</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="text-font-size">Font Size:</label>
                            <select id="text-font-size">
                                <option value="small">Small (36px)</option>
                                <option value="normal" selected>Normal (48px)</option>
                                <option value="large">Large (64px)</option>
                                <option value="xlarge">X-Large (80px)</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button type="submit">Print Text</button>
                            <button type="button" onclick="previewText(event)">Preview Only</button>
                        </div>
                        <div id="text-result" class="result" style="display:none;"></div>
                    </form>
                </div>
                
                <div class="form-section">
                    <h3>📱 Print QR Code</h3>
                    <form onsubmit="printQR(event)">
                        <div class="form-group">
                            <label for="qr-data">QR Code Data:</label>
                            <input id="qr-data" type="text" placeholder="URL, text, or data..." required>
                        </div>
                        <div class="button-group">
                            <button type="submit">Print QR Code</button>
                            <button type="button" onclick="previewQR(event)">Preview Only</button>
                        </div>
                        <div id="qr-result" class="result" style="display:none;"></div>
                    </form>
                </div>
                
                <div class="form-section">
                    <h3>📅 Print Calendar Events</h3>
                    <form onsubmit="printCalendar(event)">
                        <div class="form-group">
                            <label for="calendar-entity">Calendar Entity (optional):</label>
                            <input id="calendar-entity" type="text" placeholder="calendar.family">
                        </div>
                        <div class="form-group">
                            <label for="calendar-font">Font:</label>
                            <select id="calendar-font">
                                <option value="sans-serif">Sans-serif (Clean)</option>
                                <option value="console">Console (Monospace)</option>
                                <option value="handwriting">Handwriting</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="calendar-font-size">Font Size:</label>
                            <select id="calendar-font-size">
                                <option value="small">Small (36px)</option>
                                <option value="normal" selected>Normal (48px)</option>
                                <option value="large">Large (64px)</option>
                                <option value="xlarge">X-Large (80px)</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button type="submit">Print Today's Events</button>
                            <button type="button" onclick="previewCalendar(event)">Preview Only</button>
                        </div>
                        <div id="calendar-result" class="result" style="display:none;"></div>
                    </form>
                </div>
                
                <div class="form-section">
                    <h3>✅ Print Todo List</h3>
                    <form onsubmit="printTodo(event)">
                        <div class="form-group">
                            <label for="todo-entity">Todo Entity:</label>
                            <input id="todo-entity" type="text" placeholder="todo.shopping" required>
                        </div>
                        <div class="form-group">
                            <label for="todo-font">Font:</label>
                            <select id="todo-font">
                                <option value="console" selected>Console (Monospace)</option>
                                <option value="sans-serif">Sans-serif (Clean)</option>
                                <option value="handwriting">Handwriting</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="todo-font-size">Font Size:</label>
                            <select id="todo-font-size">
                                <option value="small">Small (36px)</option>
                                <option value="normal" selected>Normal (48px)</option>
                                <option value="large">Large (64px)</option>
                                <option value="xlarge">X-Large (80px)</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button type="submit">Print Todo List</button>
                            <button type="button" onclick="previewTodo(event)">Preview Only</button>
                        </div>
                        <div id="todo-result" class="result" style="display:none;"></div>
                    </form>
                </div>
                
                
                <!-- API Documentation -->
                <div class="api-section">
                    <h3>🔌 API Endpoints</h3>
                    <ul>
                        <li><strong>POST /api/print/text</strong> - Print plain text</li>
                        <li><strong>POST /api/print/qr</strong> - Print QR codes</li>
                        <li><strong>POST /api/print/calendar</strong> - Print calendar events</li>
                        <li><strong>POST /api/print/todo</strong> - Print todo lists</li>
                        <li><strong>POST /api/notify</strong> - Home Assistant notification endpoint</li>
                        <li><strong>POST /api/rediscover</strong> - Force printer rediscovery</li>
                        <li><strong>GET /api/status</strong> - Get service status</li>
                    </ul>
                    
                    <h4>Font Types</h4>
                    <ul>
                        <li><code>sans-serif</code> - Clean, readable font (DejaVu Sans)</li>
                        <li><code>console</code> - Monospace font (DejaVu Sans Mono)</li>
                        <li><code>handwriting</code> - Handwritten-style font (Liberation Sans)</li>
                    </ul>
                </div>
                
                <footer style="text-align: center; margin-top: 30px; color: #666;">
                    <p><em>Sticky Note Printer - Universal Home Assistant Add-on & Standalone Application</em></p>
                </footer>
            </div>

            <script>
            function showResult(elementId, success, message, imageUrl = null, previewOnly = false) {{
                const result = document.getElementById(elementId);
                result.className = 'result ' + (success ? 'success' : 'error');
                
                // Clear previous content
                result.innerHTML = '';
                
                // Add message with preview indicator
                const messageElement = document.createElement('div');
                if (previewOnly && success) {{
                    messageElement.textContent = '📖 ' + message;
                }} else {{
                    messageElement.textContent = message;
                }}
                result.appendChild(messageElement);
                
                // Add image preview if available
                if (success && imageUrl) {{
                    const imagePreview = document.createElement('div');
                    imagePreview.className = 'image-preview';
                    imagePreview.innerHTML = 
                        '<p>Generated Image Preview:</p>' +
                        '<img src="' + imageUrl + '" alt="Generated sticky note preview" />';
                    result.appendChild(imagePreview);
                }}
                
                result.style.display = 'block';
                setTimeout(() => result.style.display = 'none', 10000); // Show longer for images
            }}

            async function printText(event) {{
                event.preventDefault();
                const text = document.getElementById('text-content').value;
                const font = document.getElementById('text-font').value;
                const font_size = document.getElementById('text-font-size').value;
                
                try {{
                    const response = await fetch('/api/print/text', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{text, font, font_size, job_name: 'Web-Text'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'text-result', 
                        result.success, 
                        result.success ? 'Text printed successfully!' : 'Failed to print text',
                        result.image_url
                    );
                }} catch (error) {{
                    showResult('text-result', false, 'Error: ' + error.message);
                }}
            }}

            async function printQR(event) {{
                event.preventDefault();
                const data = document.getElementById('qr-data').value;
                
                try {{
                    const response = await fetch('/api/print/qr', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{data, job_name: 'Web-QR'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'qr-result', 
                        result.success, 
                        result.success ? 'QR code printed successfully!' : 'Failed to print QR code',
                        result.image_url
                    );
                }} catch (error) {{
                    showResult('qr-result', false, 'Error: ' + error.message);
                }}
            }}

            async function printCalendar(event) {{
                event.preventDefault();
                const calendar_entity = document.getElementById('calendar-entity').value || null;
                const font = document.getElementById('calendar-font').value;
                const font_size = document.getElementById('calendar-font-size').value;
                
                try {{
                    const response = await fetch('/api/print/calendar', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{calendar_entity, font, font_size, job_name: 'Web-Calendar'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'calendar-result', 
                        result.success, 
                        result.success ? 'Calendar printed successfully!' : 'Failed to print calendar',
                        result.image_url
                    );
                }} catch (error) {{
                    showResult('calendar-result', false, 'Error: ' + error.message);
                }}
            }}

            async function printTodo(event) {{
                event.preventDefault();
                const todo_entity = document.getElementById('todo-entity').value;
                const font = document.getElementById('todo-font').value;
                const font_size = document.getElementById('todo-font-size').value;
                
                try {{
                    const response = await fetch('/api/print/todo', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{todo_entity, font, font_size, job_name: 'Web-Todo'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'todo-result', 
                        result.success, 
                        result.success ? 'Todo list printed successfully!' : 'Failed to print todo list',
                        result.image_url
                    );
                }} catch (error) {{
                    showResult('todo-result', false, 'Error: ' + error.message);
                }}
            }}

            async function discoverPrinter() {{
                try {{
                    const response = await fetch('/api/rediscover', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{}})
                    }});
                    const result = await response.json();
                    showResult('printer-setup-result', result.success, result.message || (result.success ? 'Printer discovered!' : 'No printer found'));
                    
                    // Refresh status if successful
                    if (result.success) {{
                        setTimeout(() => {{
                            refreshStatus();
                        }}, 1000);
                    }}
                }} catch (error) {{
                    showResult('printer-setup-result', false, 'Error: ' + error.message);
                }}
            }}

            function showManualConfig() {{
                const configDiv = document.getElementById('manual-config');
                if (configDiv.style.display === 'none') {{
                    configDiv.style.display = 'block';
                }} else {{
                    configDiv.style.display = 'none';
                }}
            }}

            async function refreshStatus() {{
                try {{
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    
                    const printerStatusSpan = document.getElementById('printer-status');
                    let printerStatus = 'No Printer Configured';
                    let statusClass = 'warning';
                    
                    if (status.printer && status.printer.status) {{
                        if (status.printer.status === 'connected') {{
                            printerStatus = 'Connected';
                            statusClass = 'success';
                        }} else if (status.printer.status === 'disconnected') {{
                            printerStatus = 'Disconnected';
                            statusClass = 'error';
                        }} else {{
                            printerStatus = status.printer.status;
                        }}
                    }}
                    
                    printerStatusSpan.textContent = printerStatus;
                    
                    // Update the status container class
                    const statusContainer = printerStatusSpan.closest('.status');
                    statusContainer.className = 'status ' + statusClass;
                    
                }} catch (error) {{
                    console.error('Failed to refresh status:', error);
                }}
            }}

            async function configurePrinter(event) {{
                event.preventDefault();
                const printer_ip = document.getElementById('printer-ip').value.trim();
                const port = parseInt(document.getElementById('printer-port').value) || 631;
                const path = document.getElementById('printer-path').value || '/ipp/print';
                
                if (!printer_ip) {{
                    showResult('printer-setup-result', false, 'Printer IP is required');
                    return;
                }}
                
                try {{
                    const response = await fetch('/api/configure_printer', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{printer_ip, port, path}})
                    }});
                    const result = await response.json();
                    const success = result.success;
                    const message = result.message || (success ? 'Printer configured successfully!' : 'Failed to configure printer');
                    
                    showResult('printer-setup-result', success, message);
                    
                    // Refresh status if successful
                    if (success) {{
                        setTimeout(() => {{
                            refreshStatus();
                        }}, 1000);
                    }}
                    
                }} catch (error) {{
                    showResult('printer-setup-result', false, 'Error: ' + error.message);
                }}
            }}

            // Preview functions (generate images without printing)
            async function previewText(event) {{
                event.preventDefault();
                const text = document.getElementById('text-content').value;
                const font = document.getElementById('text-font').value;
                const font_size = document.getElementById('text-font-size').value;
                
                try {{
                    const response = await fetch('/api/preview/text', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{text, font, font_size, job_name: 'Text-Preview'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'text-result', 
                        result.success, 
                        result.success ? 'Preview generated successfully!' : 'Failed to generate preview',
                        result.image_url,
                        true // preview only
                    );
                }} catch (error) {{
                    console.error('Error previewing text:', error);
                    showResult('text-result', false, 'Error: ' + error.message);
                }}
            }}

            async function previewQR(event) {{
                event.preventDefault();
                const data = document.getElementById('qr-data').value;
                
                try {{
                    const response = await fetch('/api/preview/qr', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{data, job_name: 'QR-Preview'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'qr-result', 
                        result.success, 
                        result.success ? 'QR preview generated successfully!' : 'Failed to generate QR preview',
                        result.image_url,
                        true // preview only
                    );
                }} catch (error) {{
                    console.error('Error previewing QR:', error);
                    showResult('qr-result', false, 'Error: ' + error.message);
                }}
            }}

            async function previewCalendar(event) {{
                event.preventDefault();
                const calendar_entity = document.getElementById('calendar-entity').value || null;
                const font = document.getElementById('calendar-font').value;
                const font_size = document.getElementById('calendar-font-size').value;
                
                try {{
                    const response = await fetch('/api/preview/calendar', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{calendar_entity, font, font_size, job_name: 'Calendar-Preview'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'calendar-result', 
                        result.success, 
                        result.success ? 'Calendar preview generated successfully!' : 'Failed to generate calendar preview',
                        result.image_url,
                        true // preview only
                    );
                }} catch (error) {{
                    console.error('Error previewing calendar:', error);
                    showResult('calendar-result', false, 'Error: ' + error.message);
                }}
            }}

            async function previewTodo(event) {{
                event.preventDefault();
                const todo_entity = document.getElementById('todo-entity').value;
                const font = document.getElementById('todo-font').value;
                const font_size = document.getElementById('todo-font-size').value;
                
                try {{
                    const response = await fetch('/api/preview/todo', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{todo_entity, font, font_size, job_name: 'Todo-Preview'}})
                    }});
                    const result = await response.json();
                    showResult(
                        'todo-result', 
                        result.success, 
                        result.success ? 'Todo preview generated successfully!' : 'Failed to generate todo preview',
                        result.image_url,
                        true // preview only
                    );
                }} catch (error) {{
                    console.error('Error previewing todo:', error);
                    showResult('todo-result', false, 'Error: ' + error.message);
                }}
            }}

            // Auto-refresh status every 30 seconds
            setInterval(refreshStatus, 30000);
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

async def create_app() -> web.Application:
    """Create and configure the web application"""
    server = StickyPrintServer()
    await server.initialize_service()
    return server.app

def main():
    """Main entry point"""
    logger.info("Starting Sticky Note Printer Add-on...")
    
    try:
        # Create and run the web application
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        app = loop.run_until_complete(create_app())
        
        # Get port from config
        config = UniversalConfig()
        port = config.get('port', 8099)
        
        # Run the web server
        web.run_app(
            app,
            host='0.0.0.0',
            port=port,
            access_log=logger
        )
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == '__main__':
    main()
