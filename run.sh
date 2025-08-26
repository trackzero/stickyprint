#!/bin/bash

# Detect if running in Home Assistant environment
if [ -n "$SUPERVISOR_TOKEN" ] && command -v bashio >/dev/null 2>&1; then
    echo "Detected Home Assistant add-on environment"
    
    # Get configuration from Home Assistant
    export PRINTER_AUTO_DISCOVER=$(bashio::config 'printer.auto_discover')
    export PRINTER_MANUAL_IP=$(bashio::config 'printer.manual_ip')
    export FONT_SIZE=$(bashio::config 'fonts.default_size')
    export FONT_MARGIN=$(bashio::config 'fonts.margin')
    export FONT_LINE_SPACING=$(bashio::config 'fonts.line_spacing')
    export CALENDAR_ENTITY=$(bashio::config 'calendar.default_entity')
    export DISCOVERY_TIMEOUT=$(bashio::config 'discovery.timeout')
    
    # Set Home Assistant API configuration
    export HASSIO_TOKEN=$SUPERVISOR_TOKEN
    export HASSIO_URL="http://supervisor/core"
    
    # Log startup with bashio
    bashio::log.info "Starting Sticky Note Printer Add-on..."
    bashio::log.info "Auto-discover: $PRINTER_AUTO_DISCOVER"
    bashio::log.info "Manual IP: $PRINTER_MANUAL_IP"
    bashio::log.info "Default calendar: $CALENDAR_ENTITY"
else
    echo "Running in standalone mode"
    echo "Configuration will be loaded from config file or environment variables"
fi

# Start the Python application
cd /app && python3 -m src.main
