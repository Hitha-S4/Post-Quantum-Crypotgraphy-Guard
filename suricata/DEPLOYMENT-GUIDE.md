# Suricata Deployment Guide for Ubuntu Server

## Overview

This guide explains how to create a deployable executable/package for Suricata that can be copied to an Ubuntu server.

## ⚠️ Important Considerations

Suricata is a **complex network security application** with many system dependencies. Unlike simple Go or Rust applications that can be compiled into a single static binary, Suricata requires:

- System libraries (libpcap, libyaml, libjansson, etc.)
- Kernel modules for packet capture
- Configuration files
- Rule files
- Proper permissions (runs as root or with CAP_NET_RAW)

## Deployment Options

### Option 1: DEB Package (Recommended) ✅

Create a `.deb` package that can be easily installed on any Ubuntu server.

**Steps:**

1. **On your build machine (Ubuntu):**
   ```bash
   chmod +x build-deb-package.sh
   ./build-deb-package.sh
   ```

2. **This creates:** `suricata-custom_<version>_<arch>.deb`

3. **Copy to Ubuntu server:**
   ```bash
   scp suricata-custom_*.deb user@server:/tmp/
   ```

4. **Install on server:**
   ```bash
   ssh user@server
   sudo dpkg -i /tmp/suricata-custom_*.deb
   sudo apt-get install -f  # Install any missing dependencies
   ```

**Advantages:**
- ✅ Handles dependencies automatically
- ✅ Proper system integration
- ✅ Easy to install/uninstall
- ✅ Standard Ubuntu package management

### Option 2: Portable Binary Bundle

Create a self-contained directory with the binary and dependencies.

**Steps:**

1. **Build Suricata:**
   ```bash
   ./autogen.sh
   ./configure --prefix=/opt/suricata --disable-gccmarch-native
   make -j$(nproc)
   sudo make install DESTDIR=/tmp/suricata-bundle
   ```

2. **Create bundle:**
   ```bash
   cd /tmp/suricata-bundle
   tar czf suricata-bundle.tar.gz opt/
   ```

3. **Copy to server:**
   ```bash
   scp suricata-bundle.tar.gz user@server:/tmp/
   ```

4. **Extract on server:**
   ```bash
   ssh user@server
   cd /
   sudo tar xzf /tmp/suricata-bundle.tar.gz
   ```

5. **Install dependencies on server:**
   ```bash
   sudo apt-get install libpcre2-8-0 libpcap0.8 libnet1 libyaml-0-2 \
       libjansson4 zlib1g libcap-ng0 libmagic1 libnetfilter-queue1 \
       libhiredis0.14 libevent-2.1-7 libssl3
   ```

**Advantages:**
- ✅ More control over installation location
- ✅ Can bundle custom configurations

**Disadvantages:**
- ❌ Manual dependency management
- ❌ No automatic updates
- ❌ Requires manual system integration

### Option 3: Docker Container 🐳

Package Suricata in a Docker container for maximum portability.

**Create Dockerfile:**
```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    libpcre2-8-0 libpcap0.8 libnet1 libyaml-0-2 \
    libjansson4 zlib1g libcap-ng0 libmagic1 \
    libnetfilter-queue1 libhiredis0.14 libevent-2.1-7 \
    libssl3 && \
    rm -rf /var/lib/apt/lists/*

COPY suricata-bundle/opt/suricata /opt/suricata
COPY etc/suricata.yaml /etc/suricata/
COPY rules/ /etc/suricata/rules/

ENTRYPOINT ["/opt/suricata/bin/suricata"]
CMD ["-c", "/etc/suricata/suricata.yaml", "-i", "eth0"]
```

**Build and deploy:**
```bash
docker build -t suricata-custom .
docker save suricata-custom | gzip > suricata-custom.tar.gz
# Copy to server and load
docker load < suricata-custom.tar.gz
```

**Advantages:**
- ✅ Maximum portability
- ✅ Isolated environment
- ✅ Easy version management

**Disadvantages:**
- ❌ Requires Docker on server
- ❌ Network mode complexity for packet capture
- ❌ Performance overhead

## Quick Start: Using the DEB Package Builder

The easiest method is using the provided script:

```bash
# 1. Make script executable
chmod +x build-deb-package.sh

# 2. Build the package (requires Ubuntu/Debian)
./build-deb-package.sh

# 3. Copy to server
scp suricata-custom_*.deb user@ubuntu-server:/tmp/

# 4. Install on server
ssh user@ubuntu-server
sudo dpkg -i /tmp/suricata-custom_*.deb
sudo apt-get install -f

# 5. Verify installation
suricata --version

# 6. Copy your configuration and rules
sudo cp -r /path/to/your/rules/* /etc/suricata/rules/
sudo cp /path/to/your/suricata.yaml /etc/suricata/

# 7. Run Suricata
sudo suricata -c /etc/suricata/suricata.yaml -i eth0
```

## System Requirements

**Build Machine:**
- Ubuntu 20.04+ or Debian 11+
- 4GB RAM minimum
- Build tools (gcc, make, autotools)
- Rust toolchain

**Target Server:**
- Ubuntu 20.04+ (same or newer than build machine)
- 2GB RAM minimum
- Network interface for monitoring
- Root access or CAP_NET_RAW capability

## Files to Include in Deployment

When deploying, ensure you include:

1. **Binary:** `/usr/bin/suricata` (or `/opt/suricata/bin/suricata`)
2. **Configuration:** `/etc/suricata/suricata.yaml`
3. **Rules:** `/etc/suricata/rules/*.rules`
4. **Classification:** `/etc/suricata/classification.config`
5. **Reference:** `/etc/suricata/reference.config`
6. **Threshold:** `/etc/suricata/threshold.config`

## Testing Your Deployment

After installation on the server:

```bash
# Check version
suricata --version

# Test configuration
sudo suricata -T -c /etc/suricata/suricata.yaml

# List available interfaces
ip link show

# Run in test mode
sudo suricata -c /etc/suricata/suricata.yaml -i eth0 --init-errors-fatal
```

## Troubleshooting

### Missing Dependencies
```bash
# Check missing libraries
ldd /usr/bin/suricata

# Install missing packages
sudo apt-get install -f
```

### Permission Issues
```bash
# Grant capabilities instead of running as root
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/suricata
```

### Version Mismatch
- Build on the **same or older** Ubuntu version as your target server
- Use `--disable-gccmarch-native` flag to avoid CPU-specific optimizations

## Best Practices

1. **Build on matching OS:** Build on Ubuntu 20.04 if deploying to Ubuntu 20.04
2. **Test locally first:** Test the package on a local VM before production
3. **Include all configs:** Bundle your custom rules and configurations
4. **Document dependencies:** Keep a list of required system packages
5. **Version control:** Tag your builds with version numbers
6. **Security:** Keep Suricata and rules updated regularly

## Conclusion

For Ubuntu server deployment, the **DEB package method** (Option 1) is strongly recommended as it:
- Handles dependencies automatically
- Integrates properly with the system
- Follows Ubuntu best practices
- Makes updates and removal easy

Use the provided `build-deb-package.sh` script to get started quickly!