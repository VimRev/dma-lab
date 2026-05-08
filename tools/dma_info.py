#!/usr/bin/env python3
"""
DMA Hardware Info Reader
Reads and displays detailed hardware information for DMA boards via PCIe configuration space.

Works with:
  - Linux: Direct sysfs access (/sys/bus/pci/devices/)
  - Windows: PowerShell WMI queries
  - Cross-platform: PCILeech if available

Usage:
  python3 dma_info.py                     Auto-detect DMA devices
  python3 dma_info.py --bus 03:00.0       Read info for specific PCIe device
  python3 dma_info.py --all               Show all PCIe devices
  python3 dma_info.py --json              Output as JSON
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


# ─── Known DMA Device IDs ─────────────────────────────────────────────────────
# Xilinx vendor ID
VENDOR_XILINX = 0x10EE

# Known DMA-related device IDs
DMA_DEVICES = {
    # Xilinx FPGA development boards
    0x0007: "Virtex-7 PCIe Gen2/Gen3 Design",
    0x7011: "Xilinx PCIe DMA Bridge",
    0x7012: "Xilinx PCIe DMA Endpoint",
    0x7014: "Xilinx QDMA (Queue-based DMA)",
    0x7021: "Xilinx PCIe DMA/Bridge Subsystem",
    0x7022: "Xilinx PCIe DMA/Bridge Subsystem (Gen3)",
    0x8011: "Xilinx Alveo / UltraScale+ DMA",
    # Custom DMA boards (common FPGA IDs)
    0x0666: "Custom DMA (PCILeech compatible)",
    0x1337: "Custom DMA (screamer/enigma style)",
    0xAAAA: "Custom DMA (development/testing)",
}

# DMA board families
DMA_BOARD_FAMILIES = {
    "screamer": {
        "name": "Screamer",
        "variants": ["Screamer Squirrel", "PCIeScreamer R2", "PCIeScreamer R1"],
        "fpga": "Artix-7",
        "interface": "FT601 USB 3.0",
    },
    "enigma": {
        "name": "Enigma",
        "variants": ["Enigma X1", "Enigma X2"],
        "fpga": "Artix-7",
        "interface": "FT601 USB 3.0",
    },
    "leechcore": {
        "name": "LeechCore Generic",
        "variants": ["FT601-based", "FT2232H-based"],
        "fpga": "Various",
        "interface": "FTDI",
    },
    "xilinx_dev": {
        "name": "Xilinx Development Board",
        "variants": ["KC705", "VC709", "AU200", "AU280"],
        "fpga": "Various",
        "interface": "PCIe",
    },
}


class PCIeDevice:
    """Represents a single PCIe device with its configuration space data."""

    def __init__(self, bus_addr: str):
        self.bus_addr = bus_addr
        self.vendor_id = None
        self.device_id = None
        self.class_code = None
        self.class_name = ""
        self.subsystem_vendor = None
        self.subsystem_device = None
        self.revision = None
        self.bar_sizes = []
        self.bar_types = []
        self.link_speed = None
        self.link_width = None
        self.driver = ""
        self.device_name = ""
        self.is_dma = False
        self.raw_config = {}

    def to_dict(self):
        return {
            'bus_addr': self.bus_addr,
            'vendor_id': f"0x{self.vendor_id:04X}" if self.vendor_id else None,
            'device_id': f"0x{self.device_id:04X}" if self.device_id else None,
            'class_code': f"0x{self.class_code:06X}" if self.class_code else None,
            'class_name': self.class_name,
            'subsystem_vendor': f"0x{self.subsystem_vendor:04X}" if self.subsystem_vendor else None,
            'subsystem_device': f"0x{self.subsystem_device:04X}" if self.subsystem_device else None,
            'revision': self.revision,
            'bar_sizes': self.bar_sizes,
            'link_speed': self.link_speed,
            'link_width': self.link_width,
            'driver': self.driver,
            'device_name': self.device_name,
            'is_dma': self.is_dma,
        }


def read_sysfs_hex(path: str) -> int:
    """Read a hex value from a sysfs file."""
    try:
        with open(path, 'r') as f:
            return int(f.read().strip(), 16)
    except (FileNotFoundError, PermissionError, ValueError):
        return -1


def read_sysfs_str(path: str) -> str:
    """Read a string from a sysfs file."""
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError):
        return ""


def read_bar_sizes_linux(bus_addr: str) -> list:
    """Read BAR sizes from sysfs on Linux."""
    bars = []
    pci_path = Path(f"/sys/bus/pci/devices/{bus_addr}")

    for i in range(6):
        resource_path = pci_path / f"resource{i}"
        if resource_path.exists():
            try:
                with open(resource_path, 'r') as f:
                    lines = f.readlines()
                if lines:
                    # Format: start end flags
                    parts = lines[0].strip().split()
                    if len(parts) >= 2:
                        start = int(parts[0], 16)
                        end = int(parts[1], 16)
                        size = end - start + 1
                        if size > 0 and start != 0:
                            bar_type = "IO" if (start & 0x01) else "Memory"
                            bars.append({
                                'index': i,
                                'start': start,
                                'end': end,
                                'size': size,
                                'size_human': format_size(size),
                                'type': bar_type,
                            })
            except (ValueError, IndexError):
                pass

    return bars


def format_size(size: int) -> str:
    """Format byte count to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size} {unit}"
        size //= 1024
    return f"{size} TB"


