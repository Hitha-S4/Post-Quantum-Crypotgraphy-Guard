# 🚀 Quick Start: Monitor ALL Devices on Your Network

## Problem: Only Seeing Your Mac's Traffic?

You're on a **switched network** - this is normal! Switches only send traffic to the device it's meant for, so you can only see your own Mac's traffic by default.

## Solution: Gateway Mode (5 Minutes Setup)

Configure your Mac as the network gateway so ALL traffic flows through it!

---

## 📋 Step-by-Step Guide

### Step 1: Enable Gateway Mode

```bash
sudo ./enable-gateway-mode.sh
```

This will:

- ✅ Enable IP forwarding on your Mac
- ✅ Configure NAT (Network Address Translation)
- ✅ Allow traffic to flow through your Mac

### Step 2: Configure ONE Test Device

Pick one device (phone, tablet, or laptop) to test with first.

#### For iPhone/iPad:

1. Settings → WiFi
2. Tap (i) next to your network
3. Configure IP → Manual
4. Change **Router** from `9.79.192.1` to `9.79.193.4`
5. Keep DNS as `9.79.192.1`
6. Save

#### For Android:

1. Settings → WiFi
2. Long press your network → Modify
3. Advanced Options → IP Settings → Static
4. Change **Gateway** from `9.79.192.1` to `9.79.193.4`
5. Keep DNS as `9.79.192.1`
6. Save

#### For Another Mac/Laptop:

1. System Settings → Network
2. Click your connection → Details/Advanced
3. TCP/IP tab
4. Change **Router** from `9.79.192.1` to `9.79.193.4`
5. Keep DNS as `9.79.192.1`
6. Apply

#### For Windows:

1. Control Panel → Network and Sharing
2. Change adapter settings
3. Right-click connection → Properties
4. IPv4 → Properties
5. Change **Default Gateway** from `9.79.192.1` to `9.79.193.4`
6. Keep DNS as `9.79.192.1`
7. OK

### Step 3: Test the Device

On the device you just configured:

```bash
# Test internet connectivity
ping 8.8.8.8

# Browse the web
# Open any website
```

If it works, the device is now routing through your Mac! ✅

### Step 4: Check Suricata Logs

```bash
# View live alerts
./view-live-alerts.sh

# OR check the log file
tail -f logs/fast.log

# OR analyze captured traffic
./analyze-traffic.sh
```

You should now see traffic from the other device! 🎉

### Step 5: Configure More Devices (Optional)

Repeat Step 2 for each device you want to monitor.

---

## 🔍 What You'll See

Once configured, Suricata will capture:

✅ **From the test device:**

- Web browsing
- App network activity
- Streaming (Netflix, YouTube, etc.)
- Gaming traffic
- DNS queries
- Everything!

✅ **In the logs:**

```
[**] [1:1000002:1] TCP Connection detected [**]
{TCP} 192.168.1.50:54321 -> 142.250.185.46:443
                ↑ This is the other device!

[**] [1:1000004:1] HTTP Request detected [**]
{HTTP} 192.168.1.50 -> 93.184.216.34:80
```

---

## 🎯 Quick Verification

### Check if gateway mode is working:

```bash
# On your Mac, check IP forwarding:
sysctl net.inet.ip.forwarding
# Should show: net.inet.ip.forwarding: 1

# Check NAT rules:
sudo pfctl -s nat
# Should show NAT rules for 9.79.192.0/23
```

### Check if device is routing through Mac:

On the test device:

```bash
# Check route (Mac/Linux):
netstat -rn | grep default
# Should show: 9.79.193.4 as gateway

# Trace route to internet:
traceroute 8.8.8.8
# First hop should be 9.79.193.4 (your Mac)
```

---

## 🛑 To Stop/Disable

### Temporarily stop monitoring:

```bash
# In the monitoring terminal, press Ctrl+C
```

### Disable gateway mode:

```bash
sudo ./disable-gateway-mode.sh
```

### Restore devices to normal:

On each configured device, change gateway back to `9.79.192.1`

---

## ⚠️ Troubleshooting

### Device has no internet after configuration:

**Check 1:** Is gateway mode enabled?

```bash
sysctl net.inet.ip.forwarding
# Should be: 1
```

**Check 2:** Is NAT working?

```bash
sudo pfctl -s nat
# Should show NAT rules
```

**Check 3:** Can you ping your Mac from the device?

```bash
ping 9.79.193.4
# Should respond
```

**Fix:** Re-run enable script:

```bash
sudo ./enable-gateway-mode.sh
```

### Still only seeing Mac's traffic:

**Check 1:** Did you configure the device's gateway?

- Verify gateway is set to `9.79.193.4` on the device

**Check 2:** Is the device actually using your Mac?

```bash
# On the device:
traceroute 8.8.8.8
# First hop should be 9.79.193.4
```

**Check 3:** Is Suricata running?

```bash
ps aux | grep suricata
# Should show suricata process
```

### Device configured but can't browse:

**Check 1:** DNS settings

- Make sure DNS is set to `9.79.192.1` (not 9.79.193.4)

**Check 2:** Firewall blocking?

```bash
# Temporarily disable firewall on Mac
sudo pfctl -d
# Try browsing on device
# Re-enable: sudo pfctl -e
```

---

## 📊 Expected Results

After setup, you should see:

### In logs/fast.log:

```
[**] ICMP Packet detected [**] {ICMP} 9.79.193.4 -> 8.8.8.8
[**] TCP Connection detected [**] {TCP} 192.168.1.50:12345 -> 142.250.185.46:443
[**] HTTP Request detected [**] {HTTP} 192.168.1.100 -> 93.184.216.34:80
```

### In logs/eve.json:

- Multiple source IPs (not just 9.79.193.4)
- Traffic from configured devices
- DNS queries from all devices
- Complete network visibility

---

## 🎊 Success Indicators

You'll know it's working when:

✅ Device can browse internet normally
✅ Logs show traffic from device's IP (not just 9.79.193.4)
✅ `./analyze-traffic.sh` shows multiple source IPs
✅ Live alerts show traffic from other devices

---

## 💡 Pro Tips

1. **Start with one device** - Test thoroughly before adding more
2. **Keep monitoring running** - Don't stop/start while testing
3. **Generate traffic** - Browse, stream, use apps on test device
4. **Check logs frequently** - Verify you're seeing the traffic
5. **Document IPs** - Note which IP belongs to which device

---

## 📚 More Information

- Full guide: [`NETWORK-WIDE-MONITORING.md`](NETWORK-WIDE-MONITORING.md:1)
- Basic monitoring: [`README-MONITORING.md`](README-MONITORING.md:1)
- Disable gateway: `sudo ./disable-gateway-mode.sh`

---

**You're now monitoring your entire network!** 🛡️🌐
