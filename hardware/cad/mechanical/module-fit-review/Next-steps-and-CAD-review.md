# Alfred: module prototype and CAD fit review

Status: preliminary dimensional review, not an electronics-inclusive assembly clearance approval. Reviewed 13 September 2026. No native CAD was changed.

## Decision

Keep the Pi Zero 2 W and the existing local Ubuntu server. The Pi runs the microphone, playback, SSH client and jaw timing; the server runs transcription, language generation and synthesized voice. Prototype with assembled audio modules before committing to custom PCB manufacture. Keep one FS90 positional jaw servo, matching the current mechanical assembly; the historical neck-servo idea is not implemented in this CAD.

## Files actually checked

Source: rev-b/

Fresh mesh-audit.json records SHA-256, bounds, watertightness, winding and positive volume for all 16 STL files. All passed those mesh checks. README, generator geometry and existing geometry-audit/jaw-sweep reports were also reviewed. Existing reports show no sampled printed-part collisions from 0 to 20 degrees; that motion test was not rerun here and excluded commercial hardware. Native SolidWorks geometry was not rebuilt in this review.

## Mechanical findings

| Interface | Evidence | Required action |
|---|---|---|
| External size | Plinth mesh 137 x 111.6 mm, top Z=56.8; head reaches Z=202 | Retain external envelope. Overall volume is adequate for a preliminary module layout, not a completed fit approval. |
| Base cavity | Modeled 127 x 101.6 x 50.8 mm above floor | Preserve cosmetic shell; lay out the assembled modules with connector and cable envelopes before changing openings. |
| Bottom cover | Four old PCB support centers (7.5,7.8), (119.5,7.8), (7.5,93.8), (119.5,93.8); support tops Z=9 | Use these supports for a removable adapter tray. Add separate M2.5 Pi mounts and module retention. Account for tray thickness and screw ends. |
| Pi | 65 x 30 mm PCB; old CAD assumes Pi mounted on custom carrier | Existing enclosure supports cannot directly mount the Pi. Establish Pi orientation, header height, SD removal and power-plug access in the new tray. |
| Speaker | Existing nominal pocket 72 wide x 19 deep x 32 high; source now offers Adafruit 3351 at 70 x 17 x 30 in installed orientation | Nominal total slack is 2 mm in each axis, before foam and tolerances. Verify tabs, cable exit and lid. Retain cradle provisionally. Do not infer screw compatibility from envelope fit. |
| Microphone | Duct is tied to old PCB acoustic bore at (13.5,11.8), roof Z=9 | Breakout needs its own support and sealed acoustic adapter. Existing narrow lid is not a breakout mount. Align actual module port, keep it unobstructed and isolate speaker vibration. |
| Button | Stem bottom Z=15.1; old assumed switch actuator top Z=14.9 | Add a supported switch beneath the existing stem or revise stem length. Preserve approximately 0.2 mm initial gap only after checking actual actuator travel and print tolerance. |
| Rear openings | USB X=23.5..43.5, Z=6.5..18.5; SD X=81.5..115.5, Z=19.5..31 | These correspond to the custom PCB arrangement. Recheck/reposition for final Pi and power entry; plug body and removal paths matter, not just connector faces. |
| Servo and jaw | FS90 nominal body 23.2 x 12.5 x 22; cradle is strap-mounted; shaft target Y=58,Z=176, axis X | Actual body, mounting ears, output shaft, horn and cable must be added/measured. Coupon proves body fit only. Verify 8 mm horn radius and 35.114 mm link before powering. |
| Torso/head | Existing geometry and wiring route retained | No module-driven cosmetic redesign indicated. Keep cable service loop behind moving jaw. |

## Prototype hardware baseline

- Raspberry Pi Zero 2 W, microSD and a suitable regulated supply.
- Adafruit ICS-43434 microphone breakout 6049, matching the microphone family already used in the custom design. Exact board/port drawing still needs to be imported before mounting design is released.
- Adafruit MAX98357A amplifier breakout 3006. Listed planar dimensions 19.4 x 17.8 mm. Its published 3 mm height must not be used as the completed assembly envelope: the fitted terminal block, headers and wires require more clearance.
- Adafruit 3351 enclosed 4-ohm, 3 W speaker as the nominal cradle-compatible candidate.
- FS90 positional servo and original horn, existing button function, wiring and mounting hardware.

These are engineering baseline candidates, not a complete purchase list. Header soldering may still be required. No purchase has been made. The module mic/amp still require Pi audio configuration and real target testing; the previous custom-board overlay is not automatically validated by choosing similar chips.

## Next steps in order

1. Finish the prototype wiring/power design and complete module/connector list. Allocate audio pins and a servo timing method that does not conflict with I2S. Preserve controlled servo startup. Size and separate the motor power branch; do not power the servo from a GPIO or route its current through the Pi. For early bench tests, separate regulated motor power with common ground is practical; it is not a change to the final one-cable requirement. Avoid tying two supply outputs together.
2. Add exact purchased-part envelopes to the CAD assembly, including terminal blocks, headers, horn, plugs and cable bends. Design the adapter tray, microphone support/duct interface and switch support; then update rear access only where necessary. Run static and motion clearances including those parts. Do not print the existing base as a final module-compatible enclosure yet.
3. Obtain the prototype electronics after the list is complete. Print fit coupon 15 first, then servo cradle 12, drive link 13 and jaw 10 as test pieces. Measure the real servo shaft and horn against the CAD target before committing to cosmetic prints.
4. Prove the Pi client on the bench: record speech, send it to the existing local server, play streamed replies and reconnect after a network interruption. Confirm audio levels and buffering. Then add synchronized servo motion, starting with the horn/link disconnected and a small calibrated travel range.
5. Test the installed electronics: speaker loudness, microphone pickup, servo interference, supply droop and Pi undervoltage reporting, temperatures, startup/restart behavior and cable clearance. Run an extended conversation session at the intended loudness and motion settings. Log outcomes rather than treating CAD or electrical-rule checks as physical validation.
6. Incorporate measured fit corrections, print the final base internals and cosmetic pieces, and assemble. Decide afterward whether a custom PCB provides enough benefit to justify fabrication; the earlier PCB Rev E remains incomplete and is not an ordering release.

## Manufacturer references

- Pi: https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/
- Microphone: https://www.adafruit.com/product/6049
- Amplifier: https://www.adafruit.com/product/3006
- Speaker dimensions: https://www.adafruit.com/product/3351
- Servo: https://www.pololu.com/product/2818/specs