def get_link_info_linux(bus_addr: str) -> dict:
    """Read PCIe link speed and width from sysfs."""
    pci_path = Path(f"/sys/bus/pci/devices/{bus_addr}")

    speed = read_sysfs_str(pci_path / "current_link_speed")
    width = read_sysfs_str(pci_path / "current_link_width")
    max_speed = read_sysfs_str(pci_path / "max_link_speed")
    max_width = read_sysfs_str(pci_path / "max_link_width")

    return {
        'current_speed': speed or "Unknown",
        'current_width': width or "Unknown",
        'max_speed': max_speed or "Unknown",
        'max_width': max_width or "Unknown",
    }


def classify_device(vendor_id: int, device_id: int, class_code: int) -> tuple:
    """Classify a device and determine if it might be DMA hardware."""
    is_dma = False
    name = ""

    # Check class code: 0x068000 = Other bridge, 0x058000 = Other memory controller
    class_major = (class_code >> 16) & 0xFF
    class_sub = (class_code >> 8) & 0xFF

    # DMA devices are often classified as "Other" bridge or memory controller
    if class_major == 0x06 and class_sub == 0x80:
        is_dma = True  # "Other bridge device"

    # Check against known DMA device IDs
    if device_id in DMA_DEVICES:
        name = DMA_DEVICES[device_id]
        is_dma = True

    # Check for Xilinx vendor
    if vendor_id == VENDOR_XILINX:
        if not name:
            name = f"Xilinx Device (0x{device_id:04X})"
        is_dma = True

    return is_dma, name


def get_class_name(class_code: int) -> str:
    """Convert PCI class code to human-readable name."""
    major = (class_code >> 16) & 0xFF
    sub = (class_code >> 8) & 0xFF

    classes = {
        0x00: {0x00: "Legacy Device", 0x01: "VGA-Compatible Device"},
        0x01: {0x00: "SCSI Controller", 0x01: "IDE Controller", 0x02: "Floppy Controller",
               0x03: "IPI Controller", 0x04: "RAID Controller", 0x05: "ATA Controller",
               0x06: "SATA Controller", 0x07: "SAS Controller", 0x08: "NVMe Controller"},
        0x02: {0x00: "Ethernet Controller", 0x01: "Token Ring Controller",
               0x02: "FDDI Controller", 0x03: "ATM Controller", 0x04: "ISDN Controller",
               0x05: "WorldFip Controller", 0x06: "PICMG Controller", 0x07: "InfiniBand Controller",
               0x08: "Fabric Controller"},
        0x03: {0x00: "VGA Controller", 0x01: "XGA Controller", 0x02: "3D Controller"},
        0x04: {0x00: "Multimedia Controller", 0x01: "Audio Controller", 0x02: "Video Controller"},
        0x05: {0x00: "RAM Controller", 0x01: "Flash Controller"},
        0x06: {0x00: "Host Bridge", 0x01: "ISA Bridge", 0x02: "EISA Bridge",
               0x03: "MCA Bridge", 0x04: "PCI-to-PCI Bridge", 0x05: "PCMCIA Bridge",
               0x06: "NuBus Bridge", 0x07: "CardBus Bridge", 0x08: "RACEway Bridge",
               0x09: "Semi-transparent PCI-to-PCI Bridge", 0x0A: "InfiniBand-to-PCI Bridge",
               0x80: "Other Bridge Device"},
        0x07: {0x00: "Serial Controller", 0x01: "Parallel Controller", 0x02: "Multiport Serial",
               0x03: "Modem", 0x04: "GPIB Controller", 0x05: "Smart Card Controller"},
        0x08: {0x00: "PIC", 0x01: "DMA Controller", 0x02: "Timer", 0x03: "RTC Controller"},
        0x09: {0x00: "Keyboard Controller", 0x01: "Digitizer Pen", 0x02: "Mouse Controller"},
        0x0C: {0x03: "USB Controller", 0x04: "Fibre Channel", 0x05: "SMBus Controller"},
        0x12: {0x00: "Processing Accelerator"},
    }

    if major in classes and sub in classes[major]:
        return classes[major][sub]
    if major in classes and 0x80 in classes[major]:
        return classes[major][0x80]
    return f"Class 0x{major:02X}, Sub 0x{sub:02X}"


