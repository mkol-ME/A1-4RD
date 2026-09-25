# Alfred carrier - revision D

PCB for Raspberry Pi Zero 2 W, ICS-43434 microphone, MAX98357A amplifier and one FS90 jaw servo. Four copper layers, 120 x 94 mm. Open `Alfred.kicad_pro` in KiCad 10.

Revision D replaces revision C for prototype builds. **The circuit changes are complete and CAD-checked; this remains unbuilt hardware requiring bench qualification.**

## Fixes

- Lower-loss SI4459BDY-T1-GE3 input MOSFETs reduce calculated pair drop at 4.1 A from 98 mV to 67 mV at the stated 25 C rating.
- TPS389001DSET replaces the old comparator. Nominal cutoff is 4.842 V; recovery threshold is 4.871 V followed by about 107 ms stable-rail qualification.
- A Nexperia 74AUP1G74 hardware arm latch prevents rail recovery from restarting the servo while request stays high. Re-arming requires a deliberate low-to-high request after supply-good.
- R304 remains unfitted for 9 dB amplifier gain; its stencil apertures are now removed.
- Connector and mounting-hole positions remain unchanged.

## Validation and limits

Fresh DRC, schematic parity and ERC pass. `Validation.txt` records netlist, manufacturing and logic checks. The latch passed 65,536 eight-event sequences in a truth-table model; this is not analog or physical testing.

The earlier nominal threshold conflict is removed. At the illustrative maximum load, calculated static margin to the upper threshold is about 42 mV when enabling and 51 mV while running, before additional cable/contact/PCB losses. Temperature and actual load still limit jaw availability. Measure the Pi-header voltage and verify intended operation under combined load. See `Design-notes.md` and `Self-review.md` for bounds and acceptance tests.

## Build files

`Fabrication/` contains current Gerbers, PTH/NPTH drills and normalized job dimensions. The three PDFs are current schematic, assembly and copper exports. Use `BOM-grouped.csv`, `BOM-do-not-fit.csv`, `Placement-coordinates.csv` and `Fabrication-and-assembly.md` together. The placement table includes THT and mechanical items; confirm machine rotation conventions with the assembler.

`software/` contains audio overlay source, a quiet duplex test and the revised jaw-enable sequence. Target compilation and physical audio testing remain necessary. Use the specified Raspberry Pi 27 W USB-C supply through this carrier; do not simultaneously power the Pi's own power connector.

## Cost

Fitted electronics allowance: **$43.71**, approximately **$0.65 more than revision C**. Combined inherited allowance: **$99.06 excluding Pi**, shipping, tax, assembly, stencil and enclosure. This is a mixed planning estimate, not a checkout quote; see `Cost-and-purchasing.md`.

Start with electrical loads and the jaw linkage detached. Validate startup, fault latching, Pi-header minimum voltage, audio and servo regeneration before relying on Alfred. Previous revisions remain in separate folders.
