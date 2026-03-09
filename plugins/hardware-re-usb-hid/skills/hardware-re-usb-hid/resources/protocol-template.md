# Protocol Documentation Template

**NOTE**: The packet format below is ONE common pattern (2-byte header with Report ID + Command ID). Many devices use different structures — 3+ byte headers, sub-command fields, length fields, checksums, etc. Always discover your device's actual framing from passive captures before assuming this layout.

## Device Profile

| Field | Value |
|-------|-------|
| Device | [Name] |
| VID:PID | 0xVVVV:0xPPPP |
| USB Speed | [1.5 / 12 / 480 / 5000] Mbps |
| Interfaces | [count] |
| Protocol Interface | hidrawN (interfaceN, [size]-byte packets) |
| Packet Size | [64 / 512 / 1024] bytes |

## Interface Map

| hidraw | Interface | Class | Usage | Packet Size |
|--------|-----------|-------|-------|-------------|
| hidraw0 | input0 | HID | Keyboard | 64B |
| hidraw1 | input1 | HID | Media keys | 64B |
| hidraw2 | input2 | HID | Vendor-specific | 1024B |

## Packet Format

```
REQUEST:
  [0]     Report ID (0x00 for HID default)
  [1]     Command ID
  [2..N]  Payload (command-specific)
  [N+1..] Zero-padding to packet size

RESPONSE:
  [0]     Report ID
  [1]     Command ID (echo)
  [2]     Status (0x00=OK, 0x01=unknown cmd, ...)
  [3..N]  Response data
```

## Command Table

| Cmd | Name | Request Payload | Response Data | Notes |
|-----|------|----------------|---------------|-------|
| 0x01 | GET_VERSION | (none) | [major, minor, patch] | |
| 0x02 | GET_PROPERTY | [propId_LE16] | [value...] | |

## Error Codes

| Code | Meaning | Trigger |
|------|---------|---------|
| 0x00 | OK | Successful command |
| 0x01 | Unknown command | Invalid command ID |

## State Machine

```
INIT → OPEN_HANDLE → AUTHENTICATED → READY
                                       ↓
                                   READ/WRITE
                                       ↓
                                   CLOSE_HANDLE
```

## Dangerous Commands

| Cmd | Risk | Mitigation |
|-----|------|------------|
| 0xNN | Flash write | Requires backup first |

## Open Questions

- [ ] Unknown command 0xNN — sends data but purpose unclear
- [ ] State machine transition conditions need verification
