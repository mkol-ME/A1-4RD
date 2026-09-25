# Alfred physical build: first prototype

The repository has a working Windows laptop client and Linux server. No body,
carrier PCB, Pi client, jaw mechanism, or neck mechanism has been built or
purchased yet. Anton now uses an MI50 for Alfred's model. This plan starts with
a bench prototype so the PCB and enclosure can be based on measured interfaces.

On 2026-09-23, Anton reported `gemma4:26b-a4b-it-q8_0` in `ollama ps`; the user
described the current model as “gemma4 28b.” Confirm the intended model tag
separately if server documentation is updated. The model choice does not change
the physical client's requirements.

## Fixed project choices

- Six-inch printed figure, moving jaw, nodding neck.
- Raspberry Pi Zero 2 W in the base; server keeps Whisper, model, memory, and TTS.
- One USB-C power input; I2S microphone and mono class-D speaker amplifier.
- Two small 5 V servos, one button, one visible status indicator.
- V2 base adds an approximately four-inch screen for Alfred's words; see
  [display-v2.md](display-v2.md) for the preliminary interface.

## Build order and pass criteria

1. **Bring up a Pi Zero 2 W on the bench.** Boot Raspberry Pi OS, connect to
   Wi-Fi, SSH into Anton, and verify the existing server endpoints through the
   tunnel. Use a suitable micro-USB supply for the Pi during this stage.
2. **Run the existing client on the Pi with temporary audio devices.** Verify
   Wi-Fi/SSH tunnel, microphone capture, sentence playback, and music playback.
   `client/listen.py`, `client/talk.py`, and `client/music.py` already have the
   server protocol, but contain Windows/WASAPI assumptions. The Pi port is work
   to do; the existing laptop client is not proof that the Pi client runs.
3. **Prove the chosen I2S microphone and amplifier together.** Wire both to a
   Zero 2 W on a bench, with shared BCLK and LRCLK and separate DIN/DOUT. Use a
   single sound-card configuration that exposes capture and playback. Record and
   play at the same time for at least ten minutes; check captured samples,
   playback dropouts, and `dmesg`. Test cold boots too. Separate stock overlays
   can each work alone yet fail when both claim the same I2S controller. Do not
   lock in either chip or the PCB until this passes.
4. **Measure power at the actual loads.** With a current-limited bench supply,
   record Pi boot/Wi-Fi peaks, amplifier draw at the intended maximum volume,
   each servo's movement and stall current, and the worst simultaneous event.
   Measure the voltage at the Pi 5 V header during both servos starting and
   reversing. Set the supply, connector, switch, traces, and protection from
   those measurements; the Pi's 2 A recommended supply is for the Pi, not this
   complete assembly.
5. **Measure the mechanical envelope and prototype the mechanisms.** Record
   available base diameter/width, depth, internal height, head volume, jaw
   pivot, neck axis, and intended print material. Use the official Pi Zero 2 W
   mechanical drawing for Pi and connector keep-outs. Print the head/jaw pivot
   and neck joint with
   temporary servo mounts. Measure jaw closed/open angles, usable servo pulse
   range, linkage travel, physical stops, and clearance. Verify smooth motion
   without servo buzzing or binding before designing the final enclosure.
6. **Freeze interfaces, then design the carrier.** Capture board outline,
   mounting-hole coordinates, Pi orientation and SD access, USB-C edge,
   microphone port alignment, speaker chamber, servo connectors, wire path,
   and V2 display power and mini-HDMI cable clearance.
   Only then prepare schematic, BOM, and board layout.

## First bench parts

Buy only enough to test the interfaces before committing to the enclosure or
custom PCB:

| Part | Quantity | Why now |
| --- | ---: | --- |
| Raspberry Pi Zero 2 W with soldered 40-pin header | 1 | Client target and GPIO access |
| microSD card, micro-USB Pi supply, female jumper wires, breadboard | 1 each | Boot and temporary wiring |
| I2S MEMS microphone breakout, e.g. SPH0645LM4H | 1 | Prove Pi capture and the eventual mic path |
| MAX98357A I2S mono amplifier breakout | 1 | Prove Pi playback on the same I2S controller |
| 4–8 Ω speaker rated for the amplifier's intended output | 1 | Audio test; final diameter waits for enclosure measurements |

The listed mic and amp are *candidates for a bench test*, not yet approved for
the carrier. The mic driver and the combined Linux sound-card configuration need
the simultaneous test above. Wait to choose the two servo models and USB-C
power components until the head geometry and load measurements are available.

## Electrical architecture to prove

```
USB-C 5 V sink -> attach/inrush and fault protection -> 5 V distribution
                                                 |-> Pi Zero 2 W
                                                 |-> audio amplifier
                                                 `-> switched/current-limited servo branch
Pi 3.3 V -> I2S microphone, button input, status LED circuit
Pi GPIO -> servo-control signals (through suitable protection)
```

Keep the servo branch's high-current path away from the Pi feed and microphone.
All branches still share a ground reference. A separate servo regulator is not
automatically a fix when its input is the same 5 V source: the supply and cable
must support total load, and the Pi must stay above its operating threshold at
its own pins during transients. Decide bulk capacitance and branch protection
from the scope/current measurements, not a generic capacitor value.

For a 5 V sink-only USB-C receptacle, CC1 and CC2 each need their own 5.1 kΩ
pull-down to ground. A design with substantial downstream bulk capacitance needs
an attach-controlled power path so that capacitance is not exposed directly on
VBUS at plug-in. A plain 5 V Type-C source can advertise at most 3 A; verify its
advertisement and the cable before treating 3 A as available. If measured load
exceeds that, revisit the power architecture before making the PCB.

## Security boundary for the button

The button can request a profile or start an identification step. It cannot
authenticate a person by itself. Until an identity check exists, any press-based
profile should be treated as unverified and should not unlock private memory.
The server's memory lookup must enforce that boundary.

## Measurements needed to finish CAD and PCB

| Item | Record |
| --- | --- |
| Base and head | Outer and usable internal dimensions, wall thickness, print material |
| Pi | Header orientation, SD and port access, mounting/stack height |
| Jaw | Pivot coordinates, closed/open angles, linkage space, physical stops |
| Neck | Pivot axis, target nod angle, wire passage, stop positions |
| Servos | Exact model, body/horn dimensions, motion/stall current at 5 V |
| Audio | Exact mic, amp and speaker; speaker diameter/depth/impedance and port positions |
| Power | Pi/amp/servo current traces and lowest Pi voltage during simultaneous motion |
| Assembly | Fasteners, service opening, connector access, cable strain relief |

## Source notes

- [Raspberry Pi Zero 2 W official drawings and schematics](https://pip.raspberrypi.com/categories/584)
- [Raspberry Pi power recommendations](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Adafruit SPH0645LM4H I2S microphone breakout](https://www.adafruit.com/product/3421)
- [Adafruit MAX98357A I2S amplifier breakout](https://www.adafruit.com/product/3006)
- [Raspberry Pi device tree overlay reference](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README)
- [Reported failure when separate I2S mic and amp overlays both claim the Pi controller](https://forums.raspberrypi.com/viewtopic.php?t=317483)
- [TI USB-C sink design guide, pages 53–54](https://www.ti.com/lit/pdf/slyy228)