def scan_linux(json_output: bool = False, show_all: bool = False) -> list:
    """Scan PCIe devices on Linux via sysfs."""
    devices = []
    pci_base = Path("/sys/bus/pci/devices")

    if not pci_base.exists():
        print("[!] /sys/bus/pci/devices not found. Is this Linux?")
        return devices

    for dev_dir in sorted(pci_base.iterdir()):
        bus_addr = dev_dir.name

        dev = PCIeDevice(bus_addr)
        dev.vendor_id = read_sysfs_hex(dev_dir / "vendor")
        dev.device_id = read_sysfs_hex(dev_dir / "device")
        dev.class_code = read_sysfs_hex(dev_dir / "class")
        dev.revision = read_sysfs_hex(dev_dir / "revision")
        dev.subsystem_vendor = read_sysfs_hex(dev_dir / "subsystem_vendor")
        dev.subsystem_device = read_sysfs_hex(dev_dir / "subsystem_device")

        if dev.vendor_id < 0:
            continue

        # Get class name
        if dev.class_code >= 0:
            dev.class_name = get_class_name(dev.class_code)

        # Classify device
        if dev.class_code >= 0:
            dev.is_dma, dev.device_name = classify_device(
                dev.vendor_id, dev.device_id, dev.class_code
            )

        # Get driver
        driver_link = dev_dir / "driver"
        if driver_link.exists():
            try:
                dev.driver = os.readlink(driver_link).name
            except OSError:
                pass

        # Get BAR info for DMA devices
        if dev.is_dma or show_all:
            dev.bar_sizes = read_bar_sizes_linux(bus_addr)
            link_info = get_link_info_linux(bus_addr)
            dev.link_speed = link_info['current_speed']
            dev.link_width = link_info['current_width']

        devices.append(dev)

    return devices


def scan_windows(json_output: bool = False, show_all: bool = False) -> list:
    """Scan PCIe devices on Windows via PowerShell."""
    devices = []

    ps_cmd = (
        "Get-CimInstance -ClassName Win32_PnPEntity | "
        "Where-Object { $_.PNPDeviceID -match '^PCI\\\\' } | "
        "Select-Object Name, PNPDeviceID, Status, ConfigManagerErrorCode | "
        "ConvertTo-Json -Compress"
    )

    try:
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[!] PowerShell error: {result.stderr}")
            return devices

        raw = json.loads(result.stdout)
        if isinstance(raw, dict):
            raw = [raw]

        for item in raw:
            pnp_id = item.get('PNPDeviceID', '')
            # Parse vendor/device from PNP ID: PCI\VEN_XXXX&DEV_XXXX
            ven_match = re.search(r'VEN_([0-9A-Fa-f]{4})', pnp_id)
            dev_match = re.search(r'DEV_([0-9A-Fa-f]{4})', pnp_id)

            if not ven_match or not dev_match:
                continue

            dev = PCIeDevice(pnp_id)
            dev.vendor_id = int(ven_match.group(1), 16)
            dev.device_id = int(dev_match.group(1), 16)
            dev.device_name = item.get('Name', 'Unknown')
            dev.is_dma, _ = classify_device(dev.vendor_id, dev.device_id, 0)
            dev.raw_config = item

            devices.append(dev)

    except FileNotFoundError:
        print("[!] PowerShell not found. Are you on Windows?")
    except subprocess.TimeoutExpired:
        print("[!] PowerShell query timed out")
    except json.JSONDecodeError as e:
        print(f"[!] Failed to parse PowerShell output: {e}")

    return devices


