# DMA Toolkit - PCILeech Configurations

This directory contains PCILeech and LeechCore configuration templates for various DMA hardware setups.

## Usage

1. Copy the config that matches your hardware
2. Edit the device-specific settings
3. Run PCILeech with your config

```bash
pcileech.exe your-config.cfg
```

## Config Files

| File | Description |
|------|-------------|
| `pcileech/base.cfg` | Base template with all common options |
| `pcileech/fpga-artix7.cfg` | Optimized for Artix-7 based boards |
| `pcileech/fpga-spartan6.cfg` | Optimized for Spartan-6 based boards |
| `leechcore/leechcore.cfg` | LeechCore connection parameters |
| `memprocfs/memprocfs.ini` | MemProcFS forensic analysis config |

## Common Parameters

### Device Selection
```
-device FPGA
```
Options: `FPGA`, `USB3380`, `SP605`, `AC701`, `SQUIRREL`

### Connection Settings
```
-device fpga://algo=1
```
- `algo=1` — Default algorithm (most compatible)
- `algo=2` — Alternative for specific firmware versions

### Performance Tuning
```
-min-fpga-version 9
-max-size 0x1000
```

## Need Help?

Join our Discord for hardware-specific config support:
👉 https://discord.gg/JJgc2cDEK5
