# Explaining the A1-4RD base to an AI: the CAD side

## First, be clear about what you are asking for

An AI cannot hand you a good STEP file. It has no geometric kernel, no view of
your model, and no way to check a fit. What it *is* good at is everything
upstream and downstream of the geometry:

| Ask it for this | Not this |
|---|---|
| A written design spec you then model from | "Generate the enclosure" |
| Kinematics: linkage lengths, servo throw → jaw angle | An assembly file |
| Print orientation, overhang, tolerance, and shrink advice | A sliced G-code file |
| A parametric script (build123d / CadQuery / OpenSCAD) | A parametric Fusion file |
| A review of a design you describe back to it | A review of a screenshot it half-reads |

You are fluent in CAD. The leverage is in the **spec** and the **mechanism math**,
not in it drawing boxes. So the deliverable you should ask for is a dimensioned
specification and a decisions log — something you can model from in an hour —
plus a parametric script only if you want a throwaway first body to check
proportions.

## The spec skeleton — fill this in, then hand it over

The reason CAD requests to an AI come back useless is almost always that one of
these seven is missing. Fill each one, in this order.

**1. Origin and datums.** Where is (0,0,0), which way is +Z, what face sits on
the desk. Every dimension afterwards references this. Say it explicitly or you
will get answers in three different coordinate frames.

**2. Envelope.** Outer footprint, total height, and the internal volume left
after wall thickness. State the wall thickness you intend and the material.

**3. Interfaces — the actual content.** For each, position, orientation, and
tolerance:
- PCB: outline, mounting hole coordinates and diameter, standoff height, which
  edge the USB-C connector exits and how much clearance it needs to the wall.
- Servos: pocket dimensions for the body, screw hole spacing, output shaft
  position and axis, and how much sweep the horn needs unobstructed.
- Speaker: diameter, depth, sealed or ported chamber, grille pattern and open
  area, standoff from the wall.
- Microphone: the port hole diameter and the gap between the PCB mic and the
  outer surface. This one has a right answer acoustically and a wrong one.
- Button: cap diameter, travel, panel thickness at that spot, how it retains.
- Cable routing from base to head, and strain relief at both ends.
- SD card and USB access without disassembly, or an explicit decision that you
  accept disassembly.

**4. Assembly strategy.** How it comes apart, how many pieces, what fastens to
what — heat-set inserts, self-tapping screws, snap fit, magnets. Say which, and
the hole diameters that go with it. Also say what has to be serviceable versus
what can be permanent.

**5. Print constraints.** Printer, nozzle, layer height, material, and the
orientation you intend for each part. Then the rules that follow: max unsupported
overhang angle, minimum feature size, whether supports are allowed, and which
surfaces are cosmetic. State your clearance convention explicitly — e.g. 0.2 mm
for sliding fits, 0.1 mm for press fits, holes drawn 0.2 mm oversize — because
otherwise you will get generic advice you already know.

**6. Aesthetic intent.** This is the part people leave out and it is the whole
project. Say it in plain language: he is a classic English butler at six inches — dry,
warm, formal. The base should read as a butler's stand, not a gadget. "A1-4RD"
is a visual pun that goes on the base as a nameplate. Screws should not be
visible from the front. Give the AI the reference and the feeling; it will push
back on details that fight it.

**7. What is already fixed.** The jaw is driven from a precomputed angle curve,
so it moves continuously through speech rather than snapping open and shut —
which means the linkage needs smooth travel over a modest range, not a binary
open/closed action. The head nods. The figure is six inches. Those are settled.

## The kinematics ask — do this one separately

The jaw is the only real mechanism, and it is worth a dedicated conversation.
Give the AI: the jaw pivot location, the desired open and closed jaw angles, the
servo's usable rotation, the servo mounting position, and the space available for
a linkage. Ask it for link lengths and attachment points that map servo angle to
jaw angle smoothly, plus the resulting non-linearity across the range so you can
compensate in software if it matters. That is a solvable geometry problem and it
will do it well. Ask it to "design the jaw" and it will write you a paragraph.

## Copy-paste prompt

---

I am designing the 3D-printed base for a six-inch desk companion figure called
A1-4RD ("Alfred") — a butler character, dry and formal, not
a consumer gadget. The base houses a Raspberry Pi Zero 2 W on a custom carrier
PCB, a speaker, a microphone, a button, and the wiring up to two servos in the
figure (jaw and neck nod). I am fluent in CAD and printing, so I do not need
modeling instruction — I need a rigorous specification and the mechanism math.

I will give you the parameters below. Your job:

1. Ask me for anything missing before you produce anything. Do not fill gaps with
   assumptions.
2. Produce a **dimensioned specification** I can model from directly: every
   feature located against a stated origin, with tolerances and the reasoning
   behind each number. Not prose descriptions of features — coordinates and
   dimensions.
3. Produce a **decisions log**: each choice, the alternative you rejected, and
   why. I want to be able to argue with your reasoning.
4. Flag every place where my constraints conflict with each other, and every
   place a decision depends on something I have not measured yet.
5. Where a number is acoustically or mechanically load-bearing — the mic port,
   the speaker chamber, the servo pocket fit — say so and give me the rule, not
   just the value.

Be blunt about problems. If something I have specified will not print, will not
fit, or will sound bad, say so plainly and give me the fix.

My parameters:

[paste the seven-section spec here]

---

## Sequencing note

Do the PCB architecture stage first. Its stage-4 mechanical interface sheet —
board outline, hole coordinates, connector positions, component keep-out heights
— is exactly the input section 3 of this spec needs. Designing the enclosure
around a board that has not settled means doing it twice.
