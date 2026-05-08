# DMA Detection Vectors — How Anti-Cheats Identify DMA Hardware

> **Last updated:** May 2026
> **Applies to:** EAC, BattlEye, Vanguard, FACEIT, nProtect

This document catalogs the known detection vectors used by modern anti-cheat systems to identify DMA-based cheating hardware. Understanding these vectors is essential for firmware development and security research.

---

## Table of Contents

1. [PCIe Enumeration Fingerprinting](#1-pcie-enumeration-fingerprinting)
2. [Device ID & Class Code Analysis](#2-device-id--class-code-analysis)
3. [BAR (Base Address Register) Analysis](#3-bar-analysis)
4. [PCIe Link Behavior Profiling](#4-pcie-link-behavior-profiling)
5. [Timing-Based Detection](#5-timing-based-detection)
6. [Memory Access Pattern Analysis](#6-memory-access-pattern-analysis)
7. [Driver & Firmware Fingerprinting](#7-driver--firmware-fingerprinting)
8. [Kernel-Level PCIe Topology Scanning](#8-kernel-level-pcie-topology-scanning)
9. [Behavioral Heuristics](#9-behavioral-heuristics)
10. [Countermeasures & Mitigations](#10-countermeasures--mitigations)

---

## 1. PCIe Enumeration Fingerprinting

### What They Do
Anti-cheats enumerate all PCIe devices and compare the list against known hardware databases. Unknown or suspicious devices trigger detection flags.

### Specific Checks

```
# Pseudocode: Anti-cheat PCIe scan logic
for device in enumerate_pci_devices():
    if device.vendor_id not in KNOWN_VENDORS:
        flag_suspicious(device)
    
    if device.class_code == 0x068000:  # "Other bridge"
        if device.device_id not in KNOWN_BRIDGE_IDS:
            flag_suspicious(device)
    
    if device.subsystem_vendor == 0x0000:
        flag_suspicious(device)  # Missing subsystem IDs
```

### Detection Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Unknown Vendor ID | Medium | Vendor ID not in PCI-SIG database |
| Generic Device ID | Medium | Device ID matches FPGA development boards |
| Class Code 0x068000 | Low | "Other bridge" — too generic |
| Missing Subsystem IDs | High | Legitimate devices always have subsystem info |
| Xilinx/Intel FPGA IDs | High | Known FPGA vendor IDs |

### Known Problematic IDs

```
# These IDs are in anti-cheat databases
VENDOR_XILINX    = 0x10EE  # Xilinx — flagged by most ACs
VENDOR_INTEL_FPGA = 0x1172  # Intel/Altera — flagged
VENDOR_LATTICE   = 0x1204  # Lattice — flagged

# Device IDs commonly associated with DMA boards
0x0007, 0x7011, 0x7012, 0x7021, 0x7022  # Xilinx XDMA/QDMA
0x0666, 0x1337, 0xAAAA                    # Custom DMA boards
```

---

## 2. Device ID & Class Code Analysis

### What They Do
Beyond simple ID checking, anti-cheats analyze the relationship between vendor, device, subsystem, and class codes. Inconsistencies indicate spoofed or custom hardware.

### Consistency Checks

```
Legitimate device example:
  Vendor:    0x8086 (Intel)
  Device:    0x1539 (I211 Gigabit Network)
  Subsystem: 0x8086:0x0000 (Intel reference design)
  Class:     0x020000 (Ethernet controller)

Suspicious device example:
  Vendor:    0x10EE (Xilinx)
  Device:    0x0666 (Custom)
  Subsystem: 0x0000:0x0000 (Missing!)
  Class:     0x068000 (Other bridge)
```

### Red Flags

- **Subsystem IDs all zeros** — Legitimate hardware always has subsystem vendor/device
- **Class code mismatch** — Device claims to be a bridge but has memory BARs
- **Revision 0x00** — Most production hardware has non-zero revision
- **PCIe capability list anomalies** — Missing or malformed capability structures

---

## 3. BAR Analysis

### What They Do
Anti-cheats read BAR (Base Address Register) contents to determine what memory regions a device exposes. DMA boards typically have:
- Large BARs (128MB+) for DMA buffers
- Small BARs for control registers
- BARs that don't match claimed device type

### BAR Fingerprinting

```
# Anti-cheat BAR analysis pseudocode
for device in pci_devices:
    bars = read_bars(device)
    
    # Check: Does BAR layout match claimed device type?
    if device.class == "Network Controller":
        expected_bars = 1-2  # Typically
        if len(bars) > 3:
            flag_suspicious()
    
    # Check: BAR sizes
    for bar in bars:
        if bar.size > 256MB:
            flag_suspicious()  # Unusually large
    
    # Check: BAR content patterns
    if bars_contain_pcileech_signature(bar_data):
        flag_critical()
```

### Known BAR Patterns

| Pattern | Detection Level | Description |
|---------|----------------|-------------|
| XDMA signature at BAR0+0x00 | Critical | `0x444D4158` ("XDMA") at offset 0 |
| QDMA signature at BAR0+0x00 | Critical | `0x444D4151` ("QDMA") at offset 0 |
| PCILeech magic bytes | Critical | Known firmware signatures |
| All-zero BAR content | Medium | Empty/unused BARs |
| BAR with only control regs | Low | Small BAR with few active registers |

---

## 4. PCIe Link Behavior Profiling

### What They Do
Anti-cheats monitor PCIe link characteristics to detect hardware anomalies. DMA boards connected via adapter cards or risers often show different link behavior than integrated devices.

### Monitored Parameters

```
# What anti-cheats check:
link_speed       # Gen1/Gen2/Gen3/Gen4
link_width       # x1, x4, x8, x16
link_status      # Active, L0, L1, L2
retrain_count    # How often the link retrains
error_count      # Correctable/uncorrectable errors
```

### Detection Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Link retrains during game | High | Indicates hot-plug or unstable connection |
| Gen1 speed in Gen3+ slot | Medium | Possible adapter limitation |
| Width downgrade (x16→x1) | Medium | Riser or adapter reducing bandwidth |
| High correctable error rate | Medium | Poor signal integrity |
| Link status changes | High | Device going to/from L1/L2 states |

### Why DMA Boards Are Different

DMA boards connected via:
- **Riser cables** — Often limit to Gen2 or Gen1 speeds
- **USB adapters** — Don't use PCIe link at all (FT601/FT2232H)
- **M.2 adapters** — May show different link characteristics
- **Chipset slots** — Different topology than CPU-direct slots

---

## 5. Timing-Based Detection

### What They Do
Anti-cheats measure the time it takes to read game memory. DMA reads go through the PCIe bus and FPGA, adding measurable latency compared to normal CPU reads.

### Timing Analysis

```python
# Anti-cheat timing probe (conceptual)
def probe_memory_timing(address):
    """Read same address multiple times and measure variance."""
    times = []
    for _ in range(1000):
        start = rdtsc()
        value = read_memory(address)
        end = rdtsc()
        times.append(end - start)
    
    # Normal reads: consistent timing (cache hits)
    # DMA reads: variable timing (PCIe round-trip)
    variance = calculate_variance(times)
    if variance > THRESHOLD:
        flag_suspicious()
```

### Detection Thresholds

| Metric | Normal | DMA | Notes |
|--------|--------|-----|-------|
| Read latency (cached) | 1-4 ns | N/A | L1/L2 cache |
| Read latency (uncached) | 50-100 ns | 200-500 ns | DMA adds PCIe round-trip |
| Latency variance | Low | High | DMA timing is inconsistent |
| Batch read throughput | High | Limited | PCIe bandwidth ceiling |

### Timing Evasion

- **Pre-fetching** — Read data before it's requested
- **Caching** — Store frequently accessed data locally
- **Timing normalization** — Add artificial delay to match normal timing

---

## 6. Memory Access Pattern Analysis

### What They Do
Anti-cheats monitor which memory regions are being accessed and look for patterns consistent with DMA cheating (reading player positions, health, etc.).

### Pattern Detection

```
Suspicious patterns:
  - Reading player entity list repeatedly at high frequency
  - Accessing multiple player positions in rapid succession
  - Reading memory regions that the game process doesn't access
  - Cross-process memory reads to game address space
```

### What They Monitor

- **Read frequency** — How often specific addresses are read
- **Access scope** — Which memory regions are touched
- **Timing correlation** — Reads correlating with game events
- **Process context** — Who is doing the reading

---

## 7. Driver & Firmware Fingerprinting

### What They Do
Anti-cheats check loaded kernel drivers and compare them against known signatures. They also probe firmware via PCIe configuration space.

### Driver Checks

```
# Anti-cheat driver scanning
loaded_drivers = enumerate_kernel_modules()
for driver in loaded_drivers:
    if driver in KNOWN_DMA_DRIVERS:
        flag_critical(driver)  # PCILeech, LeechCore, etc.
    
    if driver.has_valid_signature == False:
        flag_suspicious(driver)
    
    if driver.name matches "pcileech*", "leech*", "memproc*":
        flag_critical()
```

### Known Flagged Drivers

| Driver | Status | Description |
|--------|--------|-------------|
| pcileech.sys | Critical | PCILeech kernel module |
| leechcore.sys | Critical | LeechCore memory access |
| ftdi.sys | High | FTDI USB drivers (if unexpected) |
| Custom unsigned drivers | High | Any unsigned kernel module |

### Firmware Probing

Anti-cheats can also probe device firmware via:
- **PCIe configuration reads** — Read device capabilities
- **BAR content scanning** — Check for known firmware patterns
- **Capability structure analysis** — Validate PCIe capability list

---

## 8. Kernel-Level PCIe Topology Scanning

### What They Do
Kernel-mode anti-cheat components scan the entire PCIe topology tree and validate the parent-child relationships between bridges, switches, and endpoints.

### Topology Validation

```
Expected topology (legitimate):
  CPU Root Port → PCIe Switch → GPU
  CPU Root Port → PCH → NVMe
  CPU Root Port → PCH → Network

Suspicious topology:
  CPU Root Port → Unknown Bridge → DMA Device  # Extra hop
  PCH → PCIe Slot → DMA Device  # In chipset slot
```

### What They Check

- **Root port mapping** — Is the device behind a CPU or PCH root port?
- **Bridge chain depth** — Too many bridges = suspicious
- **Hot-plug capability** — DMA boards may support hot-plug
- **ACS (Access Control Services)** — Peer-to-peer DMA protection

---

## 9. Behavioral Heuristics

### What They Do
Beyond hardware fingerprinting, anti-cheats use behavioral analysis to detect DMA-assisted cheating.

### Heuristic Indicators

| Indicator | Weight | Description |
|-----------|--------|-------------|
| Perfect tracking through walls | High | Aim-assist via DMA reads |
| Pre-firing at exact positions | High | Knowledge of enemy positions |
| Impossible reaction times | Medium | Information advantage |
| Consistent "game sense" | Medium | Always knowing where to look |
| No missed shots on moving targets | High | Real-time position tracking |

### Statistical Analysis

Anti-cheats maintain statistical models of legitimate player behavior:
- **Reaction time distributions** — DMA users react faster than human limits
- **Accuracy patterns** — Unnatural accuracy distribution
- **Positioning decisions** — Too optimal positioning based on hidden info

---

## 10. Countermeasures & Mitigations

### Firmware-Level

| Mitigation | Effectiveness | Description |
|-----------|---------------|-------------|
| ID spoofing | Medium | Change vendor/device IDs to match legitimate hardware |
| Subsystem ID filling | High | Add realistic subsystem vendor/device IDs |
| Class code correction | Medium | Use appropriate class code for claimed device type |
| BAR content shaping | Medium | Fill BARs with realistic firmware signatures |
| PCIe capability spoofing | High | Add proper capability structures |

### Software-Level

| Mitigation | Effectiveness | Description |
|-----------|---------------|-------------|
| Read rate limiting | Medium | Don't read too frequently |
| Access pattern randomization | Medium | Add noise to access patterns |
| Timing normalization | Medium | Match normal read timing |
| Driver hiding | Low | Most ACs can find hidden drivers |

### Hardware-Level

| Mitigation | Effectiveness | Description |
|-----------|---------------|-------------|
| CPU-direct slot | High | Avoid chipset slots |
| Native Gen3/Gen4 | High | Match expected link speed |
| Proper power delivery | Medium | Avoid power-related link issues |
| No adapters/risers | High | Direct slot connection |

---

## References

- [PCI-SIG PCI Express Base Specification](https://pcisig.com/specifications/pci-express)
- [Xilinx XDMA Driver Documentation](https://www.xilinx.com/products/intellectual-property/pcie-dma.html)
- [PCILeech Project](https://github.com/ufrisk/pcileech)
- [EAC Technical Overview](https://www.easy.ac/en-us/support/game/guides/technical/)

---

> **Disclaimer:** This document is intended for security research and educational purposes only. Understanding detection vectors helps build better defensive systems and promotes transparency in anti-cheat technology.

---

> **Join our research community:** [Discord](https://discord.gg/JJgc2cDEK5)
