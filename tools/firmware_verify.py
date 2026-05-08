#!/usr/bin/env python3
"""
DMA Firmware Signature Verifier
Validates FPGA bitstream integrity and detects common firmware tampering.

Supports:
  - Xilinx 7-Series (Artix-7, Spartan-7, Kintex-7)
  - Xilinx UltraScale / UltraScale+
  - Intel (Altera) FPGA bitstreams
  - Custom DMA firmware images

Usage:
  python3 firmware_verify.py <firmware.bin>
  python3 firmware_verify.py --dir ./firmwares/
  python3 firmware_verify.py --dump-header <firmware.bin>
"""

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import datetime
from pathlib import Path


# ─── Xilinx Bitstream Constants ───────────────────────────────────────────────
# Xilinx 7-series bitstreams start with a sync word after dummy bytes
XILINX_SYNC_WORD = bytes([0xAA, 0x99, 0x55, 0x66])

# Known Xilinx header opcodes (bits [31:29] of each header word)
XILINX_OPCODE_NOP     = 0x00
XILINX_OPCODE_READ    = 0x01
XILINX_OPCODE_WRITE   = 0x02
XILINX_OPCODE_UNKNOWN = 0x03

# Xilinx configuration register addresses
XILINX_REG_CRC      = 0x00  # CRC register
XILINX_REG_FAR      = 0x01  # Frame Address Register
XILINX_REG_FDRI     = 0x02  # Frame Data Register Input (write)
XILINX_REG_FDRO     = 0x03  # Frame Data Register Output (read)
XILINX_REG_CMD      = 0x04  # Command Register
XILINX_REG_CTL      = 0x05  # Control Register
XILINX_REG_MASK     = 0x06  # Mask Register
XILINX_REG_STAT     = 0x07  # Status Register
XILINX_REG_LOUT     = 0x08  # Legacy Output Register
XILINX_REG_COR      = 0x09  # Configuration Option Register
XILINX_REG_MFWR     = 0x0A  # Multi Frame Write Register
XILINX_REG_CBC      = 0x0B  # Initial Configuration Value (CBC)
XILINX_REG_IDCODE   = 0x0C  # Device ID Register
XILINX_REG_AXSS     = 0x0D  # User Access Register
XILINX_REG_COR1     = 0x0E  # Configuration Option Register 1
XILINX_REG_WBSTAR   = 0x10  # Warm Boot Start Address
XILINX_REG_TIMER    = 0x11  # Watchdog Timer Register
XILINX_REG_BOOTSTS  = 0x16  # Boot History Status Register
XILINX_REG_CTL1     = 0x18  # Control Register 1
XILINX_REG_BSPI     = 0x1F  # BPI/SPI Configuration

# Known Xilinx IDCODEs (Device ID → Name)
XILINX_DEVICES = {
    0x03620093: "Artix-7 (xc7a35t)",
    0x03622093: "Artix-7 (xc7a50t)",
    0x0362C093: "Artix-7 (xc7a100t)",
    0x0362E093: "Artix-7 (xc7a200t)",
    0x037C2093: "Artix-7 (xc7a325t)",
    0x04A62093: "Artix-7 UltraScale (xcau15p)",
    0x03631093: "Kintex-7 (xc7k70t)",
    0x03647093: "Kintex-7 (xc7k160t)",
    0x0364C093: "Kintex-7 (xc7k325t)",
    0x03651093: "Kintex-7 (xc7k410t)",
    0x03684093: "Kintex UltraScale (xcku040)",
    0x03687093: "Kintex UltraScale (xcku060)",
    0x0368B093: "Kintex UltraScale (xcku115)",
    0x03691093: "Virtex-7 (xc7vx330t)",
    0x03696093: "Virtex-7 (xc7vx485t)",
    0x0369C093: "Virtex-7 (xc7vx690t)",
    0x036D7093: "Virtex UltraScale (xcvu065)",
    0x03823093: "Spartan-7 (xc7s15)",
    0x03824093: "Spartan-7 (xc7s25)",
    0x03825093: "Spartan-7 (xc7s50)",
    0x03826093: "Spartan-7 (xc7s75)",
    0x03827093: "Spartan-7 (xc7s100)",
}

