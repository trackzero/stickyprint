# Sticky Note Printer - Universal Home Assistant Add-on & Standalone Application

A versatile application that enables printing notifications, QR codes, calendar events, and todo lists to IPP-compatible sticky note printers. Works both as a **Home Assistant add-on** and as a **standalone application**.

## ✨ Features

- **🔍 Auto-Discovery**: Automatically finds IPP printers on your network
- **⚙️ Manual Configuration**: Supports static IP configuration 
- **📄 Multiple Content Types**:
  - Plain text notifications with customizable fonts
  - QR codes from text or URLs
  - Today's calendar events from any Home Assistant calendar
  - Todo lists with checkboxes from Home Assistant todo integrations
- **🎨 Three Font Styles**:
  - Sans-serif: Clean, readable font (DejaVu Sans)
  - Console: Monospace font perfect for code or structured data (DejaVu Sans Mono)
  - Handwriting: Handwritten-style font for a personal touch (Liberation Sans)
- **🏠 Home Assistant Integration**: Works as a notification platform
- **🌐 RESTful API**: Direct API access for advanced automation
- **💻 Command Line Interface**: Direct printing from terminal
- **🐳 Docker Support**: Run standalone with Docker
- **🔧 Universal Configuration**: Automatically detects environment

## 🚀 Installation & Usage

### Option 1: Home Assistant Add-on

1. Add this repository to your Home Assistant Add-on Store:
   - Go to **Supervisor** → **Add-on Store** → **Menu** (⋮) → **Repositories**
   - Add: `https://github.com/your-username/ha-stickyprint-addon`

2. Install the "Sticky Note Printer" add-on

3. Configure the add-on (see Configuration section below)

4. Start the add-on

### Option 2: Standalone Python Installation

```bash
# Install via pip
pip install stickyprint

# Create example configuration
stickyprint-config config.json

# Edit the configuration file
nano config.json

# Run the server
stickyprint

# Or use CLI directly
stickyprint-cli text "Hello World!"
stickyprint-cli qr "https://example.com"
stickyprint-cli discover
```

### Option 3: Docker Standalone

```bash
# Clone repository
git clone https://github.com/your-username/stickyprint
cd stickyprint

# Copy and edit configuration
cp config.json.example config.json
nano config.json

# Run with Docker Compose
docker-compose up -d

# Or run with Docker directly
docker build -t stickyprint .
docker run -d -p 8099:8099 -v $(pwd)/config.json:/app/config.json stickyprint
```

### Option 4: Development Installation

```bash
# Clone and install in development mode
git clone https://github.com/your-username/stickyprint
cd stickyprint
pip install -e .

# Run directly
python -m src.main
```

## ⚙️ Configuration

### Home Assistant Add-on Configuration

Configure via the Home Assistant add-on interface:

```yaml
printer:
  auto_discover: true      # Automatically discover IPP printers
  manual_ip: ""           # Static IP address (if auto_discover fails)
fonts:
  default_size: 12        # Default font size (8-24)
  margin: 10             # Page margins (5-20)
  line_spacing: 1.2      # Line spacing multiplier (1.0-2.0)
calendar:
  default_entity: "calendar.family"  # Default calendar for events
discovery:
  timeout: 30            # Printer discovery timeout (10-60 seconds)
```

### Standalone Configuration

#### Configuration File (Recommended)

Create a `config.json` file:

```json
{
  "printer": {
    "auto_discover": true,
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
```

#### Environment Variables

Alternatively, use environment variables:

```bash
export STICKYPRINT_AUTO_DISCOVER=true
export STICKYPRINT_MANUAL_IP=192.168.1.100
export STICKYPRINT_FONT_SIZE=12
export STICKYPRINT_HA_URL=http://homeassistant.local:8123
export STICKYPRINT_HA_TOKEN=your_token_here
export STICKYPRINT_PORT=8099
```

### Configuration Priority

The application loads configuration in this order:
1. Configuration file (`config.json`, `config.yaml`)
2. Environment variables
3. Default values

## 💻 Usage

### Web Interface

