<div align="center">

# ⚡ DMA Toolkit

### Hardware-Level Anti-Cheat Research & Firmware Resources

[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/JJgc2cDEK5)
[![GitHub Stars](https://img.shields.io/github/stars/VimRev/dma-toolkit?style=for-the-badge&logo=github)](https://github.com/VimRev/dma-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

**Firmware configs · Anti-cheat analysis · Hardware guides · Driver development**

*70+ researchers and developers in our Discord community*

[**👉 JOIN OUR DISCORD**](https://discord.gg/JJgc2cDEK5)

</div>

---

## What This Repo Contains

| Directory | Description |
|-----------|-------------|
| [`configs/`](configs/) | PCILeech & LeechCore configuration files for various setups |
| [`firmware/`](firmware/) | Firmware resources, sig-ruling guides, and FPGA configs |
| [`guides/`](guides/) | Hardware selection, setup tutorials, and anti-cheat analysis |
| [`tools/`](tools/) | Utility scripts for DMA development and testing |

## Quick Start

### Prerequisites
- DMA hardware board (Screamer Squirrel, Enigma X1, PCIeScreamer, etc.)
- PCILeech [installed](https://github.com/ufrisk/pcileech)
- LeechCore [installed](https://github.com/ufrisk/leechcore)
- MemProcFS (optional, for memory forensics) [here](https://github.com/ufrisk/memprocfs)

### Basic Setup
```bash
# Clone the repo
git clone https://github.com/VimRev/dma-toolkit.git
cd dma-toolkit

# Copy a config template
cp configs/pcileech/example.cfg my-setup.cfg

# Edit to match your hardware
nano my-setup.cfg

# Run PCILeech with your config
pcileech.exe my-setup.cfg
```

## Anti-Cheat Analysis

We actively research and document how modern anti-cheat systems work at the kernel level:

| Anti-Cheat | Games | Status |
|------------|-------|--------|
| EasyAntiCheat (EAC) | Fortnite, Apex, Rust | 🔍 Active research |
| BattlEye | PUBG, Arma, R6 Siege | 🔍 Active research |
| Vanguard | Valorant | 🔍 Active research |
| Ricochet | Warzone, MW3 | 🔍 Active research |
| FACEIT AC | CS2 | 🔍 Active research |

> Detailed analysis and bypass discussions happen in our [**Discord server**](https://discord.gg/JJgc2cDEK5).

## Hardware Guide

### Recommended DMA Boards

| Board | Interface | FPGA | Price Range | Notes |
|-------|-----------|------|-------------|-------|
| Screamer Squirrel | PCIe | Xilinx Artix-7 | $150-200 | Great for beginners |
| Enigma X1 | PCIe | Xilinx Artix-7 | $180-250 | Solid community support |
| PCIeScreamer R2 | PCIe | Xilinx Spartan-6 | $100-150 | Budget option |
| Screamer M2 | M.2 | Xilinx Artix-7 | $200-280 | Laptop compatible |

> Full comparison and buying guides in [`guides/hardware-guide.md`](guides/hardware-guide.md)

### Recommended FPGA Dev Boards (DIY)
- **Xilinx Artix-7** — Best price/performance for DMA
- **Xilinx Spartan-6** — Budget, still functional
- **Intel Cyclone V** — Alternative, less community support

## PCILeech Config Templates

Pre-made configs for common setups are in [`configs/`](configs/):

```
configs/
├── pcileech/
│   ├── base.cfg              # Base config template
│   ├── fpga-artix7.cfg       # Artix-7 FPGA boards
│   └── fpga-spartan6.cfg     # Spartan-6 FPGA boards
├── leechcore/
│   └── leechcore.cfg         # LeechCore connection settings
└── memprocfs/
    └── memprocfs.ini         # MemProcFS forensic mode
```

## Community Resources

### Tools & References
- [PCILeech](https://github.com/ufrisk/pcileech) — Direct Memory Access attack toolkit
- [LeechCore](https://github.com/ufrisk/leechcore) — LeechCore Memory Acquisition Library
- [MemProcFS](https://github.com/ufrisk/memprocfs) — Memory Process File System
- [Screamer PCIe Squirrel](https://github.com/ufrisk/pcileech-fpga) — FPGA firmware source

### Learning Resources
- [PCILeech Wiki](https://github.com/ufrisk/pcileech/wiki) — Official documentation
- [LeechCore API Docs](https://github.com/ufrisk/leechcore/wiki) — Library documentation
- Our Discord has dedicated channels for learning and troubleshooting

## Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Submit a PR

Or share your configs and guides in our [Discord](https://discord.gg/JJgc2cDEK5) and we'll add them.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

### 🚀 Join Our Community

[![Discord](https://img.shields.io/badge/Discord-Join%20Now-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/JJgc2cDEK5)

**70+ members · Active discussion · Firmware sharing · Hardware guides**

</div>
