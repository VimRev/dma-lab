# DMA Toolkit - Utility Scripts

Handy scripts for DMA development, testing, and hardware analysis.

## Scripts

### `check_device.py`
Verify DMA board connection and basic functionality.

```bash
python3 check_device.py
```

### `pcie_scan.py`
Scan PCIe bus and list connected devices. Identifies known DMA/FPGA hardware.

```bash
python3 pcie_scan.py
```

### `dma_info.py`
Read detailed hardware information for DMA boards. Auto-detects DMA devices and shows PCIe configuration space data.

```bash
# Auto-detect DMA devices
python3 dma_info.py

# Show all PCIe devices
python3 dma_info.py --all

# Specific device
python3 dma_info.py --bus 03:00.0

# JSON output
python3 dma_info.py --json
```

### `firmware_verify.py`
Validate FPGA bitstream integrity and detect firmware tampering. Supports Xilinx 7-Series, UltraScale, and Intel FPGA bitstreams.

```bash
# Verify a single firmware file
python3 firmware_verify.py firmware.bin

# Show detailed header info
python3 firmware_verify.py --dump-header firmware.bin

# Verify all firmware files in directory
python3 firmware_verify.py --dir ./firmwares/

# JSON output
python3 firmware_verify.py --json firmware.bin
```

**Features:**
- Xilinx IDCODE extraction and device identification
- CRC integrity checking
- Board family detection (Screamer, Enigma, etc.)
- Bitstream format auto-detection
- Batch verification mode

### `bar_dump.py`
Read and display PCIe BAR (Base Address Register) memory regions. Essential for debugging firmware and verifying device register access.

```bash
# Dump all BARs for a device
python3 bar_dump.py --bus 03:00.0

# Dump only BAR0
python3 bar_dump.py --bus 03:00.0 --bar 0

# Read first 4K of BAR0
python3 bar_dump.py --bus 03:00.0 --bar 0 --size 4K

# Scan for DMA devices and dump
python3 bar_dump.py --scan

# Annotate with known register names
python3 bar_dump.py --bus 03:00.0 --interpret
```

**Features:**
- Hex dump with ASCII representation
- Known DMA register name annotation
- BAR size and type display
- Batch scanning mode
- JSON output support

### `memory_dump.py`
Dump specific memory regions for analysis.

```bash
python3 memory_dump.py --pid 1234 --address 0x7FFE0000 --size 0x1000
```

## Requirements

```bash
pip install -r requirements.txt
```

## Notes

- Scripts require PCILeech to be installed for full functionality
- Run with appropriate permissions (admin/root)
- Linux: `sudo` may be needed for PCIe BAR access
- Windows: Run as Administrator
- These are utility scripts, not standalone tools
- For full DMA toolkit, use PCILeech directly

---

## Need Help?

👉 **[Join our Discord](https://discord.gg/JJgc2cDEK5)**
