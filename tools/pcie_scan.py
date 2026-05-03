#!/usr/bin/env python3
"""
PCIe Bus Scanner
Lists all PCIe devices connected to the system.
Useful for verifying DMA board enumeration.
"""

import subprocess
import sys
import re


def scan_pcie_linux():
    """Scan PCIe devices on Linux using lspci."""
    try:
        result = subprocess.run(
            ['lspci', '-vvv', '-mm'],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except FileNotFoundError:
        print("[!] lspci not found. Install pciutils package.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"[!] Error running lspci: {e}")
        return None


def scan_pcie_windows():
    """Scan PCIe devices on Windows using PowerShell."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-PnpDevice -Class System | Where-Object {$_.InstanceId -match "PCI"} | Select-Object Status,InstanceId,FriendlyName | Format-Table -AutoSize'],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except Exception as e:
        print(f"[!] Error scanning PCIe: {e}")
        return None


def find_dma_devices(output):
    """Look for known DMA device signatures in PCIe output."""
    dma_signatures = [
        'Xilinx',
        'Artix',
        'Spartan',
        'Screamer',
        'Enigma',
        'DMA',
        'FPGA',
        '0x10ee',  # Xilinx vendor ID
    ]

    found = []
    for line in output.split('\n'):
        for sig in dma_signatures:
            if sig.lower() in line.lower():
                found.append(line.strip())
                break

    return found


def main():
    print("=" * 60)
    print("  DMA Toolkit - PCIe Bus Scanner")
    print("=" * 60)
    print()

    # Detect OS and scan
    if sys.platform.startswith('linux'):
        print("[*] Scanning PCIe bus (Linux)...")
        output = scan_pcie_linux()
    elif sys.platform == 'win32':
        print("[*] Scanning PCIe bus (Windows)...")
        output = scan_pcie_windows()
    else:
        print("[!] Unsupported OS")
        sys.exit(1)

    if not output:
        print("[!] Failed to scan PCIe bus")
        sys.exit(1)

    # Look for DMA devices
    print("\n[*] Looking for DMA/FPGA devices...")
    dma_devices = find_dma_devices(output)

    if dma_devices:
        print(f"\n[+] Found {len(dma_devices)} potential DMA device(s):")
        print("-" * 60)
        for dev in dma_devices:
            print(f"  {dev}")
        print("-" * 60)
    else:
        print("\n[-] No known DMA devices found")
        print("    Possible reasons:")
        print("    - DMA board not inserted or powered off")
        print("    - Board not enumerated by BIOS/OS")
        print("    - Custom firmware with different signatures")

    # Show all PCIe devices
    print("\n[*] All PCIe devices:")
    print("-" * 60)
    print(output[:2000])  # Limit output length
    if len(output) > 2000:
        print(f"\n... ({len(output) - 2000} more characters)")
    print("-" * 60)

    # Tips
    print("\n[*] Tips:")
    print("  - If DMA board not found, try a different PCIe slot")
    print("  - Check Device Manager (Windows) or dmesg (Linux)")
    print("  - Verify FPGA firmware is properly flashed")
    print()
    print("Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


if __name__ == '__main__':
    main()
