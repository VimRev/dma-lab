#!/usr/bin/env python3
"""
PCIe BAR (Base Address Register) Dump Tool
Reads and displays BAR memory regions for DMA devices.

BARs contain the device's memory-mapped registers and data buffers.
Analyzing BAR contents is essential for:
  - Verifying DMA board firmware is responding
  - Reading device status registers
  - Identifying memory-mapped regions for direct access
  - Debugging firmware issues

Usage:
  python3 bar_dump.py --bus 03:00.0             Dump all BARs for device
  python3 bar_dump.py --bus 03:00.0 --bar 0     Dump only BAR0
  python3 bar_dump.py --bus 03:00.0 --size 256  Dump first 256 bytes per BAR
  python3 bar_dump.py --bus 03:00.0 --offset 0x100 --size 64  Specific region
  python3 bar_dump.py --scan                     Scan for DMA devices and dump
"""

import argparse
import json
import os
import struct
import sys
from pathlib import Path


# ─── Common DMA Register Offsets ──────────────────────────────────────────────
# These are typical register layouts for Xilinx XDMA/QDMA designs.
# Actual layout depends on the specific firmware implementation.
COMMON_DMA_REGS = {
    0x00: "ID / Magic",
    0x04: "Version",
    0x08: "Status",
    0x0C: "Control",
    0x10: "Interrupt Status",
    0x14: "Interrupt Enable",
    0x18: "Interrupt Clear",
    0x1C: "Reserved",
    0x20: "Source Address (Low)",
    0x24: "Source Address (High)",
    0x28: "Destination Address (Low)",
    0x2C: "Destination Address (High)",
    0x30: "Transfer Length",
    0x34: "Transfer Control",
    0x38: "Transfer Status",
    0x3C: "Descriptor Address (Low)",
    0x40: "Descriptor Address (High)",
    0x44: "Descriptor Control",
    0x48: "SG DMA Status",
    0x4C: "SG DMA Control",
    # XDMA-specific offsets
    0x80: "XDMA ID",
    0x84: "XDMA Control",
    0x88: "XDMA Status",
    0x8C: "XDMA IRQ Vector",
    0x90: "XDMA IRQ Mask",
}


def format_hex(value: int, width: int = 8) -> str:
    """Format integer as hex with specified width."""
    return f"0x{value:0{width}X}"