def print_device(dev: PCIeDevice, verbose: bool = False):
    """Print formatted device information."""
    marker = " *** DMA ***" if dev.is_dma else ""
    print(f"\n  {dev.bus_addr}  {dev.device_name or 'Unknown Device'}{marker}")
    print(f"  {'─' * 56}")

    if dev.vendor_id is not None:
        print(f"    Vendor:    0x{dev.vendor_id:04X}", end="")
        if dev.vendor_id == VENDOR_XILINX:
            print(" (Xilinx)", end="")
        print()

    if dev.device_id is not None:
        print(f"    Device:    0x{dev.device_id:04X}")
        if dev.device_id in DMA_DEVICES:
            print(f"    Type:      {DMA_DEVICES[dev.device_id]}")

    if dev.class_name:
        print(f"    Class:     {dev.class_name}")

    if dev.revision is not None:
        print(f"    Revision:  0x{dev.revision:02X}")

    if dev.subsystem_vendor is not None and dev.subsystem_vendor >= 0:
        print(f"    Subsys:    {dev.subsystem_vendor:04X}:{dev.subsystem_device:04X}")

    if dev.driver:
        print(f"    Driver:    {dev.driver}")

    if dev.link_speed:
        print(f"    Link:      {dev.link_speed} x{dev.link_width}")

    if dev.bar_sizes:
        print(f"    BARs:")
        for bar in dev.bar_sizes:
            print(f"      BAR{bar['index']}: {bar['size_human']:>10}  ({bar['type']})")

    if verbose and dev.raw_config:
        print(f"    Raw:       {json.dumps(dev.raw_config, indent=6)}")


def main():
    parser = argparse.ArgumentParser(
        description="DMA Hardware Info Reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         Auto-detect DMA devices
  %(prog)s --all                   Show all PCIe devices
  %(prog)s --bus 03:00.0           Show info for specific device
  %(prog)s --json                  Output as JSON
  %(prog)s -v --all                Verbose output for all devices
        """
    )
    parser.add_argument('--bus', '-b', help='PCIe bus address (e.g., 03:00.0)')
    parser.add_argument('--all', '-a', action='store_true', help='Show all PCIe devices')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if not args.json:
        print("=" * 64)
        print("  DMA Toolkit - Hardware Info Reader")
        print("=" * 64)

    # Scan devices
    if sys.platform.startswith('linux'):
        devices = scan_linux(json_output=args.json, show_all=args.all)
    elif sys.platform == 'win32':
        devices = scan_windows(json_output=args.json, show_all=args.all)
    else:
        print("[!] Unsupported OS")
        sys.exit(1)

    if not devices:
        if not args.json:
            print("\n  [-] No PCIe devices found")
        sys.exit(1)

    # Filter by bus address if specified
    if args.bus:
        devices = [d for d in devices if d.bus_addr.startswith(args.bus)]
        if not devices:
            print(f"\n  [-] No device found at bus {args.bus}")
            sys.exit(1)

    # Filter to DMA devices unless --all
    if not args.all:
        dma_devices = [d for d in devices if d.is_dma]
        if dma_devices:
            devices = dma_devices
        else:
            if not args.json:
                print("\n  [-] No DMA devices detected")
                print("      Use --all to show all PCIe devices")

    # Output
    if args.json:
        output = [d.to_dict() for d in devices]
        print(json.dumps(output, indent=2))
    else:
        dma_count = sum(1 for d in devices if d.is_dma)
        total = len(devices)
        print(f"\n  Found {total} device(s) ({dma_count} potential DMA)")

        for dev in devices:
            print_device(dev, verbose=args.verbose)

        print()
        if dma_count > 0:
            print(f"  Detected {dma_count} potential DMA device(s)")
        print("  Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


if __name__ == '__main__':
    main()
