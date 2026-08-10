# Suricata Installation Guide

Complete guide to building and installing Suricata 9.0.0-dev from source on macOS.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps](#next-steps)

---

## Prerequisites

### Required Tools

- **Xcode Command Line Tools** (for compiler and build tools)
- **Homebrew** (package manager for macOS)
- **Git** (for cloning the repository)

### Install Xcode Command Line Tools

```bash
xcode-select --install
```

### Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## System Requirements

- **Operating System:** macOS 10.15+ (tested on macOS Sequoia)
- **Architecture:** Intel or Apple Silicon (M1/M2/M3)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 2GB for source + dependencies
- **Network:** Internet connection for downloading dependencies

---

## Installation Steps

### Step 1: Install Build Dependencies

Install all required build tools and libraries:

```bash
brew install libtool automake autoconf pkg-config rust pcre2 libyaml jansson libmagic libpcap lz4 libmaxminddb hiredis
```

**Packages Explained:**

- `libtool`, `automake`, `autoconf` - Build system tools
- `pkg-config` - Dependency detection
- `rust` - Rust compiler (required for Rust components)
- `pcre2` - Perl Compatible Regular Expressions
- `libyaml` - YAML parser
- `jansson` - JSON library
- `libmagic` - File type detection
- `libpcap` - Packet capture library
- `lz4` - Compression library
- `libmaxminddb` - GeoIP2 database library (for geographic IP lookups)
- `hiredis` - Redis client library (for Redis support)

**Note:** `libnet` is not available via Homebrew on macOS. If you need libnet support, you'll need to build it from source or configure without it.

### Step 2: Install Rust Tools

Install `cbindgen` for generating C bindings from Rust:

```bash
cargo install cbindgen
```

### Step 3: Clone Suricata Repository

If you haven't already cloned the repository:

```bash
git clone https://github.com/OISF/suricata.git
cd suricata
```

### Step 4: Generate Build Files

Run the autogen script to generate configure script:

```bash
./autogen.sh
```

**Expected Output:**

```
Running autoreconf -fv --install
autoreconf: Entering directory `.'
autoreconf: configure.ac: tracing
...
autoreconf: Leaving directory `.'
```

### Step 5: Configure Build

Set up environment variables for Homebrew libraries:

```bash
export PKG_CONFIG_PATH="/opt/homebrew/opt/libyaml/lib/pkgconfig:/opt/homebrew/opt/jansson/lib/pkgconfig:/opt/homebrew/opt/libmagic/lib/pkgconfig:/opt/homebrew/opt/libpcap/lib/pkgconfig:/opt/homebrew/opt/pcre2/lib/pkgconfig:/opt/homebrew/opt/lz4/lib/pkgconfig:/opt/homebrew/opt/libmaxminddb/lib/pkgconfig:/opt/homebrew/opt/hiredis/lib/pkgconfig:$PKG_CONFIG_PATH"

export CPPFLAGS="-I/opt/homebrew/opt/libyaml/include -I/opt/homebrew/opt/jansson/include -I/opt/homebrew/opt/libmagic/include -I/opt/homebrew/opt/libpcap/include -I/opt/homebrew/opt/pcre2/include -I/opt/homebrew/opt/lz4/include -I/opt/homebrew/opt/libmaxminddb/include -I/opt/homebrew/opt/hiredis/include"

export LDFLAGS="-L/opt/homebrew/opt/libyaml/lib -L/opt/homebrew/opt/jansson/lib -L/opt/homebrew/opt/libmagic/lib -L/opt/homebrew/opt/libpcap/lib -L/opt/homebrew/opt/pcre2/lib -L/opt/homebrew/opt/lz4/lib -L/opt/homebrew/opt/libmaxminddb/lib -L/opt/homebrew/opt/hiredis/lib"
```

Run configure with recommended options:

**Option A: Full features (with GeoIP2 and Redis):**
```bash
./configure --enable-rust --enable-lua --enable-geoip --enable-hiredis --disable-gccmarch-native
```

**Option B: Minimal features (without GeoIP2 and Redis):**
```bash
./configure --enable-rust --enable-lua --disable-gccmarch-native
```

**Option C: With GeoIP2 only (no Redis):**
```bash
./configure --enable-rust --enable-lua --enable-geoip --disable-gccmarch-native
```

**Configuration Options:**

- `--enable-rust` - Enable Rust components (required)
- `--enable-lua` - Enable Lua scripting support
- `--enable-geoip` - Enable GeoIP2 support (requires libmaxminddb)
- `--enable-hiredis` - Enable Redis support (requires hiredis)
- `--enable-nfqueue` - Enable NFQUEUE support (Linux only, not available on macOS)
- `--disable-gccmarch-native` - Disable CPU-specific optimizations (better compatibility)

**Note:**
- If you encounter errors about missing `libmaxminddb`, install it: `brew install libmaxminddb` or remove `--enable-geoip`
- If you encounter errors about missing `hiredis`, install it: `brew install hiredis` or remove `--enable-hiredis`
- `--enable-nfqueue` is not supported on macOS (Linux only), so it's been removed from the recommended options

**Expected Output (end):**

```
Suricata Configuration:
  AF_PACKET support:                       yes
  eBPF support:                            no
  XDP support:                             no
  PF_RING support:                         no
  NFQueue support:                         yes
  NFLOG support:                           no
  IPFW support:                            no
  Netmap support:                          no
  DAG enabled:                             no
  Napatech enabled:                        no
  WinDivert enabled:                       no
  DPDK support:                            no

  Unix socket enabled:                     yes
  Detection enabled:                       yes

  Libmagic support:                        yes
  libnss support:                          no
  libnspr support:                         no
  libjansson support:                      yes
  hiredis support:                         yes
  hiredis async with libevent:             yes
  PCRE jit:                                yes
  LUA support:                             yes
  libluajit:                               no
  GeoIP2 support:                          yes
  Non-bundled htp:                         no
  Hyperscan support:                       no
  Libnet support:                          yes
  liblz4 support:                          yes
  Landlock support:                        no
  Rust support (experimental):             yes
  Rust strict mode:                        no
  Rust compiler path:                      /opt/homebrew/bin/rustc
  Rust compiler version:                   rustc 1.84.0
  Cargo path:                              /opt/homebrew/bin/cargo
  Cargo version:                           cargo 1.84.0

  Python support:                          yes
  Python path:                             /opt/homebrew/opt/python@3.13/bin/python3.13
  Install suricatactl:                     yes
  Install suricatasc:                      yes
  Install suricata-update:                 yes

  Profiling enabled:                       no
  Profiling locks enabled:                 no
  Profiling rules enabled:                 no

  Plugin support (experimental):           yes

  Development settings:
    Coccinelle / spatch:                   no
    Unit tests enabled:                    no
    Debug output enabled:                  no
    Debug validation enabled:              no

  Generic build parameters:
    Installation prefix:                   /usr/local
    Configuration directory:               /usr/local/etc/suricata/
    Log directory:                         /usr/local/var/log/suricata/

    --prefix                               /usr/local
    --sysconfdir                           /usr/local/etc
    --localstatedir                        /usr/local/var
    --datarootdir                          /usr/local/share

    Host:                                  aarch64-apple-darwin24.2.0
    Compiler:                              clang (exec name) / clang (real)
    GCC Protect enabled:                   no
    GCC march native enabled:              no
    GCC Profile enabled:                   no
    Position Independent Executable enabled: no
    CFLAGS                                 -g -O2 -std=c11 -march=native -I${srcdir}/../rust/gen -I${srcdir}/../rust/dist
    PCAP_CFLAGS                             -I/opt/homebrew/opt/libpcap/include
    SECCFLAGS
```

### Step 6: Build Suricata

Compile the source code (this may take 10-20 minutes):

```bash
make -j$(sysctl -n hw.ncpu)
```

**Note:** The `-j$(sysctl -n hw.ncpu)` flag uses all CPU cores for faster compilation.

**Expected Output (end):**

```
Making all in rust
  CARGO_TARGET_DIR=../../rust/target cargo build --release --features strict
   Compiling suricata-9.0.0-dev
    Finished release [optimized] target(s) in 5m 23s
...
make[2]: Nothing to be done for `all-am'.
```

### Step 7: Install Suricata (Optional)

To install system-wide:

```bash
sudo make install
```

**Or run from source directory** (recommended for development):

```bash
./src/suricata --version
```

---

## Configuration

### Step 1: Create Required Directories

```bash
mkdir -p logs etc
```

### Step 2: Copy Configuration Files

```bash
# Copy main configuration
cp suricata.yaml.in suricata.yaml

# Copy classification and reference files
cp classification.config etc/
cp reference.config etc/
```

### Step 3: Modify Configuration

Edit `suricata.yaml` and update these key settings:

```yaml
# Line 62: Change log directory
default-log-dir: logs/

# Line 2313: Change rule path
default-rule-path: .

# Line 2315: Set rule files
rule-files:
  - signatures.rules

# Line 2322-2323: Set classification and reference paths
classification-file: etc/classification.config
reference-config-file: etc/reference.config

# Line 1410: Disable unix socket (optional, to avoid permission issues)
unix-command:
  enabled: no
```

### Step 4: Create Detection Rules

Create `signatures.rules`:

```bash
cat > signatures.rules << 'EOF'
# Test Rules for Suricata
alert icmp any any -> any any (msg:"ICMP Packet Detected"; sid:1000001; rev:1;)
alert tcp any any -> any any (msg:"TCP Connection Detected"; sid:1000002; rev:1;)
alert udp any any -> any any (msg:"UDP Packet Detected"; sid:1000003; rev:1;)
alert http any any -> any any (msg:"HTTP Request Detected"; sid:1000004; rev:1;)
EOF
```

---

## Verification

### Test 1: Check Version

```bash
./src/suricata --version
```

**Expected Output:**

```
This is Suricata version 9.0.0-dev RELEASE
Features: PCAP_SET_BUFF LIBPCAP_VERSION_MAJOR=1 AF_PACKET HAVE_PACKET_FANOUT LIBCAP_NG LIBNET1.1 HAVE_HTP_URI_NORMALIZE_HOOK PCRE2 HAVE_LIBJANSSON HAVE_LIBMAGIC RUST HAVE_LUA HAVE_LIBHIREDIS HAVE_LIBEVENT
SIMD support: none
Atomic intrinsics: 1 2 4 8 16 byte(s)
64-bits, Little-endian architecture
GCC version 4.2.1 Compatible Apple LLVM 16.0.0 (clang-1600.0.26.6), C version 201112
compiled with -fstack-protector
L1 cache line size (CLS)=64
compiled with LibHTP v0.5.49, linked against LibHTP v0.5.49
Suricata Configuration:
  AF_PACKET support:                       yes
  eBPF support:                            no
  XDP support:                             no
  PF_RING support:                         no
  NFQueue support:                         yes
  NFLOG support:                           no
  IPFW support:                            no
  Netmap support:                          no
  DAG enabled:                             no
  Napatech enabled:                        no
  WinDivert enabled:                       no
  DPDK support:                            no

  Unix socket enabled:                     yes
  Detection enabled:                       yes

  Libmagic support:                        yes
  libnss support:                          no
  libnspr support:                         no
  libjansson support:                      yes
  hiredis support:                         yes
  hiredis async with libevent:             yes
  PCRE jit:                                yes
  LUA support:                             yes
  libluajit:                               no
  GeoIP2 support:                          yes
  Non-bundled htp:                         no
  Hyperscan support:                       no
  Libnet support:                          yes
  liblz4 support:                          yes
  Landlock support:                        no
  Rust support (experimental):             yes
  Rust strict mode:                        no
  Rust compiler path:                      /opt/homebrew/bin/rustc
  Rust compiler version:                   rustc 1.84.0
  Cargo path:                              /opt/homebrew/bin/cargo
  Cargo version:                           cargo 1.84.0

  Python support:                          yes
  Python path:                             /opt/homebrew/opt/python@3.13/bin/python3.13
  Install suricatactl:                     yes
  Install suricatasc:                      yes
  Install suricata-update:                 yes

  Profiling enabled:                       no
  Profiling locks enabled:                 no
  Profiling rules enabled:                 no

  Plugin support (experimental):           yes

  Development settings:
    Coccinelle / spatch:                   no
    Unit tests enabled:                    no
    Debug output enabled:                  no
    Debug validation enabled:              no

  Generic build parameters:
    Installation prefix:                   /usr/local
    Configuration directory:               /usr/local/etc/suricata/
    Log directory:                         /usr/local/var/log/suricata/

    --prefix                               /usr/local
    --sysconfdir                           /usr/local/etc
    --localstatedir                        /usr/local/var
    --datarootdir                          /usr/local/share

    Host:                                  aarch64-apple-darwin24.2.0
    Compiler:                              clang (exec name) / clang (real)
    GCC Protect enabled:                   no
    GCC march native enabled:              no
    GCC Profile enabled:                   no
    Position Independent Executable enabled: no
    CFLAGS                                 -g -O2 -std=c11 -march=native -I${srcdir}/../rust/gen -I${srcdir}/../rust/dist
    PCAP_CFLAGS                             -I/opt/homebrew/opt/libpcap/include
    SECCFLAGS
```

### Test 2: Check Configuration

```bash
./src/suricata -T -c suricata.yaml -v
```

**Expected Output (end):**

```
[i] suricata: Configuration provided was successfully loaded. Exiting.
```

### Test 3: List Network Interfaces

```bash
./src/suricata --list-runmodes
```

**Expected Output:**

```
Available runmodes:
  - workers: Workers runmode, each thread does all tasks from acquisition to logging
  - autofp: Auto-FP runmode, each thread does all tasks from acquisition to logging
  - single: Single threaded runmode
```

### Test 4: Run Basic Test

```bash
sudo ./src/suricata -c suricata.yaml -i en0 -v
```

Press `Ctrl+C` after a few seconds. Check logs:

```bash
cat logs/fast.log
```

You should see detected packets!

---

## Troubleshooting

### Issue: `configure: error: libyaml not found`

**Solution:** Set PKG_CONFIG_PATH and CPPFLAGS/LDFLAGS as shown in Step 5.

### Issue: `ERROR! libmaxminddb GeoIP2 library not found`

**Solution 1:** Install libmaxminddb:
```bash
brew install libmaxminddb
```

Then update environment variables to include libmaxminddb paths (see Step 5).

**Solution 2:** Configure without GeoIP2:
```bash
./configure --enable-rust --enable-lua --enable-nfqueue --enable-hiredis --disable-gccmarch-native
```
(Remove `--enable-geoip` from the configure command)

### Issue: `ERROR! libmaxminddb GeoIP2 library not found`

**Solution 1:** Install libmaxminddb:
```bash
brew install libmaxminddb
```

Then update environment variables to include libmaxminddb paths (see Step 5).

**Solution 2:** Configure without GeoIP2:
```bash
./configure --enable-rust --enable-lua --disable-gccmarch-native
```
(Remove `--enable-geoip` from the configure command)

### Issue: `ERROR! libhiredis library not found`

**Solution 1:** Install hiredis:
```bash
brew install hiredis
```

Then update environment variables to include hiredis paths (see Step 5).

**Solution 2:** Configure without Redis support:
```bash
./configure --enable-rust --enable-lua --enable-geoip --disable-gccmarch-native
```
(Remove `--enable-hiredis` from the configure command)

### Issue: `libnet.h version 1.1.x not found`

**Solution:** libnet is not available via Homebrew on macOS. Configure without libnet support (it's optional):
```bash
./configure --enable-rust --enable-lua --enable-geoip --enable-hiredis --disable-gccmarch-native
```
Suricata will build successfully without libnet - it's only needed for specific packet injection features.

### Issue: `cbindgen: command not found`

**Solution:**

```bash
cargo install cbindgen
```

### Issue: `Permission denied` when running Suricata

**Solution:** Run with sudo:

```bash
sudo ./src/suricata -c suricata.yaml -i en0
```

### Issue: `unix-command: failed to create socket`

**Solution:** Disable unix-command in suricata.yaml:

```yaml
unix-command:
  enabled: no
```

### Issue: `classification.config not found`

**Solution:** Copy files to etc/ directory:

```bash
mkdir -p etc
cp classification.config etc/
cp reference.config etc/
```

### Issue: Build fails with Rust errors

**Solution:** Update Rust:

```bash
rustup update
cargo install cbindgen --force
```

### Issue: `make: *** No targets specified and no makefile found`

**Solution:** Run autogen.sh first:

```bash
./autogen.sh
./configure --enable-rust
```

---

## Next Steps

### 1. Basic Monitoring

See [`README-MONITORING.md`](README-MONITORING.md:1) for basic monitoring setup.

### 2. Network-Wide Monitoring

See [`NETWORK-WIDE-MONITORING.md`](NETWORK-WIDE-MONITORING.md:1) for monitoring all devices on your network.

### 3. Advanced Configuration

- **Update Rules:** Use `suricata-update` to download latest rules
- **Performance Tuning:** Adjust thread settings in suricata.yaml
- **Custom Rules:** Write your own detection signatures
- **Output Formats:** Configure JSON, PCAP, or syslog outputs

### 4. Useful Commands

```bash
# Run in verbose mode
sudo ./src/suricata -c suricata.yaml -i en0 -v

# Test configuration
./src/suricata -T -c suricata.yaml

# Run with specific ruleset
sudo ./src/suricata -c suricata.yaml -i en0 -S custom.rules

# Run on PCAP file
./src/suricata -c suricata.yaml -r capture.pcap

# View live alerts
tail -f logs/fast.log

# View detailed JSON logs
tail -f logs/eve.json | jq
```

---

## Build Information

- **Suricata Version:** 9.0.0-dev
- **Build System:** Autotools + Cargo
- **Languages:** C (core) + Rust (components)
- **Tested On:** macOS Sequoia (Apple Silicon)
- **Build Time:** ~15-20 minutes
- **Disk Usage:** ~1.5GB (source + build artifacts)

---

## Additional Resources

- **Official Documentation:** https://docs.suricata.io/
- **GitHub Repository:** https://github.com/OISF/suricata
- **Rule Documentation:** https://docs.suricata.io/en/latest/rules/
- **Community Forum:** https://forum.suricata.io/

---

## Quick Reference

### Essential Files

- `suricata.yaml` - Main configuration
- `signatures.rules` - Detection rules
- `logs/fast.log` - Alert log (human-readable)
- `logs/eve.json` - Event log (JSON format)
- `logs/stats.log` - Statistics log

### Essential Commands

```bash
# Build from scratch (full features with GeoIP2 and Redis)
./autogen.sh && ./configure --enable-rust --enable-lua --enable-geoip --enable-hiredis --disable-gccmarch-native && make -j$(sysctl -n hw.ncpu)

# Or minimal build (no GeoIP2, no Redis)
./autogen.sh && ./configure --enable-rust --enable-lua --disable-gccmarch-native && make -j$(sysctl -n hw.ncpu)

# Test configuration
./src/suricata -T -c suricata.yaml

# Run monitoring
sudo ./src/suricata -c suricata.yaml -i en0 -v

# View alerts
tail -f logs/fast.log
```

---

**Installation complete! 🎉**

Proceed to [`README-MONITORING.md`](README-MONITORING.md:1) to start monitoring your network.