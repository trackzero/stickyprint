ARG BUILD_FROM=python:3.11-alpine
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    imagemagick \
    imagemagick-dev \
    cups-client \
    avahi \
    avahi-tools \
    avahi-compat-libdns_sd \
    dbus \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev

# Install fonts
RUN apk add --no-cache \
    font-dejavu \
    font-noto \
    font-opensans \
    ttf-liberation

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY run.sh .

# Make run script executable
RUN chmod +x run.sh

# Create fonts directory and symlink system fonts
RUN mkdir -p /app/fonts && \
    ln -sf /usr/share/fonts/dejavu/DejaVuSans.ttf /app/fonts/sans-serif.ttf && \
    ln -sf /usr/share/fonts/dejavu/DejaVuSansMono.ttf /app/fonts/console.ttf && \
    ln -sf /usr/share/fonts/liberation/LiberationSans-Regular.ttf /app/fonts/handwriting.ttf

# Expose port
EXPOSE 8099

# Run
CMD ["./run.sh"]
