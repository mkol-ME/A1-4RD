# Alfred revision C self-review - 2026-09-11

**Verdict: CAD-consistent engineering prototype, with an unresolved servo power-margin issue. Do not interpret the earlier clean DRC/ERC result as proof that Alfred will operate reliably.** This review checked saved revision C files independently of the prior status report. No hardware was available.

## Findings

### P1 - Servo enable has insufficient demonstrated voltage margin (unresolved)

The nominal comparator thresholds are 4.960 V rising and 4.915 V falling, before intrinsic hysteresis and component tolerances. Using the stated 2.85 A Pi/audio allocation with the servo off, a 5.1 V input, the FET pair's specified 25 C 24 milliohm maximum, and the eFuse's typical 28.3 milliohm resistance gives:

`5.1 - 2.85 * (0.024 + 0.0283) = 4.951 V`

That is already below the ideal rising threshold, before cable, connector, PCB and return-path losses. At 4.1 A total input and 2.85 A on the Pi/audio branch:

`5.1 - 4.1 * 0.024 - 2.85 * 0.0283 = 4.921 V`

Only about 6 mV remains above the ideal falling threshold. These illustrative mixed maximum/typical calculations are not a complete worst-case proof or a prediction of every unit. They establish that the claimed load allocation does not have demonstrated servo-availability margin. Hot resistance and comparator tolerances must be included. A narrow trace feeding a sense input does not by itself imply that load current flows through it; a full copper/contact resistance model was not performed.

Consequence: under high Pi/audio load the jaw may not enable, or it may shed power and recover repeatedly. Resolve through measured rail/drop/threshold data and, if necessary, a revised power path and supervisor hysteresis. Simply lowering thresholds can sacrifice Pi brownout protection.

Sources: [FDS6673BZ gate-drive and resistance specifications](https://www.onsemi.com/download/data-sheet/pdf/fds6673bz-d.pdf), [TPS25947 on-resistance and current limiting](https://www.ti.com/lit/ds/symlink/tps25947.pdf), [TLV3012B comparator/reference specifications](https://www.ti.com/lit/ds/symlink/tlv3012.pdf).

### P1 - Software retry policy does not provide a hardware latch (unresolved)

U5 combines SUPPLY_OK with GPIO22. If GPIO22 stays high while the Pi rail dips and recovers, U5 can re-enable U3 before Linux notices the event. The eFuse's own latch-off fault response does not turn every external enable transition into a latched fault. The documentation's instruction to clear GPIO22 is useful but cannot guarantee no fast hardware retries. Scope startup and load-step behavior; dependable one-shot shutdown needs an explicit hardware latch or a validated equivalent. No hardware latch was added in this review.

### P2 - Manufacturing metadata and BOM note (fixed)

The Gerber job had 120.1 x 94.1 mm, while the documentation claimed centerline dimensions. Verified all four Edge.Cuts segments define exactly 120 x 94 mm. Corrected job Size to those centerline dimensions and documented that KiCad's regenerated job includes stroke width. Copper and outline geometry were not changed.

R109's purpose text still quoted revision B thresholds. Corrected it in design-data.json, BOM.csv and Component-ledger.md to match R107 and the revision C calculations.

The default DNP R304 still has paste apertures. This is not a netlist fault; assembly instructions now explicitly request stencil-aperture suppression for the default build. R304 remains DNP in the native schematic/PCB and BOM.

### P2 - Integration and price claims remain conditional

The supplied voiceHAT overlay source and smoke-test logic are plausible for the chosen separate I2S data paths and GPIO17 amplifier enable. They have not been compiled/booted on the target Pi or tested with actual capture/playback. The test's successful process exit would not establish microphone sensitivity, sound quality, absence of acoustic feedback, or echo cancellation. [Raspberry Pi codec source](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/googlevoicehat-codec.c).

Recomputed the grouped lean component allowance: $43.06. The $17.74 comparison is against the prior recommended basket containing extra spares; fitted revision C electronics cost $2.44 more than revision B. This is not a current distributor quotation. The microphone is EOL and its actual sourcing cost/availability remains a procurement dependency. No new price or stock verification was performed in this self-review.

## Verification completed

- Fresh KiCad 10.0.6 DRC, zone refill in memory, all-track errors, schematic parity, and all severities including exclusions: zero violations, zero unconnected items, zero parity issues. Saved board geometry was not altered by the check.
- Fresh ERC: zero errors and warnings. Existing ignored categories remain visible in the reports; they were not enabled and audited individually.
- Independently exported schematic netlist: all 358 corresponding PCB pad entries agree.
- Nine freshly exported Gerber layers match the delivered files after removing only creation-timestamp lines. This covers copper, masks, paste, silkscreen and outline; drill geometry was not independently re-exported in this pass.
- Connector and eight mounting-hole positions/rotations match revision B. All BOM references appear in the placement file, which additionally contains the eight mechanical holes.
- Confirmed R304 is DNP and calculated purchasing total directly from the grouped BOM.
- Rebuilt archives and checksum manifest after the corrections.

## Limits of this review

This does not establish physical startup, regulator transient stability, thermal/EMC performance, assembly yield, enclosure fit or jaw reliability. The TL431 regeneration loop, modified PFET gate charge, eFuse startup with large capacitors and real simultaneous audio remain bench-validation items. The analog circuit was not simulated. No board or software was deployed.
