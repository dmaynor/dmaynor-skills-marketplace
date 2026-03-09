---
name: hardware-re-usb-hid
description: >-
  Reverse engineer USB HID peripherals via Linux hidraw. Methodical approach:
  enumerate, capture, decode, replicate. Triggers on "reverse engineer USB",
  "USB HID protocol", "HID analysis", "hidraw", "HID report descriptor",
  "USB peripheral RE", "vendor-specific HID", or any USB HID device reverse
  engineering task.
tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
---

# USB HID Reverse Engineering

Reverse engineer USB HID peripherals from unknown protocol to working Linux control code via hidraw. Follow the RE loop: Enumerate → Capture → Decode → Replicate → Document.

## When to Use

- Reverse engineering USB HID device protocols (vendor-specific features behind hidraw)
- Parsing HID report descriptors and mapping hidraw interfaces
- Decoding vendor-specific HID commands for keyboards, mice, headsets, embedded peripherals
- Capturing USB HID traffic via usbmon/Wireshark
- Analyzing firmware from HID-class peripherals (keyboards, mice, displays)
- Building Linux replacements for Windows-only HID vendor software
- Setting up QEMU VMs with USB passthrough for vendor software capture

## When NOT to Use

- Non-HID USB devices — use libusb/pyusb for bulk, CDC, or vendor-class endpoints
- Devices with published protocol documentation (just implement it)
- Bluetooth or wireless RF protocol analysis (different toolchain)
- Network protocol analysis
- Software-only reverse engineering

## Phase 1: Device Reconnaissance

**Entry**: User identifies a target USB device.
**Exit**: Complete device profile documented (VID:PID, interfaces, hidraw map, packet sizes, endpoint types).

Enumerate everything about the target before touching any protocol.

```bash
# Full descriptor dump
lsusb -d VEND:PROD -v

# Topology tree (hub/port/speed)
lsusb -t

# HID interface enumeration (use Bash for the loop, Read for individual files)
for h in /dev/hidraw*; do
  echo "=== $h ==="
done
# Then use the Read tool on each /sys/class/hidraw/hidrawN/device/uevent

# HID report descriptors
for h in /sys/class/hidraw/hidraw*/device/report_descriptor; do
  echo "=== $h ==="
  xxd -l 256 "$h"
done
```

Use the Read tool to examine each sysfs file (`/sys/class/hidraw/hidrawN/device/uevent`, report descriptors). Use Glob to find all hidraw device paths matching `/sys/class/hidraw/hidraw*/device/uevent`. Use Grep to search for device identifiers in kernel logs (`/var/log/kern.log` or `dmesg` output).

**Kernel driver unbinding**: If the device has an active kernel driver (e.g., `usbhid`), you may need to unbind it before raw access works reliably:
```bash
# Find the device's driver binding
ls -la /sys/class/hidraw/hidrawN/device/driver
# Unbind if needed (use the device ID from uevent HID_ID)
echo -n "DEVICE_ID" | sudo tee /sys/bus/hid/drivers/hid-generic/unbind
```
Some devices work through hidraw without unbinding, but if reads return incomplete data or writes fail silently, unbinding is the likely fix.

**Required facts before proceeding:**

| Fact | Source |
|------|--------|
| VID:PID | `lsusb` |
| USB speed | `lsusb -t` (1.5/12/480/5000 Mbps) |
| Interface count & classes | `lsusb -v` |
| HID report sizes | `wMaxPacketSize` per interface |
| hidraw mapping | `/sys/class/hidraw/*/device/uevent` |
| Usage pages | Report descriptor (0xFF00+ = vendor-specific) |
| Endpoint types | Interrupt IN/OUT, Bulk, etc. |

## Phase 2: Protocol Capture

**Entry**: Device profile complete from Phase 1.
**Exit**: Raw packet captures of normal device operation, with and without vendor software.

Layer captures from passive to active:

**Step 1 — Passive sniffing** (safe, no device interaction):
```bash
# usbmon is a streaming interface — Bash is required here (not Read)
sudo modprobe usbmon
sudo timeout 10 cat /sys/kernel/debug/usb/usbmon/1u > /tmp/usb-capture.txt
```

**Step 2 — Vendor software capture** (QEMU VM):
Pass device to a Windows VM, run vendor software, capture traffic on host usbmon. See `{baseDir}/resources/qemu-setup.md` for VM configuration.

**Step 3 — Active probing** (careful, sends data to device):

**WARNING**: Adapt the packet format to match YOUR device. The header structure, status byte offset, and success value below are ONE example — discover yours from passive captures first.

