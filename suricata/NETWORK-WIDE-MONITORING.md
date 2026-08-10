# 🌐 Network-Wide Monitoring Guide

## Overview

This guide explains how to monitor **ALL devices** on your network, not just your MacBook.

---

## 🎯 Three Approaches

### Option 1: Promiscuous Mode (Easiest - Recommended)

**Difficulty:** ⭐ Easy  
**Risk:** ✅ Safe  
**Effectiveness:** Limited on switched networks

### Option 2: Gateway Mode (Moderate)

**Difficulty:** ⭐⭐ Moderate  
**Risk:** ⚠️ Can disrupt network  
**Effectiveness:** ✅ Monitors all devices

### Option 3: ARP Spoofing (Advanced)

**Difficulty:** ⭐⭐⭐ Advanced  
**Risk:** ⚠️⚠️ Legal/ethical concerns  
**Effectiveness:** ✅ Monitors specific devices

---

## 🚀 Quick Start

Run the setup script:

```bash
sudo ./setup-network-monitoring.sh
```

This interactive script will guide you through the options.

---

## 📋 Option 1: Promiscuous Mode (Recommended)

### What It Does:

- Captures all packets visible to your network card
- Passive monitoring (doesn't affect network)
- Safe and simple

### Limitations:

On a **switched network** (most modern networks), you'll only see:

- ✅ Broadcast traffic
- ✅ Multicast traffic
- ✅ Traffic to/from your Mac
- ❌ Traffic between other devices

### Setup:

```bash
sudo ./setup-network-monitoring.sh
# Choose option 1
```

### To See ALL Traffic:

You need **port mirroring** on your switch:

1. **Check if your switch supports it:**

   - Look for: "Port Mirroring", "SPAN", "Monitor Port"
   - Common on managed switches
   - Not available on basic consumer switches

2. **Configure port mirroring:**

   - Access your switch admin panel
   - Set up port mirroring/SPAN
   - Mirror all ports to the port your Mac is connected to
   - Consult your switch documentation

3. **Alternative: Use a network hub**
   - Hubs broadcast all traffic (unlike switches)
   - Connect devices through hub
   - Older technology but works for monitoring

---

## 🔧 Option 2: Gateway Mode

### What It Does:

- Configures your Mac as the network gateway
- All traffic routes through your Mac
- Suricata sees everything

### Requirements:

- Your Mac must stay powered on
- Other devices must be reconfigured
- Can impact network performance

### Setup:

#### Step 1: Run Setup Script

```bash
sudo ./setup-network-monitoring.sh
# Choose option 2
```

This enables:

- IP forwarding
- NAT (Network Address Translation)
- Packet filtering rules

#### Step 2: Configure Other Devices

On **each device** you want to monitor:

**Windows:**

1. Control Panel → Network → Change adapter settings
2. Right-click connection → Properties
3. IPv4 Properties
4. Change Default Gateway to: `9.79.193.4`
5. Keep DNS as: `9.79.192.1`

**Mac/iPhone/iPad:**

1. System Settings → Network
2. Advanced → TCP/IP
3. Change Router to: `9.79.193.4`
4. Keep DNS as: `9.79.192.1`

**Android:**

1. Settings → WiFi → Long press network
2. Modify Network → Advanced
3. Change Gateway to: `9.79.193.4`

#### Step 3: Start Monitoring

```bash
sudo ./monitor-network.sh
```

### To Disable Gateway Mode:

```bash
sudo pfctl -d
sudo sysctl -w net.inet.ip.forwarding=0
```

Then reconfigure devices back to original gateway (9.79.192.1)

---

## 🔍 Option 3: ARP Spoofing (Advanced)

### ⚠️ LEGAL WARNING

**Only use on networks you own or have explicit permission to monitor.**

ARP spoofing is a man-in-the-middle technique that can be considered a network attack.

### What It Does:

- Intercepts traffic between devices and gateway
- Redirects traffic through your Mac
- Monitors specific devices

### Requirements:

Install additional tools:

```bash
brew install dsniff
# OR
brew install ettercap
```

### Usage with arpspoof:

**Terminal 1: Spoof gateway**

```bash
sudo arpspoof -i en0 -t 9.79.192.1 <target_device_ip>
```

**Terminal 2: Spoof target device**

```bash
sudo arpspoof -i en0 -t <target_device_ip> 9.79.192.1
```

**Terminal 3: Enable forwarding**

```bash
sudo sysctl -w net.inet.ip.forwarding=1
```

**Terminal 4: Monitor traffic**

```bash
sudo ./monitor-network.sh
```

### Usage with ettercap:

```bash
sudo ettercap -T -i en0 -M arp:remote /9.79.192.1// /<target_ip>//
```

---

## 📊 Comparison Table

| Feature               | Promiscuous | Gateway       | ARP Spoofing |
| --------------------- | ----------- | ------------- | ------------ |
| **Difficulty**        | Easy        | Moderate      | Advanced     |
| **Safety**            | Very Safe   | Moderate Risk | High Risk    |
| **Effectiveness**     | Limited\*   | Full          | Full         |
| **Requires Reconfig** | No          | Yes           | No           |
| **Legal Concerns**    | None        | None          | Yes          |
| **Network Impact**    | None        | Moderate      | Low          |

\*Limited on switched networks without port mirroring

---

## 🎯 Recommended Approach

### For Home Users:

1. **Start with Promiscuous Mode** (Option 1)
2. **If you have a managed switch:** Configure port mirroring
3. **If not:** Consider Gateway Mode (Option 2)

### For Learning/Testing:

- **Promiscuous Mode** is sufficient
- Monitors your own traffic
- Safe and simple

### For Professional Monitoring:

- **Port Mirroring** (with Promiscuous Mode)
- Dedicated monitoring port on switch
- Professional IDS deployment

---

## 🔧 Troubleshooting

### Not seeing other devices' traffic?

**Check 1: Network type**

```bash
# Are you on a switched network?
# Most modern networks use switches, not hubs
```

**Check 2: Promiscuous mode enabled?**

```bash
ifconfig en0 | grep PROMISC
# Should show PROMISC flag
```

**Check 3: Port mirroring configured?**

- Check your switch settings
- Verify SPAN/mirror port is active

### Gateway mode not working?

**Check 1: IP forwarding enabled?**

```bash
sysctl net.inet.ip.forwarding
# Should return: net.inet.ip.forwarding: 1
```

**Check 2: Firewall rules active?**

```bash
sudo pfctl -s all
# Should show NAT rules
```

**Check 3: Devices configured correctly?**

- Verify gateway is set to 9.79.193.4
- Test connectivity: `ping 8.8.8.8`

---

## 📈 What You'll See

Once configured for network-wide monitoring, you'll capture:

✅ **All devices' traffic:**

- Phones, tablets, laptops
- Smart TVs, IoT devices
- Gaming consoles
- Everything on the network

✅ **All protocols:**

- Web browsing (HTTP/HTTPS)
- Streaming (Netflix, YouTube)
- Gaming traffic
- Smart home devices
- DNS queries from all devices

✅ **Complete visibility:**

- Source/destination IPs
- Protocols and ports
- Connection patterns
- Bandwidth usage per device

---

## 🛡️ Security & Privacy

### Important Considerations:

1. **Legal:** Only monitor networks you own
2. **Privacy:** You'll see all network activity
3. **Responsibility:** Secure your monitoring data
4. **Ethics:** Inform users if monitoring shared network

### Best Practices:

- ✅ Document what you're monitoring
- ✅ Secure log files (encrypt if needed)
- ✅ Limit access to monitoring system
- ✅ Have a clear monitoring policy
- ✅ Comply with local laws and regulations

---

## 📚 Additional Resources

- **Port Mirroring:** Check your switch documentation
- **Suricata Docs:** https://docs.suricata.io
- **Network Security:** Research IDS/IPS best practices
- **Legal:** Consult local laws on network monitoring

---

## 🆘 Need Help?

1. **Start simple:** Try Promiscuous Mode first
2. **Test thoroughly:** Verify what you're capturing
3. **Document changes:** Keep track of network modifications
4. **Have a rollback plan:** Know how to undo changes

---

**Remember: With great monitoring power comes great responsibility!** 🛡️
