# Suricata Network Monitoring Guide

## 🚀 Quick Start

Your Suricata installation is ready to monitor all network traffic on interface **en0** (IP: 9.79.193.4).

## 📋 Available Scripts

### 1. Start Network Monitoring

```bash
sudo ./monitor-network.sh
```

**What it does:**

- Monitors ALL traffic on en0 interface in real-time
- Detects ICMP, TCP, UDP, and HTTP traffic
- Logs all events to `logs/` directory
- Press Ctrl+C to stop

**⚠️ Requires sudo** - Network monitoring needs root privileges

---

### 2. View Live Alerts (in another terminal)

```bash
./view-live-alerts.sh
```

**What it does:**

- Shows alerts in real-time as they happen
- Displays detected threats and suspicious activity
- Updates automatically when new alerts occur
- Press Ctrl+C to stop

---

### 3. Analyze Captured Traffic

```bash
./analyze-traffic.sh
```

**What it does:**

- Shows summary statistics of captured traffic
- Counts alerts, flows, DNS queries, HTTP requests, TLS connections
- Displays recent alerts
- Run this after monitoring to see what was captured

---

## 📊 Understanding the Logs

### logs/fast.log

Quick alert summary - easy to read format

```
02/09/2026-10:52:32  [**] [1:1000001:1] ICMP Packet detected [**]
{ICMP} 192.168.1.100:8 -> 192.168.1.1:0
```

### logs/eve.json

Detailed JSON events - complete information about every packet

- Full packet details
- Protocol information
- Source/destination IPs and ports
- Timestamps
- Alert metadata

### logs/stats.log

Performance statistics

- Packets processed
- Memory usage
- Detection engine stats
- Flow statistics

---

## 🎯 Current Detection Rules

Your system is configured to detect:

1. **ICMP Traffic** (sid:1000001)

   - Detects ping requests/responses
   - Useful for network diagnostics

2. **TCP Connections** (sid:1000002)

   - Detects all TCP traffic
   - Web browsing, SSH, etc.

3. **UDP Traffic** (sid:1000003)

   - Detects all UDP packets
   - DNS queries, streaming, etc.

4. **HTTP Requests** (sid:1000004)
   - Detects web traffic
   - Unencrypted web browsing

---

## 🔧 Configuration Files

- **suricata.yaml** - Main configuration
- **signatures.rules** - Detection rules
- **etc/classification.config** - Alert classifications
- **etc/reference.config** - Reference information

---

## 💡 Usage Examples

### Example 1: Monitor for 5 minutes

```bash
# Terminal 1: Start monitoring
sudo ./monitor-network.sh

# Terminal 2: Watch alerts
./view-live-alerts.sh

# After 5 minutes, press Ctrl+C in Terminal 1
# Then analyze results:
./analyze-traffic.sh
```

### Example 2: Test with sample traffic

```bash
# Terminal 1: Start monitoring
sudo ./monitor-network.sh

# Terminal 2: Generate test traffic
ping -c 5 google.com
curl http://example.com

# Check alerts
./analyze-traffic.sh
```

### Example 3: Continuous monitoring

```bash
# Start monitoring in background
sudo ./monitor-network.sh &

# Check status periodically
./analyze-traffic.sh

# Stop when done
sudo pkill -f suricata
```

---

## 📈 What You'll See

When monitoring, Suricata will detect:

✅ **All network packets** on en0
✅ **Protocol types** (TCP, UDP, ICMP, etc.)
✅ **Source and destination** IPs and ports
✅ **DNS queries** - what domains you're accessing
✅ **HTTP traffic** - unencrypted web requests
✅ **TLS connections** - encrypted connections
✅ **Suspicious patterns** matching your rules

---

## 🛡️ Security Notes

1. **Root Access Required**: Network monitoring needs elevated privileges
2. **Privacy**: You're monitoring YOUR OWN network traffic
3. **Performance**: Monitoring uses CPU and disk space
4. **Legal**: Only monitor networks you own or have permission to monitor

---

## 🔍 Troubleshooting

### "Permission denied" error

```bash
# Make sure to use sudo
sudo ./monitor-network.sh
```

### No alerts appearing

- Check if traffic is actually flowing on en0
- Try generating test traffic: `ping google.com`
- Verify rules are loaded: `./src/suricata -c suricata.yaml -T`

### Logs directory full

```bash
# Clear old logs
rm -rf logs/*
```

---

## 📚 Next Steps

1. **Add More Rules**: Edit `signatures.rules` to detect specific threats
2. **Download Rule Sets**: Use suricata-update to get professional rule sets
3. **Customize Alerts**: Modify `suricata.yaml` for your needs
4. **Set Up Dashboards**: Use tools like Kibana to visualize eve.json data

---

## 🆘 Need Help?

- Configuration: Check `suricata.yaml`
- Rules: Edit `signatures.rules`
- Logs: Look in `logs/` directory
- Documentation: https://docs.suricata.io

---

**Happy Monitoring! 🎉**
