#!/usr/bin/env bash
# find_enum_strings.sh — scan a Mach-O binary for adjacent-short-string
# enum candidates.  Prints clusters of 4+ packed short strings (<30 bytes
# each) in __cstring, which is the usual compile-time layout for a C
# switch's name-lookup pool.
#
# Usage: find_enum_strings.sh /path/to/binary [arch]
set -euo pipefail

BIN=${1:?binary path required}
ARCH=${2:-arm64e}
SLICE=$(mktemp -t enum-slice)
trap 'rm -f "$SLICE"' EXIT

lipo -thin "$ARCH" "$BIN" -output "$SLICE" 2>/dev/null || cp "$BIN" "$SLICE"

# Extract all strings with file offsets.
# Cluster rule: >=4 consecutive strings with:
#   - length 2..30
#   - file-offset delta == prev_len+1 (adjacent)
strings -a -t x "$SLICE" | awk '
    function flush() {
        if (n >= 4) {
            printf "\n--- candidate cluster (%d strings @ first_off=0x%s) ---\n", n, first_off
            for (i = 0; i < n; i++) print "  " buf[i]
        }
        n = 0
    }
    {
        off = strtonum("0x" $1)
        s = ""
        for (i = 2; i <= NF; i++) s = s (i == 2 ? "" : " ") $i
        len = length(s)
        if (len < 2 || len > 30) { flush(); next }
        if (n > 0 && off == prev_off + prev_len + 1) {
            buf[n++] = sprintf("0x%06x  %s", off, s)
        } else {
            flush()
            n = 1
            first_off = $1
            buf[0] = sprintf("0x%06x  %s", off, s)
        }
        prev_off = off
        prev_len = len
    }
    END { flush() }
'
