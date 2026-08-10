#!/bin/bash
# Script to build a Debian package for Suricata
# This creates a portable .deb file that can be installed on Ubuntu servers

set -e

echo "=== Suricata DEB Package Builder ==="
echo ""

# Check if we're on a Debian-based system
if ! command -v dpkg-buildpackage &> /dev/null; then
    echo "Error: dpkg-buildpackage not found. Install with:"
    echo "  sudo apt-get install build-essential devscripts debhelper"
    exit 1
fi

# Install build dependencies
echo "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libpcre2-dev \
    libpcap-dev \
    libnet1-dev \
    libyaml-dev \
    libjansson-dev \
    zlib1g-dev \
    libcap-ng-dev \
    libmagic-dev \
    libnetfilter-queue-dev \
    libnetfilter-log-dev \
    libnfnetlink-dev \
    libhiredis-dev \
    libevent-dev \
    libpcre3-dev \
    libssl-dev \
    rustc \
    cargo \
    python3-yaml \
    make \
    devscripts \
    debhelper \
    dh-autoreconf

# Generate configure script
echo ""
echo "Generating build files..."
./autogen.sh

# Configure for packaging
echo ""
echo "Configuring Suricata..."
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --disable-gccmarch-native \
    --enable-nfqueue \
    --enable-nflog \
    --enable-hiredis \
    --enable-geoip \
    --enable-lua

# Build
echo ""
echo "Building Suricata..."
make -j$(nproc)

# Create package structure
echo ""
echo "Creating package structure..."
PACKAGE_DIR="suricata-custom-build"
VERSION=$(grep AC_INIT configure.ac | sed 's/.*\[\([0-9.]*\).*/\1/')
ARCH=$(dpkg --print-architecture)

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/DEBIAN"
mkdir -p "$PACKAGE_DIR/usr/bin"
mkdir -p "$PACKAGE_DIR/etc/suricata"
mkdir -p "$PACKAGE_DIR/var/log/suricata"
mkdir -p "$PACKAGE_DIR/var/lib/suricata"
mkdir -p "$PACKAGE_DIR/usr/share/doc/suricata"

# Install to package directory
echo ""
echo "Installing files to package..."
make install DESTDIR="$(pwd)/$PACKAGE_DIR"

# Create control file
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: suricata-custom
Version: $VERSION
Section: net
Priority: optional
Architecture: $ARCH
Depends: libpcre2-8-0, libpcap0.8, libnet1, libyaml-0-2, libjansson4, zlib1g, libcap-ng0, libmagic1, libnetfilter-queue1, libhiredis0.14, libevent-2.1-7, libssl3
Maintainer: Custom Build <admin@localhost>
Description: Suricata IDS/IPS with PQC detection
 Custom build of Suricata with Post-Quantum Cryptography detection capabilities.
 This package includes all necessary components for network intrusion detection
 and prevention.
EOF

# Create postinst script
cat > "$PACKAGE_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Create suricata user if it doesn't exist
if ! id -u suricata > /dev/null 2>&1; then
    useradd -r -s /bin/false -d /var/lib/suricata suricata
fi

# Set permissions
chown -R suricata:suricata /var/log/suricata
chown -R suricata:suricata /var/lib/suricata
chmod 750 /var/log/suricata
chmod 750 /var/lib/suricata

echo "Suricata installed successfully!"
echo "Configuration files are in /etc/suricata/"
echo "Run 'sudo suricata -c /etc/suricata/suricata.yaml -i <interface>' to start"

exit 0
EOF

chmod 755 "$PACKAGE_DIR/DEBIAN/postinst"

# Build the package
echo ""
echo "Building DEB package..."
dpkg-deb --build "$PACKAGE_DIR" "suricata-custom_${VERSION}_${ARCH}.deb"

echo ""
echo "=== Package built successfully! ==="
echo ""
echo "Package: suricata-custom_${VERSION}_${ARCH}.deb"
echo ""
echo "To install on Ubuntu server:"
echo "  1. Copy the .deb file to your server"
echo "  2. Run: sudo dpkg -i suricata-custom_${VERSION}_${ARCH}.deb"
echo "  3. If dependencies are missing, run: sudo apt-get install -f"
echo ""
echo "To verify installation:"
echo "  suricata --version"
echo ""