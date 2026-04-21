#!/usr/bin/env python3
"""decode_jumptable.py — reconstruct an ARM64 compiled-switch jump table.

Given an `otool -arch arm64e -tV <binary>` dump, an anchor VA (the `adr`
instruction that computes the PC-relative base), and a table VA range,
print `index -> case_VA` rows.

Case labels can be cross-referenced against literal-pool "add" comments
in the same dump to recover `index -> case_VA -> name` mappings.

Usage:
    decode_jumptable.py DISASM_FILE ANCHOR_VA TABLE_START TABLE_END

Example:
    decode_jumptable.py disasm.txt 0x10000a120 0x10000a3ec 0x10000a478
"""
import re
import sys


def parse_udf(line: str):
    """Return the udf immediate value from a disassembly line, or None."""
    m = re.search(r"\budf\s+#(?:0x)?([0-9a-fA-F]+)", line)
    if not m:
        return None
    v = m.group(1)
    return int(v, 16 if line.find("0x") != -1 and line.find("#0x") != -1 else 16) if v.lower().startswith('0') and 'x' in line[:line.find('udf')+10] else int(v, 16) if any(c in 'abcdef' for c in v.lower()) else int(v)


def parse_line_va(line: str):
    m = re.match(r"\s*([0-9a-fA-F]{8,})\s+", line)
    return int(m.group(1), 16) if m else None


def main():
    if len(sys.argv) != 5:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    disasm_path = sys.argv[1]
    anchor_va = int(sys.argv[2], 16)
    tbl_start = int(sys.argv[3], 16)
    tbl_end = int(sys.argv[4], 16)

    entries = []
    with open(disasm_path) as f:
        for line in f:
            va = parse_line_va(line)
            if va is None or not (tbl_start <= va < tbl_end):
                continue
            m = re.search(r"udf\s+#(0x[0-9a-fA-F]+|\d+)", line)
            if not m:
                continue
            val_s = m.group(1)
            val = int(val_s, 16) if val_s.startswith("0x") else int(val_s)
            entries.append((va, val))

    if not entries:
        print("no udf entries in range; is this really a jump table?", file=sys.stderr)
        sys.exit(1)

    # Each udf entry is a 32-bit signed offset from anchor_va
    print(f"anchor_va = 0x{anchor_va:x}")
    print(f"table:    0x{tbl_start:x} .. 0x{tbl_end:x} ({len(entries)} entries)")
    print()
    print(f"{'idx':>4}  {'entry_va':>12}  {'offset':>8}  {'case_va':>12}")

    # Deduplicate by case_va to flag reserved-slot collapses
    seen = {}
    for idx, (entry_va, off) in enumerate(entries):
        case_va = anchor_va + off
        dup = seen.setdefault(case_va, idx)
        marker = "" if dup == idx else f"  (== idx {dup})"
        print(f"{idx:>4}  0x{entry_va:010x}  0x{off:06x}  0x{case_va:010x}{marker}")


if __name__ == "__main__":
    main()