Visit `http://localhost:8099` (or your configured port) for an interactive web interface where you can:
- Test print functions
- Configure printer settings
- View service status
- Access API documentation

### Home Assistant Notification Platform

Add to your `configuration.yaml`:

```yaml
notify:
  - name: stickyprint
    platform: rest
    resource: http://localhost:8099/api/notify
    method: POST_JSON
    title_param_name: title
    message_param_name: message
    data_param_name: data
```

Then use in automations:

```yaml
# Basic text notification
service: notify.stickyprint
data:
  message: "Hello World!"
  title: "Test Message"
  data:
    font: "sans-serif"

# QR Code notification
service: notify.stickyprint
data:
  message: "https://www.home-assistant.io"
  title: "HA Website"
  data:
    type: "qr"

# Calendar events
service: notify.stickyprint
data:
  message: ""
  title: "Today's Schedule"
  data:
    type: "calendar"
    entity: "calendar.personal"
    font: "sans-serif"

# Todo list
service: notify.stickyprint
data:
  message: ""
  title: "Shopping List"
  data:
    type: "todo"
    entity: "todo.shopping"
    font: "console"
```

### Command Line Interface

#### Basic Commands
```bash
# Print text
stickyprint-cli text "Hello World!" --font sans-serif

# Print QR code
stickyprint-cli qr "https://example.com"

# Print calendar events
stickyprint-cli calendar --entity calendar.personal

# Print todo list
stickyprint-cli todo todo.shopping --font console

# Discover printers
stickyprint-cli discover

# Check status
stickyprint-cli status

# Use custom config file
stickyprint-cli --config /path/to/config.json text "Hello"

# Verbose logging
stickyprint-cli -v discover
```

### REST API Usage

The application provides a REST API accessible at `http://localhost:8099/api/`:

#### Print Text
```bash
curl -X POST http://localhost:8099/api/print/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello World!",
    "font": "sans-serif",
    "job_name": "Test Print"
  }'
```

#### Print QR Code
```bash
curl -X POST http://localhost:8099/api/print/qr \
  -H "Content-Type: application/json" \
  -d '{
    "data": "https://www.home-assistant.io",
    "job_name": "Website QR"
  }'
```

#### Print Calendar Events
```bash
curl -X POST http://localhost:8099/api/print/calendar \
  -H "Content-Type: application/json" \
  -d '{
    "calendar_entity": "calendar.family",
    "font": "sans-serif",
    "job_name": "Today Events"
  }'
```

#### Print Todo List
```bash
curl -X POST http://localhost:8099/api/print/todo \
  -H "Content-Type: application/json" \
  -d '{
    "todo_entity": "todo.shopping",
    "font": "console",
    "job_name": "Shopping List"
  }'
```

#### Check Status
```bash
curl http://localhost:8099/api/status
```

#### Discover Printer
```bash
curl -X POST http://localhost:8099/api/rediscover
```

## Printer Requirements

This add-on is designed for IPP-compatible sticky note printers that accept:
- **Format**: BMP3, 1-bit monochrome images
- **Width**: 576 pixels (fixed)
- **Protocol**: IPP (Internet Printing Protocol)
- **File Type**: `image/reverse-encoding-bmp`

### Tested Printers
- Smart Sticky Note Printers with IPP support
- Compatible with printers using standard IPP print job submission

## 🐳 Docker Configuration

### Basic Docker Compose
```yaml
version: '3.8'
services:
  stickyprint:
    build: .
    ports:
      - "8099:8099"
    volumes:
      - ./config.json:/app/config.json:ro
    environment:
      - STICKYPRINT_AUTO_DISCOVER=true
      - STICKYPRINT_PORT=8099
```

### Host Network (Better for Printer Discovery)
```yaml
version: '3.8'
services:
  stickyprint:
    build: .
    network_mode: host
    volumes:
      - ./config.json:/app/config.json:ro
```

## 🔧 Troubleshooting

### Printer Not Found

