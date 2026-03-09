# Display Protocol Reverse Engineering

## For Devices with LCD/OLED Screens

### Step 1: Identify Display Controller

Search firmware strings for known controller ICs:

| Controller | Type | Resolution | Interface |
|------------|------|------------|-----------|
| ILI9341 | TFT LCD | 240x320 | SPI/Parallel |
| SSD1306 | OLED | 128x64 | I2C/SPI |
| ST7789 | TFT LCD | 240x240/320 | SPI |
| SSD1351 | Color OLED | 128x128 | SPI |
| GC9A01 | Round LCD | 240x240 | SPI |

### Step 2: Find Framebuffer

Look for contiguous memory regions matching expected sizes:

| Format | Calculation | Example (248x170) |
|--------|-------------|-------------------|
| RGB565 | width × height × 2 | 84,320 bytes |
| RGB888 | width × height × 3 | 126,480 bytes |
| L8 (grayscale) | width × height | 42,160 bytes |
| L8 + CLUT | width × height + 256 × 2 | 42,672 bytes |

### Step 3: Trace Render Pipeline

Map the path: USB command → framebuffer → display transfer

Common patterns:
- Direct framebuffer write via USB (send pixel data in packets)
- Indexed resource system (file IDs map to stored images)
- Compressed frames (LZW, RLE, LZ4) decoded on-device
- TouchGFX or LVGL framework managing rendering

### Step 4: Compression Formats

**Common in embedded displays:**

- **RLE** — Run-length encoding, simple, look for repeated byte patterns
- **LZW** — Lempel-Ziv-Welch, variable bit width (9-12 bits typical)
- **LZ4** — Fast decompression, look for LZ4 magic bytes `04 22 4D 18`
- **Raw** — No compression, just pixel data in format order
- **L8 + CLUT** — 8-bit indexed with Color Look-Up Table (palette)

**LZW Detection:**
- Variable bit-width codes starting at 9 bits
- Clear code = 2^min_bits, EOI code = clear + 1
- Dictionary grows from initial alphabet size
- Bit packing: LSB-first (GIF-style) or MSB-first

### Display Parameter Discovery

```python
# Probe for framebuffer read command (if device supports it)
# Try common display-related command IDs
for cmd in [0x10, 0x20, 0x30, 0x40, 0x50]:
    resp = send_recv(dev, bytes([0x00, cmd]) + b'\x00' * 62, 64)
    if resp and resp[2] == 0x00:
        print(f"Display cmd 0x{cmd:02X} responded: {resp[:16].hex()}")
```

### Resolution Discovery

If resolution is unknown:
1. Check firmware strings for dimension values
2. Look for display init sequences (often contain resolution in register writes)
3. Try common resolutions and check if framebuffer size matches transfer size
4. Read the device manual/datasheet if available
