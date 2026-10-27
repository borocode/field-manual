# A1236 (iPod Nano 3G) Reverse Engineering & Silicon Bringup

## Problem
The Apple iPod Nano 3rd Generation (Model `A1236` / `MB261`, colloquially known as the "Fat Nano") was historically abandoned by open-source firmware projects (such as `freemyipod`) around 2010. While the 1st and 2nd generation Nanos and the 5.5G/6G Classics received custom bootloaders and Rockbox support, the 3G remained unsupported due to:
1. Undocumented Flash Memory Controller (FMC) hardware registers.
2. A lack of publicly documented register-level differences between the advertised `S5L8701` SoC and the actual silicon.
3. Strict USB Device Firmware Upgrade (DFU) image transfer limits in SecureROM that abort attempts to directly inject large custom kernels into RAM.

## Environment
* **Target Device:** Apple iPod Nano 3rd Generation (`A1236`, EMC 2174, 4GB/8GB NAND).
* **SoC:** Samsung Application Processor (ARM926EJ-S r5 core).
* **Host Toolchain:** Linux / WSL2 environment with `arm-none-eabi-gcc` (9.2.1+), `libusb-1.0`, and `usbipd-win` for USB passthrough from Windows.
* **Exploit Framework:** `wInd3x` DFU payload injector.

## What Was Observed

### 1. Silicon Identification vs. Marketing Documentation
Marketing literature and service teardowns designated the chip as Samsung `S5L8701`. However, querying the chip register space and dumping the 64 KB SecureROM revealed the hardware identifier:

```text
BootROM Signature: 87020000000001
Silicon Readback:  S5L8702 Rev.0
```

The device shares its core processor memory map and peripheral definitions with the iPod Classic 6G (`S5L8702`), but interfaces with raw multi-level cell NAND flash like the Nano 2G (`S5L8700`), making generic Classic 6G builds incompatible without low-level driver shims.

### 2. USB DFU 256 KB Buffer Constraint
When injecting a custom kernel directly over USB DFU mode, image uploads exceeding 256 KB (`0x40000` bytes) failed consistently at chunk 129 with USB status 3 (`errWRITE` / stall). The Apple SecureROM staging buffer in internal SRAM (IRAM) allocated for DFU transfers has a hard 256 KB upper bound:

```text
Host -> DFU_DNLOAD (Chunk 1..128)  -> ACK
Host -> DFU_DNLOAD (Chunk 129)     -> STALL (Pipe Error / errWRITE)
```

Attempting to upload a full monolithic OS image (e.g. 5–9 MB binary) directly via DFU is fundamentally rejected by the bootrom hardware window.

## What Helped

### 1. Two-Stage Boot Architecture
To bypass the 256 KB DFU limitation:
1. **Stage 1 Payload (< 64 KB):** A minimal tethered RAM bootloader was compiled strictly under 64 KB. This payload is uploaded via DFU into internal SRAM (`0x22000000`) and executed.
2. **Hardware Initialization in RAM:** The Stage 1 bootloader initializes the system PLLs, clock gates, display controller, and clickwheel ADC, rendering an interactive development menu directly from memory.
3. **Stage 2 Target Architecture:** Stage 1 is designed to initialize the FMC NAND flash controller and load the larger secondary operating system binary from the onboard FAT32 partition once the Flash Translation Layer (FTL) driver integration is complete.

### 2. Verified Peripheral Register Map
Through hardware spew analysis and register probing, the following subsystem base addresses were mapped and verified on physical hardware:

| Subsystem | Base Address | Verified Details & Behavior |
| :--- | :--- | :--- |
| **BootROM** | `0x00000000` | 64 KB Apple SecureROM (`0x00000000 - 0x0000FFFF`). |
| **Internal SRAM (IRAM)** | `0x22000000` | 256 KB internal memory buffer for tethered DFU staging. |
| **External SDRAM** | `0x08000000` | 32 MB system RAM base. |
| **Display Controller** | S5L8702 LCD Controller | Readback Silicon ID: `0x71915800` (`lcd type: 4`). 320x240 RGB. |
| **Clock Generator** | `0x3C500000` (`CLKGEN`) | `GATES1: 0x00019013` (Bit 8: NAND clock gate; LCD gate enabled). |
| **Flash Controller** | `0x39400000` (`FMC_BASE`) | 8-bit NAND bus with hardware ECC engine. |
| **DMA Engine** | PL080 DMA | Dual-channel DMA for high-speed audio and storage buffers. |

### 3. Peripheral Initialization Sequence
* **LCD Engine:** The 320x240 LCD controller requires setting pixel clock divider registers before writing framebuffers. Once un-gated, text and bitmap buffers render without visual tearing.
* **Clickwheel ADC:** Clickwheel touch sliders communicate over the internal ADC lines, while physical button clicks (`SELECT`, `MENU`, `PLAY`, `PREV`, `NEXT`) trigger discrete GPIO line interrupts.
* **Piezo Audio:** The onboard clicker is driven via a dedicated PWM frequency register, enabling audible boot chime feedback before the main audio DAC is initialized.

## Limits
* **NAND Flash Translation Layer (FTL):** While raw read/write access to the FMC register space is operational, Samsung's proprietary wear-leveling algorithms require careful block allocation to prevent corrupting the stock Apple firmware partition tables.
* **Tethered Boot:** Executing code in RAM via DFU requires a USB host upon every cold power cycle unless written directly to the NOR/NAND boot sector.

## Related Field Notes
* [Rabbit R1 Hardware Architecture, Bootloader Unlock & GSI Porting](rabbit-r1-bootloader-unlock-and-gsi.md) — Low-level BootROM exploits and peripheral driver bringup.
* [Provenance & Postmortems: Defunct Tools & Protocols](defunct-protocols-and-homebrew-provenance.md) — Historical hardware lineage and reverse-engineering provenance.

## Sources & Credit
* [freemyipod archive documentation](https://freemyipod.org/) for S5L8700 / S5L8702 reverse engineering.
* [wInd3x USB DFU exploit engine](https://github.com/freemyipod/wInd3x).
* [usbipd-win project](https://github.com/dorssel/usbipd-win) for USB device virtualization across Windows and WSL2.
