#!/usr/bin/env python3
"""
DMA Device Checker
Verifies DMA board connection and basic functionality.
Requires PCILeech to be installed and accessible.
"""

import subprocess
import sys
import os
import shutil


def find_pcileech():
    """Find PCILeech executable."""
    # Common locations
    locations = [
        'pcileech',
        'pcileech.exe',
        os.path.expanduser('~/pcileech/pcileech'),
        os.path.expanduser('~/pcileech/pcileech.exe'),
        '/usr/local/bin/pcileech',
        'C:\\pcileech\\pcileech.exe',
    ]

    # Check PATH
    path = shutil.which('pcileech')
    if path:
        return path

    # Check common locations
    for loc in locations:
        if os.path.isfile(loc):
            return loc

    return None


def check_device(pcileech_path):
    """Run PCILeech device info check."""
    print(f"[*] Using PCILeech: {pcileech_path}")
    print("[*] Checking device connection...")

    try:
        result = subprocess.run(
            [pcileech_path, '-device', 'FPGA', '-info', '-verbosity', '1'],
            capture_output=True, text=True, timeout=30
        )

        print("\n--- PCILeech Output ---")
        print(result.stdout)
        if result.stderr:
            print("--- stderr ---")
            print(result.stderr)
        print("--- End Output ---\n")

        # Check for success indicators
        output = result.stdout + result.stderr
        if 'success' in output.lower() or 'device' in output.lower():
            print("[+] Device appears to be connected!")
            return True
        elif 'error' in output.lower() or 'failed' in output.lower():
            print("[-] Device connection failed")
            return False
        else:
            print("[?] Unknown status - check output above")
            return None

    except FileNotFoundError:
        print(f"[!] PCILeech not found at: {pcileech_path}")
        return False
    except subprocess.TimeoutExpired:
        print("[!] Connection timed out (30s)")
        print("    - Check if DMA board is powered and seated properly")
        print("    - Try: -device fpga://algo=2")
        return False
    except Exception as e:
        print(f"[!] Error: {e}")
        return False


def main():
    print("=" * 60)
    print("  DMA Toolkit - Device Checker")
    print("=" * 60)
    print()

    # Find PCILeech
    pcileech = find_pcileech()

    if not pcileech:
        print("[!] PCILeech not found!")
        print()
        print("Please install PCILeech:")
        print("  https://github.com/ufrisk/pcileech")
        print()
        print("Or specify the path manually:")
        print(f"  python3 {sys.argv[0]} /path/to/pcileech")
        sys.exit(1)

    # Allow manual path
    if len(sys.argv) > 1:
        pcileech = sys.argv[1]

    # Run check
    result = check_device(pcileech)

    print()
    print("=" * 60)
    if result is True:
        print("  Status: CONNECTED ✓")
    elif result is False:
        print("  Status: NOT CONNECTED ✗")
    else:
        print("  Status: UNKNOWN ?")
    print("=" * 60)

    print()
    print("Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


if __name__ == '__main__':
    main()
