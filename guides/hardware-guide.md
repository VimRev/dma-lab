# DMA Hardware Guide

A comprehensive guide to choosing and setting up DMA hardware for game security research.

## Table of Contents
- [What is DMA?](#what-is-dma)
- [Hardware Comparison](#hardware-comparison)
- [Buying Guide](#buying-guide)
- [Setup Guide](#setup-guide)
- [Troubleshooting](#troubleshooting)

---

## What is DMA?

Direct Memory Access (DMA) allows hardware devices to read/write system memory independently of the CPU. In the context of game security research, DMA boards can:

- Read game memory from an external device
- Bypass software-based memory protections
- Analyze anti-cheat systems at the hardware level

## Hardware Comparison

### PCIe DMA Boards

| Board | FPGA | Interface | Speed | Price | Difficulty |
|-------|------|-----------|-------|-------|------------|
| Screamer Squirrel | Artix-7 | PCIe x1 | Fast | $150-200 | Beginner |
| Enigma X1 | Artix-7 | PCIe x1 | Fast | $180-250 | Beginner |
| PCIeScreamer R2 | Spartan-6 | PCIe x1 | Medium | $100-150 | Intermediate |
| Screamer M2 | Artix-7 | M.2 | Fast | $200-280 | Intermediate |
| Custom FPGA | Various | Various | Varies | $50-300 | Advanced |

### USB-Based Solutions

| Device | Interface | Speed | Price | Notes |
|--------|-----------|-------|-------|-------|
| USB3380 | USB 3.0 | Slow | $50-80 | Legacy, limited capabilities |
| FPGA + USB3.0 | USB 3.0 | Medium | $100+ | Custom designs |

## Buying Guide

### For Beginners
**Recommended: Screamer Squirrel or Enigma X1**

- Pre-flashed with working firmware
- Active community support
- Plug-and-play with PCILeech
- Good documentation available

### For Budget Builds
**Recommended: PCIeScreamer R2**

- Cheapest option (~$100)
- Still functional for most use cases
- Spartan-6 FPGA (older, but works)
- Slower than Artix-7 alternatives

### For Advanced Users
**Recommended: Custom Artix-7 FPGA Board**

- Full control over firmware
- Best performance potential
- Requires FPGA development knowledge
- Xilinx Vivado required for firmware compilation

### Where to Buy
- Screamer Shop (official reseller)
- Various AliExpress sellers (verify firmware!)
- eBay (used boards, test before buying)
- Direct FPGA dev boards from Xilinx/AMD

> ⚠️ Always verify firmware version after purchase. Some sellers ship outdated firmware.

## Setup Guide

### Step 1: Physical Installation
1. Power off your target PC
2. Insert DMA board into an available PCIe slot
3. Power on — check Device Manager for enumeration
4. If not detected, try a different PCIe slot

### Step 2: Host PC Setup
1. Install PCILeech on your analysis machine
2. Connect DMA board via USB or network
3. Verify connection:
   ```bash
   pcileech.exe -device FPGA -info
   ```

### Step 3: Configuration
1. Copy a config from `configs/pcileech/`
2. Edit device settings to match your hardware
3. Test with a simple memory read

### Step 4: Firmware Update
1. Check current firmware version
2. Download latest firmware for your board
3. Flash using vendor-provided tool
4. Verify after flash

## Troubleshooting

### Board Not Detected
- Try different PCIe slot
- Check if board appears in Device Manager
- Verify FPGA firmware is flashed correctly
- Try: `-device fpga://algo=2`

### Connection Timeout
- Check USB cable (use quality cable)
- Verify LeechCore port (default: 28473)
- Disable firewall temporarily for testing
- Try: `-verbosity 3` for detailed error output

### Memory Read Errors
- Ensure target PC supports DMA (check BIOS settings)
- Verify IOMMU/VT-d is disabled in BIOS
- Check if anti-cheat is blocking DMA access
- Try different `-min-fpga-version` setting

### Performance Issues
- Use Artix-7 based boards for best speed
- Increase `-max-size` (may reduce stability)
- Use local connection instead of remote
- Close unnecessary applications on host PC

---

## Need Help?

Join our Discord community for hardware support, firmware sharing, and troubleshooting:

👉 **[Join Discord](https://discord.gg/JJgc2cDEK5)**

We have channels for:
- Hardware selection advice
- Firmware updates and configs
- Setup troubleshooting
- Anti-cheat analysis discussion
