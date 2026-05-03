# Anti-Cheat Analysis Guide

Technical analysis of modern anti-cheat systems and how they interact with DMA hardware.

> ⚠️ This guide is for educational and research purposes only.

## Table of Contents
- [Anti-Cheat Overview](#anti-cheat-overview)
- [Detection Methods](#detection-methods)
- [Analysis Techniques](#analysis-techniques)
- [Resources](#resources)

---

## Anti-Cheat Overview

Modern anti-cheat systems operate at multiple levels:

### User-Mode Components
- Process scanning and memory analysis
- Signature-based detection
- Behavioral analysis
- Network traffic inspection

### Kernel-Mode Components
- Driver-level memory protection
- DMA device enumeration
- PCIe device scanning
- Hypervisor detection

## Detection Methods

### PCIe Device Enumeration
Anti-cheats scan the PCIe bus for known DMA device signatures:
- Vendor/Device ID matching
- PCIe capability structure analysis
- BAR (Base Address Register) inspection
- DMA remapping unit (IOMMU) configuration

### FPGA Firmware Detection
- Known FPGA signatures in PCIe config space
- Timing analysis (DMA operations are faster than normal PCIe)
- Memory access pattern analysis
- Interrupt behavior anomalies

### Memory Integrity Checks
- Page table monitoring
- CR3 register tracking
- Memory mapping consistency
- Process memory integrity

## Analysis Techniques

### Static Analysis
1. Extract anti-cheat driver files
2. Disassemble with IDA Pro / Ghidra
3. Identify detection routines
4. Map IOCTL codes and communication

### Dynamic Analysis
1. Run anti-cheat in controlled environment
2. Monitor system calls and driver interactions
3. Trace PCIe bus activity
4. Log memory access patterns

### Tools for Analysis
- **PCILeech** — DMA memory access
- **MemProcFS** — Memory forensics
- **Ghidra** — Reverse engineering
- **WinDbg** — Kernel debugging
- **Process Monitor** — System call monitoring
- **Wireshark** — Network analysis

## Anti-Cheat Specific Notes

### EasyAntiCheat (EAC)
- Kernel driver: `EasyAntiCheat.sys`
- PCIe device scanning active
- Known to check for FPGA signatures
- Regular signature updates

### BattlEye
- Kernel driver: `BattlEye.sys`
- Aggressive DMA detection
- Hypervisor detection active
- Memory integrity checks

### Vanguard (Riot)
- Ring 0 kernel driver
- Boot-time initialization
- Most aggressive DMA detection
- TPM attestation checks

### Ricochet (Activision)
- Kernel driver with HWID checks
- Machine learning based detection
- Behavioral analysis heavy
- Regular updates

---

## Detailed Analysis

For in-depth anti-cheat analysis, bypass discussions, and reverse engineering:

👉 **[Join Our Discord](https://discord.gg/JJgc2cDEK5)**

Our community shares:
- Reverse engineering findings
- Detection method analysis
- Firmware sig-ruling techniques
- Hardware modification guides

## Resources

- [PCILeech GitHub](https://github.com/ufrisk/pcileech)
- [MemProcFS GitHub](https://github.com/ufrisk/memprocfs)
- [Ghidra](https://ghidra-sre.org/)
- [Windows Internals](https://www.microsoft.com/en-us/p/windows-internals-7th-edition-part-1/9nblggh4pns7) — Book
- [OSDev Wiki](https://wiki.osdev.org/) — OS development reference
