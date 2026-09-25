# Alfred revision C fabrication and assembly

This is an unbuilt first article. The routed PCB is a native KiCad 10 board, validated with KiCad 10.0.6. The original unrouted revisions A and B remain separate.

## Fabrication specification

- Outline: 120.0 x 94.0 mm, nominal 1.6 mm FR-4, four copper layers. Copper order is F.Cu / In1.Cu / In2.Cu / B.Cu.
- Specify **35 um finished copper on all four layers**. Do not silently accept 17 um inner copper: the power distribution is on In2.Cu. Request a symmetrical standard stack with approximately 0.2 mm outer-to-inner dielectric and the balance in the core; exact impedance is not controlled.
- L1: components, signals, local power spreading. L2: ground reference. L3: separate protected power regions. L4: signals and input switch copper.
- Minimum trace and copper clearance: 0.15 mm. Ordinary signals are 0.20 mm. Via pad/drill: 0.60/0.30 mm; minimum drill-to-drill edge clearance 0.25 mm. Copper-to-edge minimum 0.30 mm. The USB manufacturer's NPTH-to-copper geometry uses the project minimum hole clearance of 0.15 mm.
- ENIG finish preferred for QFN and microphone assembly; lead-free HASL is less flat. Green solder mask, white top silkscreen. No bottom components.
- All eight mounting holes and the 0.50 mm microphone acoustic bore are NPTH. USB shield slots are plated; use the Excellon routed-slot data. Preserve drill files separately for plated and non-plated features.
- Ordinary vias are tented on both sides. U1 and U7 each have a 0.30 mm thermal via in the exposed ground pad. The top pad aperture remains exposed; bottom tenting is requested. Via filling/capping is not specified. Inspect for solder loss into these holes during first-article reflow.
- Use a 0.10 mm stencil for the QFN, MEMS mic and tiny eFuse lands. Inspect the stencil apertures against the supplied F.Paste Gerber, including U2/U3's joined corner-pad shapes. No paste belongs in the mic bore. Apply a conservative paste volume to the thermal pads; do not hand-flood them.
- The Gerber ZIP contains only production layers and drill data. Assembly drawings and coordinate tables are separate.

## Routing decisions

High-current eFuse inputs and outputs expand into top copper and six-via banks. Their 0.30 mm necks are short escapes from 0.30 mm package lands, not long power traces. Broad internal copper carries the Pi and servo current. Each MOSFET current pin has a separate 0.60 mm escape and via. USB power contacts use multiple vias and bottom copper. Power and ground pads connect directly to planes; expect to need an adequately powered soldering iron for the through-hole connectors and bulk capacitors.

Speaker paths are widened where pad and trace spacing permits, with short finer branches at the IC and filter capacitors. The switching outputs terminate in the two 10 uH inductors; the differential capacitor is on their speaker side. Keep the external speaker wires together and short. Neither speaker terminal is ground.

The second layer is the common ground reference. Mic, logic and protection ground lands have local vias; the servo return enters near its bulk capacitor. Power does not traverse the microphone region. The antenna rectangle and mounting-hardware clearances have actual copper keepouts, not just drawing notes. Use nylon Pi mounting hardware, especially at H8 in the antenna region.

## Revision C population

Do not fit R304. Its open gain strap selects 9 dB; the assembly drawing crosses it out. Fit new R114/R115 and D101. Q1/Q2 are onsemi FDS6673BZ. R2 is 100k, R107 is 29.8k. Check D101 cathode toward PI_EN_UVLO. All other original components remain fitted.

## Assembly order

1. Reflow SMT parts, with the mic and QFNs carefully aligned. Follow the microphone manufacturer's moisture/reflow handling instructions. Do not ultrasonically clean or force liquid/air into the mic port.
2. Inspect the QFN and RPW land joints under magnification. Check rail-to-ground resistance and input-switch orientation before applying power.
3. Hand-solder the electrolytics, connectors, socket, button and LED. Observe capacitor polarity. Mount R408 6 mm above the board and keep plastic/wires at least 5 mm from its body.
4. Trim underside leads within the mechanical allowance. Use the specified removable Pi header arrangement and supports; do not force a misaligned 40-pin socket.
5. Fit the mic gasket and separate acoustic duct. Keep speaker and servo vibration away from it. Check the SD service window against the actual mated Pi.

## First-article acceptance tests

These are physical tests still to perform; CAD checks do not establish them.

- With Pi/servo disconnected, use a current-limited bench setup or monitored specified PD source. Verify requested 5 V contract, polarity, PI_5V, and that the servo rail is initially off. Do not bypass the PD power path in normal service.
- Use the specified Raspberry Pi 27 W USB-C supply with its captive cable, supporting 5.1 V / 5 A. A generic 'USB-C charger' is not an equivalent substitute.
- Confirm no two supplies drive the Pi 5 V rail simultaneously. Do not power the Pi through its own power connector while this carrier supplies the header.
- Exercise the servo supply first with an electronic load. Check current limit, latch-off/recovery behavior and SUPPLY_OK shutdown threshold. Scope PI_5V at the Pi header with a short ground spring.
- With Pi and audio active, command rapid jaw movement and brief controlled load transients. Avoid sustained mechanical stall. Check the Pi undervoltage status and verify the minimum rail voltage during the transient. Verify the 5.59 V nominal regeneration clamp under an injected regenerative pulse and check R408 temperature.
- Check sustained maximum intended speaker volume for clipping, excessive IC/inductor temperature and audible artifacts. Confirm the filter response with the actual speaker.
- Prove simultaneous capture/playback at one common I2S sample format and rate on the chosen Linux image before relying on barge-in. Echo cancellation is a separate system requirement; shared clocks alone do not provide it.
- Confirm button debounce and servo enable/PWM startup behavior. Calibrate jaw endpoints so the linkage cannot force the servo against a stop.

No physical board has been manufactured or tested, and no purchasing cart has been ordered. See Cost-and-purchasing.md for the revised mixed estimate and checked-price basis; prices and availability require a current supplier quote.

The board outline is defined by the Edge.Cuts centerline: exactly 120 x 94 mm. The Gerber job size uses that centerline, excluding the outline stroke width.

Self-review: the paste Gerber retains apertures for optional R304; request their suppression for the default DNP assembly. Do not populate R304. The Gerber job Size is normalized to the Edge.Cuts centerline (120 x 94 mm); native KiCad export includes the 0.1 mm outline stroke and must be normalized after regenerating the job.
