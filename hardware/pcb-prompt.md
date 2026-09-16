# Prompt: A1-4RD base PCB

Paste everything below the line into the other AI. Fill the four `<<< >>>` blanks
first — everything else is already decided.

---

You are an electronics design engineer helping me design a small custom PCB. I
have designed PCBs before at a hobby level but this is the most integrated board
I have attempted, so I want you to be actively skeptical of my choices and tell
me where I am about to make a beginner mistake. Do not be agreeable.

## What the board is for

I am building a six-inch 3D-printed desk companion called A1-4RD ("Alfred") — a
character, not a smart speaker. It has a moving jaw and a nodding head, listens
for a wake word, and talks. All heavy compute (speech-to-text, LLM, text-to-
speech) happens on a separate headless Linux server on my LAN. The board in the
figure's **base** is a thin client only: it captures audio, plays audio, drives
two servos, reads one button, and talks to the server over Wi-Fi.

This board replaces a laptop that currently does that job over an SSH tunnel, so
the software side is already working and is not in scope. I need the hardware.

## Fixed decisions — do not relitigate these

- **Compute is a Raspberry Pi Zero 2 W**, used as a module. My board is the
  carrier; the Pi plugs into it via the 2x20 0.1" header. I want the Pi
  removable (SD card access, and I do not want to solder a $15 board down).
- **Audio is I2S in and out**, not USB, not analog. Digital MEMS mic in, Class-D
  I2S amp out to a small speaker.
- **Two hobby servos**: one jaw, one neck nod. Standard 3-wire, 5V, ~9g class
  (SG90/MG90S). They are driven by GPIO PWM from the Pi unless you convince me
  otherwise.
- **One momentary button** on the base. This is a security control, not a
  convenience: the assistant keeps per-person memory, and pressing the button is
  how a user asserts identity so it will not read one person's private notes to
  another. Treat it as a deliberate physical input, debounced properly.
- **Single USB-C input, 5V.** One cable to the base, nothing else.
- The board lives entirely inside a 3D-printed enclosure I am designing in
  parallel. Mechanical constraints below are real, not aspirational.

## Blanks I need to fill

- Enclosure internal envelope available to the PCB: <<< e.g. 80 mm x 80 mm
  footprint, 22 mm internal height >>>
- Speaker I intend to use: <<< e.g. 4Ω 3W, 28 mm round, or "recommend one" >>>
- Assembly: <<< hand-solder everything / JLCPCB economic assembly for the
  fine-pitch parts and hand-solder the rest / full turnkey assembly >>>
- Quantity and rough budget ceiling per board: <<< e.g. 5 boards, $40 each >>>

## Functional requirements

1. Accept 5V from USB-C, protected, and distribute it to three loads: the Pi,
   the audio amplifier, and the servos.
2. Power the servos from a rail that cannot brown out the Pi. Servo stall current
   is the dominant transient in this design and I expect it to be the thing that
   crashes the Pi if I get it wrong.
3. I2S digital microphone, positioned so I can port it acoustically to a hole in
   the printed shell.
4. I2S Class-D amplifier driving one small speaker, with a sensible output
   filter for the speaker I pick.
5. Two 3-pin servo headers, keyed or clearly silkscreened, with the signal lines
   protected against a shorted or miswired servo.
6. One momentary button, hardware-debounced or explicitly documented as software-
   debounced with the RC values chosen.
7. A status indicator visible through the enclosure — single LED or one
   addressable LED, your call, argue for one.
8. Test points on every power rail and on the I2S clock lines.

## Constraints and things I already know are traps

Address each of these explicitly in your answer. If one does not apply, say so
and why.

- **USB-C CC pull-downs.** I know a USB-C receptacle without 5.1k resistors on
  CC1 and CC2 gets no power from a compliant charger. Confirm the exact
  configuration for a sink-only, 5V-only device.
- **Shared I2S bus for simultaneous capture and playback.** The Pi has one I2S
  peripheral. I want mic and amp on it at the same time, sharing BCLK and LRCLK
  with separate data lines. Tell me honestly whether this works reliably on a Pi
  Zero 2 W with mainline Linux drivers, which specific mic and amp parts are
  known-good for it, and what the failure mode is if it does not. If it does not
  work, propose the alternative and what it costs me in board area and money.
- **Servo transients.** Specify the bulk capacitance, the rail topology, and
  whether the servo rail needs its own regulator or can share the input. Show me
  the worst-case current budget as a table: Pi Zero 2 W peak, amp at full output,
  two servos stalled simultaneously, sum, and the input supply I therefore need.
- **Ground.** This board has a switching amplifier, a sensitive digital mic, and
  two motors on it. Tell me the grounding and placement strategy, not just
  "use a ground plane."
- **Trace widths.** Give me actual numbers for the servo rail and the main 5V
  rail on 1 oz copper, with the assumed temperature rise.
- **Pi header pin conflicts.** Produce a complete pin assignment table for the
  2x20 header showing every pin I use, what it does, and confirming I have not
  collided with the I2S peripheral pins or an I2C EEPROM address.
- **Mechanical.** Board outline, mounting hole positions and diameter, connector
  edge positions, and maximum component height per zone must be things I can hand
  straight to my CAD model. Assume M3 hardware unless you argue for M2.5.
- **Part availability.** Every part in the BOM must have an LCSC part number and
  be in stock. No unobtainium, no parts that only exist on a breakout board.

## What I want you to produce

Work in this order and stop for my input between stages 1 and 2.

**Stage 1 — architecture.** A block diagram in text, the power budget table, the
answer to the shared-I2S question, and the Pi pin assignment table. List every
open question you need me to answer before schematic. Flag anything where you
are guessing.

**Stage 2 — schematic.** Full schematic as a netlist I can import into KiCad 9,
plus a human-readable per-block description with every part value justified. Not
a picture, not pseudocode — something I can actually import or transcribe without
inventing values.

**Stage 3 — BOM and layout guidance.** BOM with LCSC part numbers, footprints,
and quantities. Then placement zones, routing priorities, layer stackup, and a
pre-fab review checklist specific to this board.

**Stage 4 — mechanical interface sheet.** Board outline dimensions, hole
positions as coordinates from a stated origin, connector positions and their
required clearance to the enclosure wall, component keep-out heights, and where
the mic port and speaker must sit. This goes into my CAD model, so it needs to be
dimensioned, not described.

## How to work with me

- Ask before assuming. If a requirement is ambiguous, ask rather than pick.
- Show your reasoning on anything numerical. I will check it.
- If I propose something wrong, say it is wrong and why, then give the fix.
- Prefer boring, well-documented parts over clever ones.
- Tell me explicitly when you are uncertain about a claim, especially driver
  behavior and part availability, so I know what to verify before I spend money.
