# Alfred carrier - revision C

**Improved, routed 120 x 94 mm four-layer PCB for Alfred: Raspberry Pi Zero 2 W, ICS-43434 microphone, MAX98357A speaker amplifier and one FS90 jaw servo.** Open `Alfred.kicad_pro` in KiCad 10. This revision supersedes revision B for new prototype builds.

CAD validation: zero DRC violations, zero unconnected items, zero schematic parity issues, and zero ERC errors/warnings. **This is an unbuilt first article, not bench-qualified hardware.**

## What changed

- Q1/Q2 are onsemi FDS6673BZ MOSFETs with specified on-resistance at -4.5 V gate drive. R2 changes to the existing 100k value to improve gate drive.
- R114/R115 and D101 add a divided and clamped enable input for the Pi eFuse.
- The servo supply-good circuit now senses the protected Pi rail after the Pi eFuse, with earlier nominal shedding thresholds.
- **R304 is DO NOT FIT.** Leaving GAIN_SLOT floating selects 9 dB gain instead of 3 dB, removing the earlier approximately 0.8 W output limitation. Start playback quietly and verify clipping/power before maximum volume.
- The BOM distinguishes fitted parts, optional gain components and lean single-board purchasing quantities.
- `software/` contains an Alfred GPIO17 audio overlay source, a build script, a low-volume capture/playback smoke test and Pi setup instructions. Target compilation and hardware testing remain necessary.

## Files

- Native KiCad project, six schematic sheets and pinned project libraries: editable design.
- `Fabrication/`: freshly generated Gerber X2 files and separate PTH/NPTH drill files. Specify 35 um finished copper on **all four layers**, nominal 1.6 mm board, ENIG and the documented stencil.
- `Schematic.pdf`, `Assembly-top.pdf`, `Copper-layers.pdf`: current drawing exports. Assembly drawing crosses out the unfitted R304.
- `BOM-grouped.csv`: fitted quantities and lean purchase quantities for **one** board. Assemblers may require additional attrition parts. `BOM-do-not-fit.csv` identifies omitted components.
- `BOM-external.csv`: servo, speaker, supply, Pi male header, PCB and hardware allowances. Pi itself and assembly labor are excluded.
- `Design-notes.md`, `Fabrication-and-assembly.md`, `Mechanical-interface.md`: design decisions, assembly instructions and preserved enclosure interface.
- `Validation.txt`, `DRC-report.json`, `ERC-report.txt`: final CAD results. `SHA256SUMS.txt` records package checksums.

## Cost

Planning allowance: **$43.06 fitted board components**, plus $55.35 inherited external/PCB/hardware allowances, approximately **$98.41 excluding Pi**, shipping, tax, assembly, stencil and enclosure printing. Most prices remain estimates. The previous recommended purchase basket included many unnecessary spares; the revised lean board-parts basket is approximately $17.74 lower on the documented mixed estimate/price basis. The fitted circuit itself is approximately $2.44 more expensive because of the improvements. See `Cost-and-purchasing.md`; this is not a supplier quote.

## Self-review update (2026-09-11)

See `Self-review.md`. Fresh CAD checks pass, but the servo supply-good thresholds have inadequate demonstrated margin at the stated maximum load. The jaw may fail to enable or cycle as the Pi rail recovers. A software retry policy alone cannot guarantee hardware latch-off during fast transients. This remains an engineering prototype requiring power-margin and startup validation before relying on jaw operation. Manufacturing job dimensions and an obsolete BOM threshold note were corrected.

## Before relying on Alfred

Use the specified Raspberry Pi 27 W USB-C supply (5.1 V / 5 A PD profile). First validate PD startup and rails with the Pi and servo disconnected. Then verify audio, finally supervised jaw movement. Measure the Pi header voltage during Wi-Fi, loud speech, servo acceleration and reversal, verify the regeneration clamp and temperatures, and validate 30 minutes of full-duplex operation. The original enclosure geometry and fixed connector positions remain unchanged; verify actual purchased-part fit and jaw limits.

The source revision B folder was not modified. No board order or purchase was placed.