1. **Check Network**: Ensure the printer and system are on the same network
2. **Manual IP**: If auto-discovery fails, configure the printer's IP manually
3. **Printer Status**: Check if the printer is powered on and connected to WiFi
4. **Port Access**: Ensure port 631 (IPP) is accessible on your printer
5. **Host Network**: If using Docker, try `network_mode: host` for better discovery

### Print Jobs Fail

1. **Check Logs**: Look for error messages in application logs
2. **Printer Connection**: Use the rediscover endpoint: `POST /api/rediscover` or `stickyprint-cli discover`
3. **Image Format**: Ensure the printer supports BMP3 monochrome images
4. **IPP Tools**: Verify `ipptool` and `ippfind` are installed (included in Docker)

### Fonts Not Loading

The application includes fallback fonts, but if you experience issues:
1. Check logs for font loading errors  
2. Restart the application to reload fonts
3. Use the default font type if custom fonts fail

### Home Assistant Integration Issues

1. **API Token**: Ensure your Home Assistant long-lived access token is valid
2. **URL Access**: Verify the Home Assistant URL is accessible from the application
3. **Entity Names**: Check that calendar and todo entity names exist in Home Assistant

### Environment Detection Issues

The application automatically detects if it's running as a Home Assistant add-on or standalone. If detection fails:
1. Check logs for mode detection messages
2. Manually set environment variables if needed
3. Verify configuration file format and location

## API Reference

### Endpoints

- `GET /` - Status web page
- `GET /api/status` - Service status JSON
- `GET /health` - Health check
- `POST /api/notify` - Home Assistant notification endpoint
- `POST /api/print/text` - Print text
- `POST /api/print/qr` - Print QR codes  
- `POST /api/print/calendar` - Print calendar events
- `POST /api/print/todo` - Print todo lists
- `POST /api/rediscover` - Force printer rediscovery

### Font Types

- `sans-serif` - Clean, readable font (DejaVu Sans)
- `console` - Monospace font (DejaVu Sans Mono)
- `handwriting` - Handwritten-style font (Liberation Sans)

## 🚀 Advanced Usage

### Integration Examples

#### Home Assistant Automation
```yaml
automation:
  - alias: "Morning Calendar Print"
    trigger:
      platform: time
      at: "08:00:00"
    action:
      service: notify.stickyprint
      data:
        message: ""
        data:
          type: "calendar"
          font: "sans-serif"

  - alias: "QR Code for Guest WiFi"
    trigger:
      platform: state
      entity_id: binary_sensor.doorbell
      to: "on"
    action:
      service: notify.stickyprint
      data:
        message: "WIFI:T:WPA;S:GuestNetwork;P:password123;;"
        data:
          type: "qr"
```

#### Python Script Integration
```python
import requests

# Print text
response = requests.post('http://localhost:8099/api/print/text', json={
    'text': 'Hello from Python!',
    'font': 'console',
    'job_name': 'Python-Script'
})

# Print QR code
response = requests.post('http://localhost:8099/api/print/qr', json={
    'data': 'https://example.com',
    'job_name': 'Python-QR'
})
```

### Multiple Printer Support

To use multiple printers, run multiple instances with different configurations:

```bash
# Printer 1 on port 8099
STICKYPRINT_PORT=8099 STICKYPRINT_MANUAL_IP=192.168.1.100 stickyprint &

# Printer 2 on port 8100  
STICKYPRINT_PORT=8100 STICKYPRINT_MANUAL_IP=192.168.1.101 stickyprint &
```

## 📋 Requirements

### System Requirements
- Python 3.8+
- Linux, macOS, or Windows
- Network access to IPP printer
- For Home Assistant: Home Assistant OS/Supervised

### System Dependencies
- `ipptool` and `ippfind` (CUPS client tools)
- ImageMagick (for image processing)
- Font packages (included in Docker)

### Printer Requirements
- IPP (Internet Printing Protocol) compatible
- Supports BMP3, 1-bit monochrome images
- 576 pixel width format
- Reverse-encoding BMP format

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/stickyprint/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/stickyprint/discussions)
- **Documentation**: This README and inline help (`stickyprint-cli --help`)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant community for inspiration and feedback
- CUPS project for IPP tools
- All contributors and users of this project
