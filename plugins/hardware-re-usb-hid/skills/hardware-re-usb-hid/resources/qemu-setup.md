# QEMU VM Setup for Vendor Software Capture

## Minimal Launch Command

```bash
qemu-system-x86_64 \
  -name "RE-VM" -enable-kvm -machine q35,accel=kvm \
  -cpu host -smp 4 -m 8G \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.ms.fd \
  -drive if=pflash,format=raw,file=OVMF_VARS.fd \
  -drive file=win11.qcow2,format=qcow2,if=none,id=disk0 \
  -device ahci,id=ahci -device ide-hd,drive=disk0,bus=ahci.0 \
  -device usb-ehci,id=usb \
  -device usb-tablet,id=tablet0 \
  -device usb-host,vendorid=0xVVVV,productid=0xPPPP \
  -device e1000,netdev=net0 \
  -netdev user,id=net0 \
  -display gtk -vnc :0 \
  -monitor unix:qemu-monitor.sock,server,nowait \
  -audio driver=none
```

**Adjust for your device:**
- Replace `vendorid=0xVVVV,productid=0xPPPP` with target device VID:PID
- For USB 3.0 devices, use `-device qemu-xhci,id=usb` instead of `usb-ehci`
- For composite devices with many interfaces, xHCI is often required

## TPM 2.0 (Required for Win11)

```bash
mkdir -p tpm
swtpm socket --tpmstate dir=tpm --tpm2 \
    --ctrl type=unixio,path=tpm/swtpm-sock &

# Add to QEMU command:
-chardev socket,id=chrtpm,path=tpm/swtpm-sock \
-tpmdev emulator,id=tpm0,chardev=chrtpm \
-device tpm-tis,tpmdev=tpm0
```

## Programmatic VM Control

Use a Python-based monitor client (not socat — it has escaping issues):

```python
import socket, time

def send_cmd(cmd, sock_path="qemu-monitor.sock"):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        s.connect(sock_path)
        try: s.recv(4096)
        except socket.timeout: pass
        s.sendall((cmd + "\n").encode())
        time.sleep(0.15)
        try: return s.recv(8192).decode(errors="replace")
        except socket.timeout: return ""
```

For mouse operations, use VNC (vncdotool) to avoid conflicts with the GTK tablet device:

```python
import subprocess
def vnc_click(x, y, display="localhost::5900"):
    subprocess.run(["vncdo", "-s", display, "move", str(x), str(y), "click", "1"],
                   check=True, capture_output=True, timeout=10)
```

## USB Traffic Capture During VM Operation

```bash
sudo modprobe usbmon
# Find bus number from lsusb output
tshark -i usbmon1 -w /tmp/vendor-capture.pcapng
# Or use Wireshark GUI: wireshark -i usbmon1
```

The host usbmon captures all USB traffic including VM passthrough transparently.
