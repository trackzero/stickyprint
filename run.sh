#!/usr/bin/with-contenv bashio

# Get configuration
export PRINTER_AUTO_DISCOVER=$(bashio::config 'printer.auto_discover')
export PRINTER_MANUAL_IP=$(bashio::config 'printer.manual_ip')
export FONT_SIZE=$(bashio::config 'fonts.default_size')
export FONT_MARGIN=$(bashio::config 'fonts.margin')
export FONT_LINE_SPACING=$(bashio::config 'fonts.line_spacing')
export CALENDAR_ENTITY=$(bashio::config 'calendar.default_entity')
export DISCOVERY_TIMEOUT=$(bashio::config 'discovery.timeout')

# Get Home Assistant configuration
export HASSIO_TOKEN=$SUPERVISOR_TOKEN
export HASSIO_URL="http://supervisor/core"

# Log startup
bashio::log.info "Starting Sticky Note Printer Add-on..."
bashio::log.info "Auto-discover: $PRINTER_AUTO_DISCOVER"
bashio::log.info "Manual IP: $PRINTER_MANUAL_IP"
bashio::log.info "Default calendar: $CALENDAR_ENTITY"

# Start the Python application
cd /app && python3 -m src.main
