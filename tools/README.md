# DMA Toolkit - Utility Scripts

Handy scripts for DMA development and testing.

## Scripts

### `check_device.py`
Verify DMA board connection and basic functionality.

```bash
python3 check_device.py
```

### `memory_dump.py`
Dump specific memory regions for analysis.

```bash
python3 memory_dump.py --pid 1234 --address 0x7FFE0000 --size 0x1000
```

### `pcie_scan.py`
Scan PCIe bus and list connected devices.

```bash
python3 pcie_scan.py
```

## Requirements

```bash
pip install -r requirements.txt
```

## Notes

- Scripts require PCILeech to be installed
- Run with appropriate permissions (admin/root)
- These are utility scripts, not standalone tools
- For full DMA toolkit, use PCILeech directly

---

## Need Help?

👉 **[Join our Discord](https://discord.gg/JJgc2cDEK5)**