```python
import os, time, sys

fd = os.open("/dev/hidrawN", os.O_RDWR)
log = open("/tmp/probe-log.txt", "w")

for cmd_id in range(0x00, 0xFF):
    packet = bytes([REPORT_ID, cmd_id]) + b'\x00' * (PACKET_SIZE - 2)
    try:
        os.write(fd, packet)
        resp = os.read(fd, PACKET_SIZE)
        line = f"CMD 0x{cmd_id:02X}: {resp[:16].hex()}"
        print(line)
        log.write(line + "\n")
        log.flush()
    except OSError as e:
        # Log the error — a USB disconnect here means STOP probing
        line = f"CMD 0x{cmd_id:02X}: ERROR — {e}"
        print(line, file=sys.stderr)
        log.write(line + "\n")
        if e.errno == 19:  # ENODEV — device disconnected
            print("DEVICE DISCONNECTED — aborting probe", file=sys.stderr)
            break
    time.sleep(0.05)  # 50ms delay — prevents overwhelming the device

log.close()
os.close(fd)
```

## Phase 3: Protocol Decoding

**Entry**: Raw captures from Phase 2.
**Exit**: Documented packet format, command table, and error codes.

Build the protocol model incrementally. **Do not assume a specific packet format** — discover it from captures. Header length, field positions, and status codes vary widely between devices.

1. **Framing** — Find packet boundaries, header structure, report IDs
2. **Command/Response** — Map command bytes to functions
3. **Endianness** — Test both LE and BE for multi-byte fields
4. **Padding** — Devices may require exact packet sizes (64B, 512B, 1024B)
5. **State machine** — Track handle/session state, required sequences
6. **Error codes** — Catalog all error responses and their triggers

Use Grep to search captured data for patterns. Use the Write tool to maintain a protocol specification document as findings accumulate. See `{baseDir}/resources/protocol-template.md` for the documentation format.

## Phase 4: Firmware Analysis (Optional)

**Entry**: Firmware binary obtained (vendor update, debug interface, or flash dump).
**Exit**: Identified architecture, command dispatch table, and key data structures.

**Extraction sources (try in order):**
1. Vendor update packages (zip/exe on vendor website)
2. OTA update capture (USB sniff during update)
3. Debug interfaces (SWD/JTAG if physically accessible)
4. Flash chip direct read

**Analysis:**
```bash
binwalk firmware.bin
file firmware.bin
strings firmware.bin | grep -i "version\|build\|copyright\|arm\|cortex"
```

For ARM Cortex-M: examine vector table at offset 0 — SP at `[0:4]`, Reset handler at `[4:8]`. Use this to determine flash base address for Ghidra loading.

**Key targets in firmware:**
- USB descriptor tables (search for VID/PID bytes)
- Command dispatch tables (switch/case or function pointer arrays)
- Display init sequences (SPI/I2C commands)
- Compression routines and crypto implementations

## Phase 5: Replicate & Validate

**Entry**: Decoded protocol from Phase 3.
**Exit**: Working Python code that controls the device from Linux without vendor software.

Build minimal reproducers for each discovered command:

```python
#!/usr/bin/env python3
import os, glob

def find_device(name_pattern, interface_pattern):
    """Auto-discover hidraw device by name and interface."""
    for h in sorted(glob.glob("/dev/hidraw*")):
        base = os.path.basename(h)
        try:
            uevent = open(f"/sys/class/hidraw/{base}/device/uevent").read()
            if name_pattern in uevent and interface_pattern in uevent:
                return h
        except: pass
    return None

def send_recv(dev_path, packet, size):
    """Send packet, read response."""
    fd = os.open(dev_path, os.O_RDWR)
    try:
        padded = packet.ljust(size, b'\x00')
        os.write(fd, padded)
        return os.read(fd, size)
    finally:
        os.close(fd)
```

Use the Write tool to save working scripts. Test each command individually before combining into larger tools.

## Phase 6: Document

**Entry**: Working code from Phase 5.
**Exit**: Complete RE report with device profile, protocol spec, working code, open questions, and risk assessment.

Produce these deliverables:

1. **Device Profile** — VID:PID, interfaces, hidraw map, packet sizes
2. **Protocol Spec** — packet format, command table, error codes
3. **Working Code** — minimal Python reproducer for each function
4. **Open Questions** — unknowns needing further investigation
5. **Risk Assessment** — commands with write/flash/brick potential

## Safety Rules

- **READ before WRITE** — always try GET/query commands before SET/write
- **Save device state** before modifying anything (dump configs, profiles)
- **Never flash firmware** without explicit user approval and a known-good backup
- **Watch for bricking patterns** — if a command causes USB disconnect, DO NOT retry
- **Test on one device first** — never batch-apply to multiple devices
- **Log everything** — every packet sent and received, with timestamps

## Resources

See `{baseDir}/resources/` directory:
- `{baseDir}/resources/qemu-setup.md` — QEMU VM configuration for USB passthrough and vendor software capture
- `{baseDir}/resources/protocol-template.md` — Protocol documentation template
- `{baseDir}/resources/display-re.md` — Display protocol RE techniques for LCD/OLED peripherals
