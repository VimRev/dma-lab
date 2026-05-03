# DMA Firmware Resources

This directory contains firmware-related resources for DMA hardware.

## Firmware Overview

DMA firmware runs on the FPGA and controls:
- PCIe interface configuration
- DMA read/write operations
- Memory access patterns
- Device identification (Vendor/Device IDs)

## Firmware Versions

### Common Firmware Families

| Firmware | FPGA Target | Features | Notes |
|----------|-------------|----------|-------|
| PCILeech FPGA | Artix-7, Spartan-6 | Open source, well documented | Reference implementation |
| Custom FW | Various | Board-specific optimizations | Varies by vendor |
| Sig-Ruled | Artix-7 | Modified PCIe signatures | Bypass signature detection |

### Version Naming
- `vX.Y.Z` — Major.Minor.Patch
- Major: Breaking changes or new FPGA support
- Minor: New features or improvements
- Patch: Bug fixes

## Sig-Ruling (Signature Modification)

Sig-ruling modifies the PCIe configuration space to:
- Change Vendor/Device IDs
- Modify capability structures
- Alter BAR configurations
- Mask FPGA-specific signatures

### Basic Sig-Ruling Process
1. Read current PCIe config space
2. Identify anti-cheat detection points
3. Modify signatures to match legitimate devices
4. Flash modified firmware
5. Verify with PCILeech

### Common Target Devices
- Intel Ethernet controllers
- Realtek network cards
- Standard NVMe controllers
- Generic PCIe bridges

> ⚠️ Sig-ruling is advanced. Incorrect modifications can brick your FPGA.
> Always backup original firmware before modification.

## FPGA Development

### Xilinx Artix-7
- Toolchain: Vivado (free WebPACK edition)
- HDL: Verilog / VHDL
- Development board: Arty A7, Basys 3
- Documentation: [Xilinx Docs](https://www.xilinx.com/support/documentation.html)

### Xilinx Spartan-6
- Toolchain: ISE (legacy, still functional)
- HDL: Verilog / VHDL
- Development board: Nexys 3, Basys 3
- Note: Older technology, limited future support

## Firmware Sources

### Official / Open Source
- [PCILeech FPGA](https://github.com/ufrisk/pcileech-fpga) — Reference firmware
- Community contributions in this repo

### Community / Commercial
- Board vendor firmware (check with your seller)
- Custom firmware shared in our Discord

## Flashing Firmware

### Using Vivado Hardware Manager
1. Open Vivado Hardware Manager
2. Connect to FPGA via JTAG
3. Program flash with .bin file
4. Verify successful flash

### Using Vendor Tools
- Each board may have its own flash tool
- Follow vendor documentation
- Always verify after flashing

---

## Get Firmware Updates

Our Discord community regularly shares:
- New firmware releases
- Sig-ruling templates
- Custom firmware builds
- Flash tutorials

👉 **[Join Discord](https://discord.gg/JJgc2cDEK5)**

## Contributing

Have firmware configs or sig-ruling templates to share?
- Submit a PR to this repo
- Or share in our Discord and we'll add it
