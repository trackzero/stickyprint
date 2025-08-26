import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Configuration loading error"""
    pass

class UniversalConfig:
    """Universal configuration loader that works in both HA add-on and standalone modes"""
    
    def __init__(self):
        self.mode = self._detect_mode()
        self.config = self._load_config()
        logger.info(f"Running in {self.mode} mode")
    
    def _detect_mode(self) -> str:
        """Detect if running as Home Assistant add-on or standalone"""
        # Check for Home Assistant supervisor environment
        if (os.getenv('SUPERVISOR_TOKEN') and 
            os.path.exists('/data/options.json')):
            return "ha_addon"
        
        # Check for bashio (HA add-on tool)
        try:
            import subprocess
            result = subprocess.run(['bashio', '--version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return "ha_addon"
        except:
            pass
            
        return "standalone"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on detected mode"""
        if self.mode == "ha_addon":
            return self._load_ha_addon_config()
        else:
            return self._load_standalone_config()
    
    def _load_ha_addon_config(self) -> Dict[str, Any]:
        """Load Home Assistant add-on configuration"""
        try:
            # Try to load from /data/options.json (standard HA add-on path)
            if os.path.exists('/data/options.json'):
                with open('/data/options.json', 'r') as f:
                    options = json.load(f)
                    logger.info("Loaded HA add-on config from /data/options.json")
                    return self._normalize_ha_config(options)
            
            # Fallback to environment variables (set by run.sh)
            return self._load_from_environment(ha_mode=True)
            
        except Exception as e:
            logger.error(f"Error loading HA add-on config: {e}")
            # Fallback to environment variables
            return self._load_from_environment(ha_mode=True)
    
    def _load_standalone_config(self) -> Dict[str, Any]:
        """Load standalone configuration from file or environment"""
        config_sources = [
            'config.json',
            '/app/config.json',
            '/config/config.json',
            './config.json'
        ]
        
        # Try to load from config files
        for config_path in config_sources:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        logger.info(f"Loaded standalone config from {config_path}")
                        return self._normalize_standalone_config(config)
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
                    continue
        
        # Try YAML config files
        yaml_sources = [
            'config.yaml',
            'config.yml',
            '/app/config.yaml',
            '/config/config.yaml'
        ]
        
        for config_path in yaml_sources:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        logger.info(f"Loaded standalone config from {config_path}")
                        return self._normalize_standalone_config(config)
                except Exception as e:
                    logger.warning(f"Failed to load YAML config from {config_path}: {e}")
                    continue
        
        # Fallback to environment variables
        logger.info("No config file found, using environment variables")
        return self._load_from_environment(ha_mode=False)
    
    def _normalize_ha_config(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Home Assistant add-on config to standard format"""
        return {
            'auto_discover': options.get('printer', {}).get('auto_discover', True),
            'manual_ip': options.get('printer', {}).get('manual_ip', ''),
            'font_size': options.get('fonts', {}).get('default_size', 12),
            'margin': options.get('fonts', {}).get('margin', 10),
            'line_spacing': options.get('fonts', {}).get('line_spacing', 1.2),
            'calendar_entity': options.get('calendar', {}).get('default_entity', 'calendar.family'),
            'discovery_timeout': options.get('discovery', {}).get('timeout', 30),
            'ha_url': 'http://supervisor/core',
            'ha_token': os.getenv('SUPERVISOR_TOKEN', ''),
            'port': 8099
        }
    
    def _normalize_standalone_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize standalone config to standard format"""
        # Handle both flat and nested config structures
        if 'printer' in config:
            # Nested structure (similar to HA add-on)
            return {
                'auto_discover': config.get('printer', {}).get('auto_discover', True),
                'manual_ip': config.get('printer', {}).get('manual_ip', ''),
                'font_size': config.get('fonts', {}).get('default_size', 12),
                'margin': config.get('fonts', {}).get('margin', 10),
                'line_spacing': config.get('fonts', {}).get('line_spacing', 1.2),
                'calendar_entity': config.get('calendar', {}).get('default_entity', 'calendar.family'),
                'discovery_timeout': config.get('discovery', {}).get('timeout', 30),
                'ha_url': config.get('homeassistant', {}).get('url', ''),
                'ha_token': config.get('homeassistant', {}).get('token', ''),
                'port': config.get('server', {}).get('port', 8099)
            }
        else:
            # Flat structure
            return {
                'auto_discover': config.get('auto_discover', True),
                'manual_ip': config.get('manual_ip', ''),
                'font_size': config.get('font_size', 12),
                'margin': config.get('margin', 10),
                'line_spacing': config.get('line_spacing', 1.2),
                'calendar_entity': config.get('calendar_entity', 'calendar.family'),
                'discovery_timeout': config.get('discovery_timeout', 30),
                'ha_url': config.get('ha_url', ''),
                'ha_token': config.get('ha_token', ''),
                'port': config.get('port', 8099)
            }
    
    def _load_from_environment(self, ha_mode: bool = False) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        if ha_mode:
            # Use HA add-on environment variable names
            return {
                'auto_discover': os.getenv('PRINTER_AUTO_DISCOVER', 'true').lower() == 'true',
                'manual_ip': os.getenv('PRINTER_MANUAL_IP', ''),
                'font_size': int(os.getenv('FONT_SIZE', '12')),
                'margin': int(os.getenv('FONT_MARGIN', '10')),
                'line_spacing': float(os.getenv('FONT_LINE_SPACING', '1.2')),
                'calendar_entity': os.getenv('CALENDAR_ENTITY', 'calendar.family'),
                'discovery_timeout': int(os.getenv('DISCOVERY_TIMEOUT', '30')),
                'ha_url': os.getenv('HASSIO_URL', 'http://supervisor/core'),
                'ha_token': os.getenv('HASSIO_TOKEN', ''),
                'port': int(os.getenv('PORT', '8099'))
            }
        else:
            # Use generic environment variable names for standalone
            return {
                'auto_discover': os.getenv('STICKYPRINT_AUTO_DISCOVER', 'true').lower() == 'true',
                'manual_ip': os.getenv('STICKYPRINT_MANUAL_IP', ''),
                'font_size': int(os.getenv('STICKYPRINT_FONT_SIZE', '12')),
                'margin': int(os.getenv('STICKYPRINT_MARGIN', '10')),
                'line_spacing': float(os.getenv('STICKYPRINT_LINE_SPACING', '1.2')),
                'calendar_entity': os.getenv('STICKYPRINT_CALENDAR_ENTITY', 'calendar.family'),
                'discovery_timeout': int(os.getenv('STICKYPRINT_DISCOVERY_TIMEOUT', '30')),
                'ha_url': os.getenv('STICKYPRINT_HA_URL', ''),
                'ha_token': os.getenv('STICKYPRINT_HA_TOKEN', ''),
                'port': int(os.getenv('STICKYPRINT_PORT', '8099'))
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def is_ha_addon(self) -> bool:
        """Check if running as Home Assistant add-on"""
        return self.mode == "ha_addon"
    
    def is_standalone(self) -> bool:
        """Check if running in standalone mode"""
        return self.mode == "standalone"
    
    def has_homeassistant_api(self) -> bool:
        """Check if Home Assistant API is available"""
        return bool(self.config.get('ha_url') and self.config.get('ha_token'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary"""
        return self.config.copy()
    
    def create_example_config(self, path: str = "config.json.example"):
        """Create an example configuration file for standalone usage"""
        example_config = {
            "printer": {
                "auto_discover": True,
                "manual_ip": "192.168.1.100"
            },
            "fonts": {
                "default_size": 12,
                "margin": 10,
                "line_spacing": 1.2
            },
            "calendar": {
                "default_entity": "calendar.family"
            },
            "discovery": {
                "timeout": 30
            },
            "homeassistant": {
                "url": "http://homeassistant.local:8123",
                "token": "your_long_lived_access_token_here"
            },
            "server": {
                "port": 8099
            }
        }
        
        try:
            with open(path, 'w') as f:
                json.dump(example_config, f, indent=2)
            logger.info(f"Created example config file: {path}")
        except Exception as e:
            logger.error(f"Failed to create example config: {e}")

def create_example_config_cli():
    """CLI entry point for creating example config"""
    import sys
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "config.json"
    
    config = UniversalConfig()
    config.create_example_config(path)
    print(f"Created example configuration file: {path}")
    print(f"Edit this file and then run: stickyprint")