def format_size(size: int) -> str:
    """Format byte count to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size} {unit}"
        size //= 1024
    return f"{size} PB"


def read_bar_resource(bus_addr: str, bar_index: int) -> dict:
    """Read BAR resource information from sysfs."""
    pci_path = Path(f"/sys/bus/pci/devices/{bus_addr}")
    resource_path = pci_path / f"resource{bar_index}"

    if not resource_path.exists():
        return None

    try:
        with open(resource_path, 'r') as f:
            parts = f.read().strip().split()

        if len(parts) < 3:
            return None

        start = int(parts[0], 16)
        end = int(parts[1], 16)
        flags = int(parts[2], 16)

        if start == 0 and end == 0:
            return None

        size = end - start + 1
        is_io = bool(flags & 0x01)
        is_prefetchable = bool(flags & 0x08)
        is_64bit = bool(flags & 0x04)

        return {
            'index': bar_index,
            'start': start,
            'end': end,
            'size': size,
            'flags': flags,
            'is_io': is_io,
            'is_prefetchable': is_prefetchable,
            'is_64bit': is_64bit,
            'type': 'I/O' if is_io else 'Memory',
            'size_human': format_size(size),
        }
    except (ValueError, IndexError, PermissionError) as e:
        return {'index': bar_index, 'error': str(e)}


def read_bar_data(bus_addr: str, bar_index: int, offset: int = 0, size: int = 256) -> bytes:
    """Read raw data from a BAR region via sysfs resource file."""
    resource_path = Path(f"/sys/bus/pci/devices/{bus_addr}/resource{bar_index}")

    if not resource_path.exists():
        return None

    try:
        with open(resource_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)
    except (PermissionError, OSError) as e:
        return None


def read_bar_data_mmap(bus_addr: str, bar_index: int, offset: int = 0, size: int = 256) -> bytes:
    """Read BAR data using mmap for better performance on large reads."""
    import mmap

    resource_path = Path(f"/sys/bus/pci/devices/{bus_addr}/resource{bar_index}")

    if not resource_path.exists():
        return None

    try:
        with open(resource_path, 'rb') as f:
            # Get file size
            f.seek(0, 2)
            file_size = f.tell()

            if offset >= file_size:
                return None

            read_size = min(size, file_size - offset)

            # Use mmap for efficient reading
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                return mm[offset:offset + read_size]
    except (PermissionError, OSError, ValueError) as e:
        # Fall back to regular read
        return read_bar_data(bus_addr, bar_index, offset, size)


def parse_register_value(offset: int, value: int, regs: dict = None) -> str:
    """Parse a register value and provide context."""
    if regs is None:
        regs = COMMON_DMA_REGS

    name = regs.get(offset, "Unknown")

    # Special parsing for known registers
    if offset == 0x00:  # ID / Magic
        # Try to decode as ASCII
        ascii_str = ""
        for i in range(4):
            byte = (value >> (i * 8)) & 0xFF
            if 32 <= byte < 127:
                ascii_str += chr(byte)
            else:
                ascii_str += "."
        if any(32 <= b < 127 for b in [(value >> (i * 8)) & 0xFF for i in range(4)]):
            return f"{name} = {format_hex(value)} (ASCII: '{ascii_str}')"

    elif offset == 0x08 or offset == 0x88:  # Status
        bits = []
        if value & 0x01: bits.append("BUSY")
        if value & 0x02: bits.append("DONE")
        if value & 0x04: bits.append("ERROR")
        if value & 0x08: bits.append("IDLE")
        if bits:
            return f"{name} = {format_hex(value)} [{' | '.join(bits)}]"

    elif offset == 0x0C or offset == 0x84:  # Control
        bits = []
        if value & 0x01: bits.append("START")
        if value & 0x02: bits.append("RESET")
        if value & 0x04: bits.append("IRQ_EN")
        if value & 0x08: bits.append("SG_MODE")
        if bits:
            return f"{name} = {format_hex(value)} [{' | '.join(bits)}]"

    return f"{name} = {format_hex(value)}"


def dump_bar_text(bar_info: dict, data: bytes, offset: int, show_ascii: bool = True,
                  interpret_regs: bool = False):
    """Print BAR data in hex dump format."""
    bar_idx = bar_info['index']
    print(f"\n  BAR{bar_idx} ({bar_info['type']}, {bar_info['size_human']})")
    print(f"  Address: {format_hex(bar_info['start'], 16)} - {format_hex(bar_info['end'], 16)}")
    print(f"  {'─' * 60}")

    if data is None:
        print("  [!] Cannot read BAR data (permission denied or not memory-mapped)")
        print("      Try: sudo python3 bar_dump.py ...")
        return

    if len(data) == 0:
        print("  [!] No data read from BAR")
        return

    print(f"  Offset: 0x{offset:04X}  Size: {len(data)} bytes")
    print()

    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_parts = []
        for j in range(0, len(chunk), 4):
            sub = chunk[j:j+4]
            if len(sub) == 4:
                val = struct.unpack('<I', sub)[0]
                hex_parts.append(f"{val:08X}")
            else:
                hex_parts.append(' '.join(f'{b:02X}' for b in sub))

        hex_str = ' '.join(hex_parts)
        current_offset = offset + i

        # ASCII representation
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

        # Register interpretation
        reg_comment = ""
        if interpret_regs and len(chunk) >= 4:
            val = struct.unpack('<I', chunk[:4])[0]
            reg_comment = f"  ; {parse_register_value(current_offset, val)}"

        print(f"  {current_offset:04X}: {hex_str:<48} |{ascii_str}|{reg_comment}")


def dump_bar_json(bar_info: dict, data: bytes, offset: int) -> dict:
    """Dump BAR data as JSON."""
    result = {
        'bar_index': bar_info['index'],
        'bar_type': bar_info['type'],
        'bar_size': bar_info['size'],
        'bar_start': format_hex(bar_info['start'], 16),
        'read_offset': offset,
        'read_size': len(data) if data else 0,
        'registers': [],
    }

    if data:
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                val = struct.unpack('<I', data[i:i+4])[0]
                result['registers'].append({
                    'offset': format_hex(offset + i, 4),
                    'value': format_hex(val),
                    'name': COMMON_DMA_REGS.get(offset + i, "Unknown"),
                })

    return result


def scan_and_dump(args):
    """Scan for DMA devices and dump their BARs."""
    pci_path = Path("/sys/bus/pci/devices")
    if not pci_path.exists():
        print("[!] /sys/bus/pci/devices not found. Linux only.")
        sys.exit(1)

    print("\n  Scanning for DMA devices...")

    # Xilinx vendor ID
    XILINX_VID = 0x10EE

    found = []
    for dev_dir in sorted(pci_path.iterdir()):
        bus_addr = dev_dir.name
        try:
            with open(dev_dir / 'vendor', 'r') as f:
                vid = int(f.read().strip(), 16)
            with open(dev_dir / 'device', 'r') as f:
                did = int(f.read().strip(), 16)
        except (FileNotFoundError, PermissionError, ValueError):
            continue

        if vid == XILINX_VID:
            found.append((bus_addr, vid, did))
            print(f"  Found: {bus_addr}  Vendor=0x{vid:04X}  Device=0x{did:04X}")

    if not found:
        print("  [-] No Xilinx/DMA devices found")
        print("      Make sure DMA board is inserted and powered on")
        return

    print(f"\n  Found {len(found)} potential DMA device(s)")

    for bus_addr, vid, did in found:
        args.bus = bus_addr
        dump_device_bars(args)


def dump_device_bars(args):
    """Dump BAR data for a specific device."""
    bus_addr = args.bus
    bar_filter = args.bar
    offset = args.offset
    size = args.size

    if not args.json:
        print(f"\n  {'=' * 64}")
        print(f"  DMA Toolkit - PCIe BAR Dump")
        print(f"  Device: {bus_addr}")
        print(f"  {'=' * 64}")

    # Find all BARs
    bars = []
    for i in range(6):
        info = read_bar_resource(bus_addr, i)
        if info and 'error' not in info:
            bars.append(info)

    if not bars:
        if not args.json:
            print(f"\n  [-] No BARs found for {bus_addr}")
            print("      Check that the device exists and you have permissions")
        return

    if not args.json:
        print(f"\n  Found {len(bars)} BAR(s):")
        for bar in bars:
            pfx = "  " if bar['index'] != bar_filter else "> "
            print(f"  {pfx}BAR{bar['index']}: {bar['type']:<8} {bar['size_human']:>10}  "
                  f"({format_hex(bar['start'], 16)} - {format_hex(bar['end'], 16)})"
                  f"{'  [64-bit]' if bar['is_64bit'] else ''}"
                  f"{'  [Prefetchable]' if bar['is_prefetchable'] else ''}")

    # Dump requested BAR(s)
    json_output = []

    for bar in bars:
        if bar_filter is not None and bar['index'] != bar_filter:
            continue

        # Skip I/O BARs (can't mmap them easily)
        if bar['is_io']:
            if not args.json:
                print(f"\n  BAR{bar['index']}: Skipping I/O BAR (memory-mapped only)")
            continue

        data = read_bar_data_mmap(bus_addr, bar['index'], offset, size)

        if args.json:
            json_output.append(dump_bar_json(bar, data, offset))
        else:
            dump_bar_text(
                bar, data, offset,
                show_ascii=not args.no_ascii,
                interpret_regs=args.interpret
            )

    if args.json:
        print(json.dumps(json_output, indent=2))
    else:
        print()
        print("  Tips:")
        print("  - Use --interpret to annotate known register names")
        print("  - Use --offset and --size to read specific regions")
        print("  - Run as root if permission denied")
        print("  Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


def main():
    parser = argparse.ArgumentParser(
        description="PCIe BAR Dump Tool for DMA Devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --bus 03:00.0                   Dump all BARs
  %(prog)s --bus 03:00.0 --bar 0           Dump BAR0 only
  %(prog)s --bus 03:00.0 --bar 0 --size 4K Dump first 4K of BAR0
  %(prog)s --bus 03:00.0 --interpret       Annotate with register names
  %(prog)s --scan                          Scan and dump all DMA devices
        """
    )
    parser.add_argument('--bus', '-b', help='PCIe bus address (e.g., 03:00.0)')
    parser.add_argument('--bar', type=int, help='BAR index to dump (0-5)')
    parser.add_argument('--offset', '-o', type=lambda x: int(x, 0), default=0,
                        help='Offset to start reading (hex or decimal)')
    parser.add_argument('--size', '-s', default='256',
                        help='Number of bytes to read (supports K/M suffix)')
    parser.add_argument('--scan', action='store_true', help='Scan for DMA devices and dump')
    parser.add_argument('--interpret', '-i', action='store_true',
                        help='Annotate registers with known names')
    parser.add_argument('--no-ascii', action='store_true', help='Hide ASCII column')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Parse size with K/M suffix
    size_str = args.size.upper()
    if size_str.endswith('K'):
        args.size = int(size_str[:-1]) * 1024
    elif size_str.endswith('M'):
        args.size = int(size_str[:-1]) * 1024 * 1024
    else:
        args.size = int(size_str)

    if args.scan:
        scan_and_dump(args)
    elif args.bus:
        dump_device_bars(args)
    else:
        parser.print_help()
        print("\n  Tip: Use --scan to auto-detect DMA devices, or --bus to specify one")
        sys.exit(1)


if __name__ == '__main__':
    main()