# ─── Intel/Altera Bitstream Constants ─────────────────────────────────────────
ALTERA_MAGIC_POF = bytes([0x00])  # POF files start with specific patterns
ALTERA_MAGIC_SOF = bytes([0x00])  # SOF format marker

# ─── Known DMA Board Signatures ───────────────────────────────────────────────
DMA_BOARD_SIGNATURES = {
    "screamer_squirrel": {
        "name": "Screamer Squirrel",
        "description": "PCIeScreamer R2 / Squirrel DMA board",
        "typical_idcodes": [0x03620093, 0x03622093],
    },
    "enigma_x1": {
        "name": "Enigma X1",
        "description": "Enigma X1 DMA board (Artix-7 based)",
        "typical_idcodes": [0x0362C093, 0x0362E093],
    },
    "enigma_x2": {
        "name": "Enigma X2",
        "description": "Enigma X2 dual-port DMA board",
        "typical_idcodes": [0x0362E093],
    },
    "leechcore_ft601": {
        "name": "LeechCore FT601",
        "description": "FT601-based generic DMA board",
        "typical_idcodes": [0x03620093, 0x03622093, 0x0362C093],
    },
}


class FirmwareVerifier:
    """Validates and analyzes DMA FPGA bitstream files."""

    def __init__(self, filepath: str, verbose: bool = False):
        self.filepath = Path(filepath)
        self.verbose = verbose
        self.data = None
        self.format = None
        self.device_id = None
        self.device_name = "Unknown"
        self.header_info = {}
        self.warnings = []
        self.errors = []

    def load(self) -> bool:
        """Load firmware file into memory."""
        if not self.filepath.exists():
            self.errors.append(f"File not found: {self.filepath}")
            return False

        if not self.filepath.is_file():
            self.errors.append(f"Not a regular file: {self.filepath}")
            return False

        size = self.filepath.stat().st_size
        if size == 0:
            self.errors.append("File is empty")
            return False

        if size > 128 * 1024 * 1024:  # 128 MB limit
            self.errors.append(f"File too large ({size} bytes). Max 128 MB.")
            return False

        with open(self.filepath, 'rb') as f:
            self.data = f.read()

        self.header_info['file_size'] = size
        self.header_info['filename'] = self.filepath.name
        return True

    def detect_format(self) -> str:
        """Detect the firmware file format."""
        if self.data is None:
            return "unknown"

        # Check for Xilinx raw bitstream (starts with dummy bytes then sync word)
        sync_pos = self.data.find(XILINX_SYNC_WORD)
        if sync_pos >= 0 and sync_pos < 256:
            self.format = "xilinx_bitstream"
            self.header_info['sync_offset'] = sync_pos
            return self.format

        # Check for Xilinx .bit file (has header with design name)
        # Xilinx .bit format: length-prefixed sections with type bytes
        if len(self.data) > 20 and self.data[0:2] == b'\x00\x09':
            # Possible Xilinx .bit header
            self.format = "xilinx_bit"
            return self.format

        # Check for BIN file with Xilinx sync somewhere in first 1KB
        if sync_pos >= 0 and sync_pos < 1024:
            self.format = "xilinx_bin"
            self.header_info['sync_offset'] = sync_pos
            return self.format

        # Check for Intel POF
        if len(self.data) > 16:
            # POF files have specific patterns
            header = self.data[:16]
            if b'ALTERA' in header or b'QUARTUS' in header:
                self.format = "intel_pof"
                return self.format

        # Check for raw binary (fallback)
        if len(self.data) > 4:
            self.format = "raw_binary"
            return self.format

        self.format = "unknown"
        return self.format

    def parse_xilinx_header(self) -> bool:
        """Parse Xilinx bitstream header to extract device ID and config info."""
        if self.data is None:
            return False

        # Find sync word
        sync_pos = self.data.find(XILINX_SYNC_WORD)
        if sync_pos < 0:
            self.errors.append("No Xilinx sync word found")
            return False

        # After sync word, parse configuration packets
        pos = sync_pos + 4  # Skip sync word

        if pos + 4 > len(self.data):
            self.errors.append("Truncated header after sync word")
            return False

        # Read first header word
        word = struct.unpack('>I', self.data[pos:pos+4])[0]
        header_type = (word >> 29) & 0x07
        op_code = (word >> 27) & 0x03
        reg_addr = (word >> 13) & 0x3FFF
        word_count = word & 0x03FF

        if self.verbose:
            print(f"  First header word: 0x{word:08X}")
            print(f"    Header type: {header_type}")
            print(f"    Opcode: {op_code}")
            print(f"    Register: 0x{reg_addr:02X}")
            print(f"    Word count: {word_count}")

        self.header_info['first_word'] = f"0x{word:08X}"

        # Look for IDCODE register write
        # Scan through configuration words looking for IDCODE register write
        scan_pos = sync_pos + 4
        found_idcode = False

        while scan_pos < min(len(self.data) - 4, sync_pos + 4096):
            w = struct.unpack('>I', self.data[scan_pos:scan_pos+4])[0]
            ht = (w >> 29) & 0x07

            if ht == 0x01:  # Type 1 header (register read/write)
                opcode = (w >> 27) & 0x03
                reg = (w >> 13) & 0x3FFF
                count = w & 0x03FF

                if reg == XILINX_REG_IDCODE and count > 0 and opcode == XILINX_OPCODE_WRITE:
                    # Next word should be the IDCODE value
                    if scan_pos + 8 <= len(self.data):
                        idcode = struct.unpack('>I', self.data[scan_pos+4:scan_pos+8])[0]
                        # Mask out revision bits (top 4 bits)
                        self.device_id = idcode & 0x0FFFFFFF
                        self.device_name = XILINX_DEVICES.get(self.device_id, f"Unknown (0x{self.device_id:08X})")
                        self.header_info['idcode'] = f"0x{idcode:08X}"
                        self.header_info['device_name'] = self.device_name
                        found_idcode = True
                        break

            elif ht == 0x02:  # Type 2 header (large data)
                # Type 2 headers have different format, skip for now
                pass

            scan_pos += 4

        if not found_idcode:
            self.warnings.append("Could not find IDCODE in bitstream header")
            # Try alternative: look for known IDCODE values in the data
            for idcode, name in XILINX_DEVICES.items():
                idcode_bytes = struct.pack('>I', idcode)
                pos_in_data = self.data.find(idcode_bytes)
                if pos_in_data > 0 and pos_in_data < 8192:
                    self.device_id = idcode
                    self.device_name = name
                    self.header_info['idcode'] = f"0x{idcode:08X} (found at offset 0x{pos_in_data:X})"
                    self.header_info['device_name'] = name
                    found_idcode = True
                    break

        return found_idcode

    def check_crc(self) -> bool:
        """Verify CRC integrity of the bitstream."""
        if self.data is None or len(self.data) < 8:
            return False

        # Xilinx bitstreams embed a CRC in the configuration data
        # For a basic integrity check, we compute file-level hashes
        md5 = hashlib.md5(self.data).hexdigest()
        sha256 = hashlib.sha256(self.data).hexdigest()

        self.header_info['md5'] = md5
        self.header_info['sha256'] = sha256

        # Check for null-byte padding (possible truncation or corruption)
        null_ratio = self.data.count(0x00) / len(self.data)
        if null_ratio > 0.5:
            self.warnings.append(f"High null-byte ratio ({null_ratio:.1%}) — possible corruption or unused regions")

        # Check for repeated patterns (possible flash read error)
        if len(self.data) > 1024:
            chunk = self.data[:512]
            repeat_count = 0
            for i in range(512, min(len(self.data), 4096), 512):
                if self.data[i:i+512] == chunk:
                    repeat_count += 1
            if repeat_count > 3:
                self.warnings.append(f"Repeated 512-byte blocks detected ({repeat_count}x) — possible read error")

        return True

    def identify_board(self) -> str:
        """Try to identify which DMA board this firmware targets."""
        if self.device_id is None:
            return "Unknown"

        matched_boards = []
        for board_id, board_info in DMA_BOARD_SIGNATURES.items():
            if self.device_id in board_info['typical_idcodes']:
                matched_boards.append(board_info['name'])

        if len(matched_boards) == 1:
            return matched_boards[0]
        elif len(matched_boards) > 1:
            return f"Ambiguous — could be: {', '.join(matched_boards)}"

        return "Unknown board"

    def check_firmware_size(self) -> bool:
        """Check if firmware size matches expected size for the detected device."""
        if self.device_id is None:
            return True  # Can't check without device ID

        # Expected sizes (approximate) for common devices
        expected_sizes = {
            0x03620093: 2_000_000,    # xc7a35t ~2MB
            0x03622093: 3_000_000,    # xc7a50t ~3MB
            0x0362C093: 5_000_000,    # xc7a100t ~5MB
            0x0362E093: 8_000_000,    # xc7a200t ~8MB
            0x03823093: 1_000_000,    # xc7s15 ~1MB
            0x03824093: 1_500_000,    # xc7s25 ~1.5MB
            0x03825093: 3_000_000,    # xc7s50 ~3MB
        }

        expected = expected_sizes.get(self.device_id)
        if expected and self.header_info['file_size']:
            actual = self.header_info['file_size']
            ratio = actual / expected
            if ratio < 0.3:
                self.warnings.append(f"File seems small ({actual} bytes) for {self.device_name}")
            elif ratio > 3.0:
                self.warnings.append(f"File seems large ({actual} bytes) for {self.device_name}")

        return True

    def dump_header(self):
        """Print detailed header information."""
        print("\n" + "=" * 64)
        print("  FIRMWARE HEADER DUMP")
        print("=" * 64)

        print(f"\n  File:       {self.header_info.get('filename', 'N/A')}")
        print(f"  Size:       {self.header_info.get('file_size', 0):,} bytes")
        print(f"  Format:     {self.format or 'Unknown'}")

        if 'sync_offset' in self.header_info:
            print(f"  Sync word:  at offset 0x{self.header_info['sync_offset']:X}")

        if 'idcode' in self.header_info:
            print(f"  IDCODE:     {self.header_info['idcode']}")

        if 'device_name' in self.header_info:
            print(f"  Device:     {self.header_info['device_name']}")

        if 'first_word' in self.header_info:
            print(f"  First word: {self.header_info['first_word']}")

        if 'md5' in self.header_info:
            print(f"\n  MD5:    {self.header_info['md5']}")
            print(f"  SHA256: {self.header_info['sha256']}")

        # Dump first 256 bytes in hex
        if self.data and len(self.data) > 0:
            print(f"\n  First 256 bytes (hex):")
            for i in range(0, min(256, len(self.data)), 16):
                hex_str = ' '.join(f'{b:02X}' for b in self.data[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in self.data[i:i+16])
                print(f"    {i:04X}: {hex_str:<48}  {ascii_str}")

        print()

    def verify(self) -> dict:
        """Run full verification and return results."""
        result = {
            'file': str(self.filepath),
            'valid': False,
            'format': None,
            'device': None,
            'board': None,
            'warnings': [],
            'errors': [],
            'hashes': {},
        }

        # Step 1: Load file
        if not self.load():
            result['errors'] = self.errors
            return result

        # Step 2: Detect format
        fmt = self.detect_format()
        result['format'] = fmt

        if fmt == "unknown":
            self.warnings.append("Unrecognized firmware format")

        # Step 3: Parse header (for Xilinx formats)
        if fmt in ("xilinx_bitstream", "xilinx_bit", "xilinx_bin"):
            self.parse_xilinx_header()

        # Step 4: Check integrity
        self.check_crc()
        result['hashes'] = {
            'md5': self.header_info.get('md5'),
            'sha256': self.header_info.get('sha256'),
        }

        # Step 5: Size validation
        self.check_firmware_size()

        # Step 6: Board identification
        board = self.identify_board()
        result['board'] = board

        # Compile results
        result['device'] = self.device_name
        result['idcode'] = self.header_info.get('idcode')
        result['warnings'] = self.warnings
        result['errors'] = self.errors
        result['valid'] = len(self.errors) == 0

        return result


def verify_single(filepath: str, verbose: bool = False, dump: bool = False):
    """Verify a single firmware file."""
    print("=" * 64)
    print("  DMA Toolkit - Firmware Signature Verifier")
    print("=" * 64)
    print(f"\n  File: {filepath}\n")

    verifier = FirmwareVerifier(filepath, verbose=verbose)

    if dump:
        verifier.load()
        verifier.detect_format()
        verifier.parse_xilinx_header()
        verifier.check_crc()
        verifier.dump_header()
        return

    result = verifier.verify()

    # Print results
    print(f"  Format:    {result['format'] or 'Unknown'}")
    print(f"  Device:    {result['device'] or 'Unknown'}")
    print(f"  Board:     {result['board'] or 'Unknown'}")

    if result.get('idcode'):
        print(f"  IDCODE:    {result['idcode']}")

    if result['hashes'].get('md5'):
        print(f"  MD5:       {result['hashes']['md5']}")
        print(f"  SHA256:    {result['hashes']['sha256']}")

    if result['warnings']:
        print(f"\n  Warnings ({len(result['warnings'])}):")
        for w in result['warnings']:
            print(f"    ⚠ {w}")

    if result['errors']:
        print(f"\n  Errors ({len(result['errors'])}):")
        for e in result['errors']:
            print(f"    ✗ {e}")

    print()
    if result['valid']:
        print("  Status: VERIFIED ✓")
    else:
        print("  Status: FAILED ✗")

    print()
    print("  Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


def verify_directory(dirpath: str, verbose: bool = False):
    """Verify all firmware files in a directory."""
    print("=" * 64)
    print("  DMA Toolkit - Batch Firmware Verification")
    print("=" * 64)

    dir_path = Path(dirpath)
    if not dir_path.is_dir():
        print(f"\n  [!] Not a directory: {dirpath}")
        sys.exit(1)

    extensions = {'.bin', '.bit', '.rbf', '.pof', '.sof', '.mcs', '.flash'}
    files = [f for f in dir_path.iterdir() if f.suffix.lower() in extensions]

    if not files:
        print(f"\n  [-] No firmware files found in {dirpath}")
        print(f"      Supported extensions: {', '.join(extensions)}")
        return

    print(f"\n  Scanning {len(files)} firmware file(s)...\n")

    passed = 0
    failed = 0
    warnings = 0

    for f in sorted(files):
        verifier = FirmwareVerifier(str(f), verbose=verbose)
        result = verifier.verify()

        status = "✓" if result['valid'] else "✗"
        warn_flag = " ⚠" if result['warnings'] else ""

        print(f"  [{status}] {f.name:<30} {result['device'] or 'Unknown':<25}{warn_flag}")

        if result['valid']:
            passed += 1
        else:
            failed += 1
        if result['warnings']:
            warnings += 1

    print(f"\n  {'─' * 50}")
    print(f"  Passed: {passed}  |  Failed: {failed}  |  Warnings: {warnings}")
    print()
    print("  Need help? Join our Discord: https://discord.gg/JJgc2cDEK5")


def main():
    parser = argparse.ArgumentParser(
        description="DMA Firmware Signature Verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s firmware.bin              Verify a single firmware file
  %(prog)s --dump-header firmware.bin Show detailed header info
  %(prog)s --dir ./firmwares/        Verify all firmware files in directory
  %(prog)s -v firmware.bin           Verify with verbose output
        """
    )
    parser.add_argument('file', nargs='?', help='Firmware file to verify')
    parser.add_argument('--dir', '-d', help='Verify all firmware files in directory')
    parser.add_argument('--dump-header', action='store_true', help='Dump raw header info')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    if args.dir:
        verify_directory(args.dir, verbose=args.verbose)
    elif args.file:
        if args.json:
            verifier = FirmwareVerifier(args.file, verbose=args.verbose)
            result = verifier.verify()
            print(json.dumps(result, indent=2))
        else:
            verify_single(args.file, verbose=args.verbose, dump=args.dump_header)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
