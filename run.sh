#!/bin/sh

# Start required services for printer discovery
echo "Initializing system services for printer discovery..."

# Initialize D-Bus system
echo "Setting up D-Bus..."
mkdir -p /var/run/dbus
mkdir -p /var/lib/dbus

# Generate machine-id if it doesn't exist
if [ ! -f /var/lib/dbus/machine-id ]; then
    dbus-uuidgen > /var/lib/dbus/machine-id
fi

# Start D-Bus system daemon
echo "Starting D-Bus system daemon..."
dbus-daemon --system --fork --nopidfile

# Wait for D-Bus to be ready
sleep 1

# Setup avahi directories and permissions
echo "Setting up Avahi..."
mkdir -p /var/run/avahi-daemon
mkdir -p /etc/avahi

# Create basic avahi-daemon.conf if it doesn't exist
if [ ! -f /etc/avahi/avahi-daemon.conf ]; then
    cat > /etc/avahi/avahi-daemon.conf << 'EOF'
[server]
host-name-from-machine-id=yes
domain-name=local
browse-domains=local
use-ipv4=yes
use-ipv6=yes
allow-interfaces=
deny-interfaces=
check-response-ttl=no
use-iff-running=no
enable-dbus=yes
disallow-other-stacks=no
allow-point-to-point=no

[wide-area]
enable-wide-area=yes

[publish]
disable-publishing=no
disable-user-service-publishing=no
add-service-cookie=no
publish-addresses=yes
publish-hinfo=yes
publish-workstation=no
publish-domain=yes
publish-dns-servers=
publish-resolv-conf-dns-servers=yes
publish-aaaa-on-ipv4=yes
publish-a-on-ipv6=no

[reflector]
enable-reflector=no
reflect-ipv=no

[rlimits]
rlimit-as=
rlimit-core=0
rlimit-data=4194304
rlimit-fsize=0
rlimit-nofile=768
rlimit-stack=4194304
rlimit-nproc=3
EOF
fi

# Start Avahi daemon
echo "Starting Avahi daemon for mDNS/Bonjour discovery..."
avahi-daemon --daemonize --no-drop-root

# Wait for services to initialize
echo "Waiting for services to start..."
sleep 3

# Verify services are running
echo "Checking service status..."
if ! pgrep dbus-daemon > /dev/null; then
    echo "WARNING: D-Bus daemon may not be running properly"
fi

if ! pgrep avahi-daemon > /dev/null; then
    echo "WARNING: Avahi daemon may not be running properly"
else
    echo "Avahi daemon is running"
fi

# Test ippfind availability
echo "Testing ippfind command..."
if command -v ippfind >/dev/null 2>&1; then
    echo "ippfind command is available"
else
    echo "WARNING: ippfind command not found"
fi

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
