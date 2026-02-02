# Godot Export Guide

## Export Templates

Download from Godot Editor: **Editor → Manage Export Templates → Download**.

Or manually from: https://godotengine.org/download

## Platform Setup

### Windows

1. Add Windows Desktop preset
2. Configure:
   - **Product Name**: Game name in executable properties
   - **Company Name**: Developer/publisher
   - **File Version/Product Version**: Version numbers
   - **Icon**: `.ico` file (256x256 recommended)

Export modes:
- **Export PCK/ZIP**: Data only (requires Godot runtime)
- **Export Project**: Full executable

### macOS

Requirements:
- Xcode Command Line Tools (for code signing)
- Apple Developer account (for notarization)

Configuration:
- **Bundle Identifier**: `com.company.gamename`
- **App Category**: Mac App Store category
- **Icon**: `.icns` file
- **Codesign**: Identity from keychain
- **Notarization**: Requires Apple credentials

### Linux

Minimal configuration needed:
- **Binary Format**: x86_64 (most common)
- **Architecture**: 64-bit recommended

### Android

Requirements:
- Android SDK (via Android Studio or standalone)
- JDK 17+
- Debug keystore (auto-generated) or release keystore

Setup in Editor Settings → Export → Android:
```
Android SDK Path: /path/to/Android/sdk
Debug Keystore: /path/to/.android/debug.keystore
```

Configuration:
- **Package Unique Name**: `com.company.gamename`
- **Version Code**: Integer, increment each release
- **Version Name**: Display version (e.g., "1.0.0")
- **Min SDK**: API level 21+ recommended
- **Target SDK**: Latest stable API
- **Permissions**: Request only needed permissions
- **Icon**: Adaptive icons (foreground + background)

Screen orientations:
```
Orientation: Landscape, Portrait, Sensor Landscape, etc.
```

### iOS

Requirements:
- macOS with Xcode
- Apple Developer account ($99/year)
- Provisioning profile and certificates

Configuration:
- **App Store Team ID**: From Apple Developer account
- **Bundle Identifier**: `com.company.gamename`
- **Provisioning Profile**: Downloaded from Apple
- **Code Sign Identity**: iPhone Distribution

Icons required (all sizes):
- 1024x1024 (App Store)
- 180x180 (iPhone @3x)
- 120x120 (iPhone @2x)
- 167x167 (iPad Pro)
- 152x152 (iPad @2x)

### Web (HTML5)

Configuration:
- **Export Type**: Regular or GDExtension (if using native plugins)
- **VRAM Texture Compression**: ETC2 for mobile, S3TC for desktop
- **Canvas Resize Policy**: Adaptive recommended
- **Focus Canvas on Start**: Enable for input capture

Hosting requirements:
- CORS headers if loading external resources
- SharedArrayBuffer headers for threading:
```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

## Export Presets File

Located at `export_presets.cfg` in project root. Version control friendly.

```ini
[preset.0]
name="Windows Desktop"
platform="Windows Desktop"
runnable=true
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.0.options]
binary_format/64_bits=true
texture_format/bptc=true
texture_format/s3tc=true
custom_template/debug=""
custom_template/release=""
application/icon="res://icon.ico"
application/product_name="My Game"
```

## Feature Tags

Conditional exports based on platform:

```gdscript
# In code
if OS.has_feature("mobile"):
    # Mobile-specific code
elif OS.has_feature("web"):
    # Web-specific code
elif OS.has_feature("pc"):
    # Desktop-specific code

# Check specific platform
if OS.has_feature("windows"):
    pass
elif OS.has_feature("macos"):
    pass
elif OS.has_feature("linux"):
    pass
elif OS.has_feature("android"):
    pass
elif OS.has_feature("ios"):
    pass
```

## Export Filters

### Include Specific Files

In export preset:
```
include_filter="*.json, *.csv, data/*"
```

### Exclude Files

```
exclude_filter="*.md, test/*, debug/*"
```

### Export Selected Scenes

Set **Export Filter** to "Export selected scenes (and dependencies)" then select scenes.

## Resource Encryption

Project Settings → Resource → **Encryption**:
1. Enable **Encrypt Resources**
2. Set **Encryption Key** (256-bit hex string)

Generate key:
```gdscript
var key := ""
for i in 32:
    key += "%02x" % randi_range(0, 255)
print(key)
```

## Build Optimization

### Reduce Binary Size

Project Settings:
- Disable unused modules in custom export templates
- **GDScript → Warning Level**: Warnings (not errors in release)

Export settings:
- **Strip Debug Symbols**: Enable for release
- **Optimize**: Size or Speed based on needs

### Texture Compression

Per-platform compression in Export:
- **Windows/Linux**: S3TC (BC1-BC3) + BPTC (BC7)
- **macOS**: S3TC + BPTC
- **Android**: ETC2
- **iOS**: PVRTC or ETC2
- **Web**: ETC2 + S3TC

### Audio Compression

Import dock per audio file:
- **Force Mono**: For positional audio
- **Max Rate Hz**: Reduce for less critical sounds
- **Loop Mode**: Disable if not looping

## Continuous Integration

### GitHub Actions Example

```yaml
name: Export Game

on:
  push:
    tags:
      - 'v*'

jobs:
  export:
    runs-on: ubuntu-latest
    container:
      image: barichello/godot-ci:4.2
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup
        run: |
          mkdir -v -p ~/.local/share/godot/export_templates
          mv /root/.local/share/godot/export_templates/* ~/.local/share/godot/export_templates/
      
      - name: Windows Build
        run: |
          mkdir -v -p build/windows
          godot --headless --export-release "Windows Desktop" build/windows/game.exe
      
      - name: Linux Build
        run: |
          mkdir -v -p build/linux
          godot --headless --export-release "Linux/X11" build/linux/game.x86_64
      
      - name: Web Build
        run: |
          mkdir -v -p build/web
          godot --headless --export-release "HTML5" build/web/index.html
      
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: builds
          path: build/
```

## Command Line Export

```bash
# Export release build
godot --headless --export-release "Windows Desktop" ./build/game.exe

# Export debug build
godot --headless --export-debug "Windows Desktop" ./build/game_debug.exe

# Export PCK only
godot --headless --export-pack "Windows Desktop" ./build/game.pck

# Validate project (no export)
godot --headless --validate-project
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing export templates | Download via Editor → Manage Export Templates |
| Android SDK not found | Set path in Editor Settings → Export → Android |
| iOS provisioning error | Regenerate profiles in Apple Developer portal |
| Web SharedArrayBuffer error | Configure server CORS/COOP headers |
| Large export size | Enable texture compression, strip debug symbols |
| Crash on mobile | Check device logs, verify permissions |
| Missing resources | Check export filters, verify paths |
