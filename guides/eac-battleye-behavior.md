# EAC & BattlEye Behavior Analysis — Anti-Cheat Internals

> **Last updated:** May 2026
> **Scope:** EasyAntiCheat (EAC) and BattlEye (BE) kernel-mode behavior

Technical analysis of how EAC and BattlEye operate at the kernel level, their scanning methodologies, and how they detect hardware-level cheating. This document is based on public research, reverse engineering, and documented behavior.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [EasyAntiCheat (EAC) Deep Dive](#2-easyantiCheat-deep-dive)
3. [BattlEye (BE) Deep Dive](#3-battleye-deep-dive)
4. [Kernel Driver Analysis](#4-kernel-driver-analysis)
5. [Scanning Methodologies](#5-scanning-methodologies)
6. [Signature Detection](#6-signature-detection)
7. [Behavioral Detection](#7-behavioral-detection)
8. [Update & Response Cycle](#8-update--response-cycle)
9. [Game-Specific Implementations](#9-game-specific-implementations)
10. [Research Notes](#10-research-notes)

---

## 1. Architecture Overview

### Dual-Layer Architecture

Both EAC and BattlEye use a two-layer architecture:

```
┌─────────────────────────────────────────────┐
│              User-Mode Component            │
│  ┌────────────────────────────────────────┐ │
│  │ - Game integration SDK                 │ │
│  │ - Network communication to cloud       │ │
│  │ - Heuristic analysis engine            │ │
│  │ - Screenshot capture                   │ │
│  │ - Report generation                    │ │
│  └────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│              Kernel-Mode Driver             │
│  ┌────────────────────────────────────────┐ │
│  │ - Memory scanning                      │ │
│  │ - Driver enumeration                   │ │
│  │ - Hardware fingerprinting              │ │
│  │ - Process monitoring                   │ │
│  │ - PCIe topology scanning               │ │
│  │ - Timing analysis                      │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Communication Flow

```
Game Process ←→ AC User-Mode ←→ AC Kernel Driver ←→ Cloud Backend
                                      ↓
                              System Hardware Scan
                              Memory Read/Write
                              Driver Enumeration
```

---

## 2. EasyAntiCheat (EAC) Deep Dive

### Driver: EasyAntiCheat.sys

**Loading:** EAC's kernel driver is loaded as a boot-start or demand-start driver, depending on the game's configuration.

**Key Characteristics:**
- Signed by Epic Games
- Obfuscated entry points
- Anti-debugging protections
- Self-integrity checks

### Scanning Phases

EAC performs scans in distinct phases:

#### Phase 1: Pre-Game Initialization
```
- Enumerate loaded drivers
- Check driver signatures
- Scan for known cheat signatures in memory
- Validate system call table (SSDT)
- Check for hypervisor presence
- Scan PCIe topology
```

#### Phase 2: Runtime Monitoring
```
- Periodic memory scans (configurable interval)
- Process creation monitoring
- Module load monitoring
- Network traffic analysis
- Screenshot capture (random intervals)
- Hardware state validation
```

#### Phase 3: Post-Game Analysis
```
- Upload scan results to cloud
- Behavioral pattern analysis
- Statistical anomaly detection
- Cross-reference with known cheat database
```

### EAC Specific Checks

| Check | Frequency | Detection Target |
|-------|-----------|-----------------|
| Memory integrity | Every 5-30s | Memory modification |
| Driver list | Every 60s | Unauthorized drivers |
| PCIe enumeration | Every 120s | DMA hardware |
| SSDT validation | Every 300s | Hook detection |
| Hypervisor check | At launch | VM-based cheats |
| Timing probes | Continuous | DMA timing anomalies |

### EAC Cloud Backend

EAC uploads scan data to Epic's cloud for:
- **Machine learning analysis** — Pattern detection across millions of sessions
- **Signature updates** — New cheat signatures pushed to clients
- **Behavioral modeling** — Statistical analysis of player behavior
- **Cross-game correlation** — Same cheat used across multiple games

---

## 3. BattlEye (BE) Deep Dive

### Driver: BEDaisy.sys

**Loading:** BattlEye's kernel driver (BEDaisy) is loaded early in the game launch process.

**Key Characteristics:**
- Signed by BattlEye GmbH
- Heavily obfuscated
- Anti-tampering mechanisms
- Self-updating capability

### BattlEye's Aggressive Approach

BattlEye is known for being more aggressive than EAC:

```
# BattlEye behavioral characteristics:
- More frequent scans
- Lower detection thresholds
- Faster ban waves
- More invasive hardware probing
- Aggressive driver blocking
```

### BattlEye Specific Checks

| Check | Frequency | Detection Target |
|-------|-----------|-----------------|
| Full memory scan | Every 2-10s | Any modification |
| Driver verification | Every 30s | Unsigned/modified drivers |
| Hardware fingerprint | Every 60s | Hardware spoofing |
| PCIe topology scan | Every 60s | DMA devices |
| Process tree analysis | Continuous | Injection/hooking |
| Network monitoring | Continuous | External communication |
| Integrity checks | Continuous | Code modification |

### BattlEye's Hardware Probing

BattlEye performs deep hardware analysis:

```python
# Conceptual BattlEye hardware probe
def battleye_hardware_scan():
    # 1. Enumerate all PCIe devices
    devices = enumerate_pcie_devices()
    
    # 2. Check each device against known-good database
    for dev in devices:
        if dev.vendor_id in FPGA_VENDORS:
            flag_critical("FPGA device detected")
        
        if dev.class_code == 0x068000:
            probe_bar_contents(dev)
            check_driver(dev)
    
    # 3. Check for USB-attached DMA devices
    usb_devices = enumerate_usb_devices()
    for usb in usb_devices:
        if usb.vendor_id in FTDI_IDS:
            flag_suspicious("FTDI device")
    
    # 4. Validate PCIe topology
    topology = build_pcie_tree()
    for node in topology:
        if node.depth > expected_depth:
            flag_suspicious("Unexpected bridge")
```

---

## 4. Kernel Driver Analysis

### Anti-Cheat Driver Operations

Both EAC and BattlEye's kernel drivers perform:

#### Memory Operations
```c
// Conceptual kernel-mode memory scan
NTSTATUS scan_process_memory(PEPROCESS process) {
    // Attach to target process
    KAPC_STATE apc;
    KeStackAttachProcess(process, &apc);
    
    // Scan memory regions
    for each memory_region in process->vad_tree {
        if (region.type == MEM_PRIVATE || region.type == MEM_IMAGE) {
            // Read and scan for signatures
            data = read_memory(region.base, region.size);
            check_signatures(data);
            check_patterns(data);
        }
    }
    
    KeUnstackDetachProcess(&apc);
}
```

#### Driver Enumeration
```c
// Conceptual driver enumeration
NTSTATUS enumerate_drivers() {
    // Method 1: ZwQuerySystemInformation
    ZwQuerySystemInformation(SystemModuleInformation, ...);
    
    // Method 2: Direct kernel object scanning
    for each module in PsLoadedModuleList {
        validate_signature(module);
        check_whitelist(module);
    }
    
    // Method 3: Driver object enumeration
    for each driver in ObpDirectoryObjectType {
        if (driver.type == IoDriverObjectType) {
            check_driver_object(driver);
        }
    }
}
```

### Anti-Debugging Techniques

Anti-cheat drivers employ various anti-debugging measures:

| Technique | Description |
|-----------|-------------|
| Obfuscated code | Code is heavily obfuscated to resist static analysis |
| Runtime decryption | Critical code sections decrypted at runtime |
| Integrity checks | Driver validates its own code at runtime |
| Timing checks | Detects single-stepping via timing analysis |
| Exception-based | Uses exceptions to detect breakpoints |
| Hypervisor detection | Checks for VM/hypervisor presence |

---

## 5. Scanning Methodologies

### Memory Scanning

Anti-cheats use multiple memory scanning strategies:

#### Pattern-Based Scanning
```
Known cheat signature:
  48 89 5C 24 08        ; mov [rsp+8], rbx
  57                    ; push rdi
  48 83 EC 20           ; sub rsp, 20h
  48 8B FA              ; mov rdi, rdx
  48 8B D9              ; mov rbx, rcx
  
  → "Cheat XYZ v2.1 detected"
```

#### Heuristic Scanning
```
# Heuristic detection patterns:
- Function hooks at known API entry points
- Modified game code sections
- Injected DLLs in game process
- Suspicious memory allocations
- Unusual instruction patterns
```

### PCIe Scanning

Anti-cheats scan the PCIe bus for DMA hardware:

```
# PCIe scanning approach
1. Read /sys/bus/pci/devices/ (Linux) or Enum PCI (Windows)
2. For each device:
   a. Check vendor ID against known FPGA vendors
   b. Check device ID against known DMA device IDs
   c. Read BAR contents and look for signatures
   d. Check driver (pcileech.sys, leechcore.sys, etc.)
   e. Validate PCIe capability structures
3. Build topology tree and validate parent-child relationships
```

---

## 6. Signature Detection

### Signature Types

| Type | Description | Example |
|------|-------------|---------|
| Byte patterns | Raw instruction sequences | `48 8B 05 XX XX XX XX` |
| String patterns | ASCII/Unicode strings | "pcileech", "cheat" |
| Function signatures | Function prologues/epilogues | Standard x64 function frames |
| Import patterns | API call sequences | `ReadProcessMemory` chains |
| Behavioral patterns | Call patterns over time | Repeated memory reads |

### Signature Update Cycle

```
Day 0: New cheat released
Day 1: AC vendor samples cheat
Day 2: Signatures extracted
Day 3: Signatures tested
Day 4: Signatures deployed
Day 5: Cheat detected
Day 6: Cheat author updates
Day 7: Cycle repeats
```

---

## 7. Behavioral Detection

### Statistical Analysis

Anti-cheats maintain statistical models:

```python
# Conceptual behavioral analysis
class PlayerBehaviorModel:
    def __init__(self):
        self.reaction_time_distribution = NormalDist(mu=200, sigma=50)  # ms
        self.accuracy_distribution = NormalDist(mu=0.3, sigma=0.15)
        self.positioning_entropy = calculate_entropy(historical_positions)
    
    def analyze_player(self, player_data):
        # Compare player behavior to model
        reaction_zscore = (player_data.avg_reaction - self.reaction_time_distribution.mu) / self.reaction_time_distribution.sigma
        accuracy_zscore = (player_data.accuracy - self.accuracy_distribution.mu) / self.accuracy_distribution.sigma
        
        if reaction_zscore > 3.0:  # 3 standard deviations
            flag_suspicious("Abnormal reaction time")
        
        if accuracy_zscore > 3.5:
            flag_suspicious("Abnormal accuracy")
```

### Detected Behavioral Patterns

| Pattern | Detection Method | Confidence |
|---------|-----------------|------------|
| Perfect tracking | Crosshair movement analysis | High |
| Pre-firing | Timing of shots vs. enemy visibility | High |
| Wall-hacking | Position decisions based on hidden info | Medium |
| Aim-assisting | Aim acceleration patterns | Medium |
| ESP usage | Movement patterns suggesting knowledge | Low |

---

## 8. Update & Response Cycle

### Update Mechanisms

Both EAC and BattlEye use cloud-based update systems:

```
Client → Cloud: Upload scan results
Cloud → Client: Download new signatures
Cloud → Client: Download new scanning rules
Cloud → Client: Update driver (BattlEye)
```

### Ban Waves

Anti-cheats often batch bans:

| Timing | Purpose |
|--------|---------|
| Immediate | Obvious cheats (DLL injection, known signatures) |
| Delayed (days) | Collect evidence, avoid tipping off cheat devs |
| Ban waves | Mass bans to make it harder to test countermeasures |
| Hardware bans | Ban hardware IDs for repeat offenders |

---

## 9. Game-Specific Implementations

### How Games Integrate Anti-Cheat

| Integration Level | Description | Example |
|------------------|-------------|---------|
| SDK integration | Game calls AC functions directly | Fortnite, Apex Legends |
| Service-based | AC runs as separate service | PUBG, Rainbow Six |
| Hybrid | Both SDK and service | Rust, DayZ |

### Game-Specific Behavior

Different games configure anti-cheats differently:

```
Fortnite (EAC):
  - Very aggressive scanning
  - Frequent memory scans (every 2-5 seconds)
  - Hardware fingerprinting enabled
  - Cloud analysis intensive

PUBG (BE):
  - Aggressive scanning
  - Driver blocking active
  - Hardware ban system active
  - Behavioral analysis focused

Rust (EAC):
  - Moderate scanning frequency
  - Plugin-based detection
  - Community server reporting
```

---

## 10. Research Notes

### Observations from Public Research

Based on publicly available research and documented behavior:

1. **EAC focuses more on cloud analysis** — Uploads more data for ML processing
2. **BattlEye focuses more on local detection** — More aggressive kernel-level scanning
3. **Both are moving toward hardware-level detection** — PCIe scanning becoming standard
4. **Timing analysis is becoming more sophisticated** — Statistical methods improving
5. **Hardware bans are becoming more common** — Especially for repeat offenders

### Known Limitations

| Limitation | Description |
|-----------|-------------|
| False positives | Legitimate hardware can trigger flags |
| Performance impact | Scanning affects game performance |
| Privacy concerns | Deep system scanning raises privacy questions |
| Cat-and-mouse game | Continuous arms race with cheat developers |
| Platform differences | Windows vs. Linux detection capabilities differ |

### Research Directions

Areas of active research in anti-cheat technology:

- **Machine learning for behavioral detection** — More sophisticated pattern recognition
- **Hardware attestation** — TPM-based hardware verification
- **Hypervisor-based monitoring** — Kernel-level monitoring from hypervisor
- **Network-based detection** — Server-side behavioral analysis
- **Cross-game intelligence** — Sharing detection data across games

---

## References

- [EasyAntiCheat Official](https://www.easy.ac/)
- [BattlEye Official](https://www.battleye.com/)
- [Windows Kernel Programming](https://www.amazon.com/Windows-Kernel-Programming-Pavel-Yosifovich/dp/1977593372)
- [PCIe Device Security Research](https://www.usenix.org/conference/usenixsecurity22)

---

> **Disclaimer:** This document is intended for security research and educational purposes. Understanding anti-cheat technology helps improve game security and promotes transparency in the industry.

---

> **Join our research community:** [Discord](https://discord.gg/JJgc2cDEK5)
