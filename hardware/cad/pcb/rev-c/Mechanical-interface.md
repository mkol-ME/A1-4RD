# Alfred mechanical interface — millimetres, revision C

This defines a proposed carrier/enclosure interface within the confirmed **127 × 101.6 × 50.8 mm internal housing volume**. These are design coordinates, not measurements of an existing printed shell. Use the supplied DXF for board outline/holes and CSVs for coordinates. Purchase-part fit and the header mating height require a physical fit check before freezing the enclosure.

## Coordinate system and outline

Plan view looks down onto carrier components. **PCB origin is its front-left corner; X goes right, Y goes toward the back.** Z in this document is measured upward from the internal housing floor. The front/back edges are the long edges.

| Item | Dimensions / location |
|---|---|
| Internal housing | X 0–127, Y 0–101.6, Z 0–50.8 |
| Carrier outline, PCB coordinates | (0,0), (120,0), (120,94), (0,94); square corners |
| Carrier location in housing | Housing X = PCB X + 3.5; housing Y = PCB Y + 3.8 |
| Carrier underside / top | Z = 6.0 / 7.6; nominal 1.6 mm board |
| Carrier envelope tolerance | Outline ±0.2 mm, drill positions ±0.1 mm requested; confirm fab capability |
| Bottom parts | None; reserve underside Z 3.0–6.0 for trimmed through-hole leads |
| Carrier standoffs | Four M3 supports, floor to PCB underside = 6.0 mm; boss outside diameter ≤7.0 mm |

## Mounting holes

All holes are non-plated. Keep copper and components outside a 7.0 mm diameter at M3 holes and 6.0 mm diameter at Pi mounting holes; maintain electrical clearance to metal hardware. Use insulating washers where necessary.

| Ref | PCB X | PCB Y | Drill | Hardware |
|---|---:|---:|---:|---|
| H1 | 4.0 | 4.0 | 3.2 | M3 carrier |
| H2 | 116.0 | 4.0 | 3.2 | M3 carrier |
| H3 | 4.0 | 90.0 | 3.2 | M3 carrier |
| H4 | 116.0 | 90.0 | 3.2 | M3 carrier |
| H5 | 83.5 | 90.5 | 2.7 | M2.5 Pi support |
| H6 | 106.5 | 90.5 | 2.7 | M2.5 Pi support |
| H7 | 83.5 | 32.5 | 2.7 | M2.5 Pi support |
| H8 | 106.5 | 32.5 | 2.7 | M2.5 Pi support |

The Pi has factory holes on a 58 × 23 mm rectangle, 3.5 mm from its 65 × 30 mm outline edges. **Use M2.5 on the Pi; do not enlarge its holes for M3.** Use nylon Pi screws and supports, particularly at H8 inside the antenna exclusion region; do not put a brass spacer there. See the [official Pi drawing](https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-mechanical-drawing.pdf).

## Pi orientation and connector stack

The Pi body occupies PCB X **80–110**, Y **29–94**, with its SD end toward Y=94. The carrier socket is on the carrier top; a straight male header is soldered to the Pi underside. The Pi component side faces upward. Socket physical pin 1 is at **(84.77,85.63)** and pin 2 at **(82.23,85.63)**. For each succeeding pair, subtract 2.54 mm from Y; pin 39 is (84.77,37.37), pin 40 (82.23,37.37). Confirm pin-1 orientation on a 1:1 print before mating.

Use Samtec SSW-120-01-G-D socket with TSW-120-07-G-D male header. Nominal body-height sum 8.51 + 2.54 = **11.05 mm** between carrier top and Pi underside when fully seated. Set supports to the **measured assembled gap**, nominal 11.05 mm; use 11 mm spacers plus thin shims if needed. Do not pull the Pi down against an incorrect spacer height. Pi underside is nominal Z=18.65. Reserve **Z 18.65–28.0** for Pi PCB, components and SD handling.

The official outline drawing does not dimension the SD socket aperture. Therefore the proposed enclosure uses a generous **service window**, not an unverified close-fitting SD slot: housing X **81.5–115.5**, Z **16.5–28.0** at the back wall. Provide at least **20 mm of unobstructed external withdrawal space** and a removable cover or finger notch. Keep the tunnel clear from the Pi's rear edge (housing Y=97.8) to the exterior. Mounting screws must remain accessible after removing the cover.

Reserve PCB X **96–114**, Y **25–44** for the Pi antenna: no carrier copper on any layer, no tall components, and no metal brackets, cable bundles or speaker magnet in that volume. This is a conservative proposed region around the antenna end; verify alignment against the actual Pi revision.

## Connectors and controls

Rotations below are KiCad rotations in the routed board. The physical PCB coordinate mapping above is authoritative. CAD point (X,Y) maps to KiCad editor point (50+X,144−Y) mm.

| Item | PCB footprint origin | Orientation / clearance |
|---|---|---|
| J1 USB-C | (30.0,90.8), 180° | Mouth toward back, approximately at Y=94; reserve PCB X 24–36, Y 84–94 |
| J2 Pi socket pin 1 | (84.77,85.63), 0° | Long axis toward front; pin 2 is 2.54 mm left |
| J3 speaker terminal pin 1 | (57.0,28.0), 0° | Wire entry toward front; pitch 2.54 mm; 8 mm clear above screws and 10 mm free wire space in front |
| J4 servo pin 1 | (15.0,53.0), 90° | Header runs along X; reserve X 10–25, Y 48–58, up to Z=30 for plug/wire bend |
| SW1 origin | (105.0,12.0), 0° | Button actuator center = (108.25,9.75); vertical plunger from enclosure, not a sideways load |
| D3 LED pin 1 | (99.5,8.0), 0° | LED optical axis approximately (100.77,8.0); printed light pipe centered there |
| U6 microphone package center | (10.0,8.71), 0° | PCB acoustic hole center = (10.0,8.0), diameter 0.50 mm NPTH |

For USB, use a deliberately generous rear service opening: housing X **23.5–43.5**, Z **3.5–15.5**, with a clear 20 × 12 mm tunnel extending from housing Y=94 to the outer wall. The receptacle is recessed 3.8 mm from the internal rear boundary. The opening must admit the **plug overmold**, not just its metal tongue. Keep 30 mm of external straight cable space before bending. Wall thickness is an enclosure input, so the tunnel extends through whatever wall thickness you choose; its clear section stays 20 × 12 mm throughout.

J3 is internal; there is no need for an enclosure connector opening. Secure the speaker cable so pulling the shell does not load the terminal block. J4 is also internal; provide a retention clip and a service loop rather than letting its plug carry mechanical loads.

The B3F-1000 is a four-leg, two-net switch. The standard footprint origin is not the actuator center; the coordinates above include that offset. Leave about 0.2 mm plunger rest clearance and incorporate a travel stop; verify purchased actuator height and travel before printing the final plunger. The LED body can be raised on its leads to meet a light pipe; lead forming must preserve the height zone.

## Speaker, microphone port and height zones

The selected speaker body is approximately 70 × 31 × 17 mm. Stand it upright with the 70 mm dimension across the front, its 31 mm dimension vertical, and its 17 mm depth toward the back. Proposed body envelope in PCB X/Y and housing Z is **X 25–95, Y −3.8–13.2, Z 12–43**. This puts its face at the internal front boundary. Use a padded printed cradle with a **71 × 32 × 18 mm cavity**, centered on the nominal body, and a removable retaining strap. Do not rely on the supplier's ambiguous mounting-hole spacing. Keep at least 1 mm in front of the diaphragm/grille and preserve its factory rear enclosure.

The microphone is separated to the left of the speaker. Seal a **3 mm diameter annular gasket seat** around its underside acoustic hole. Provide a printed acoustic passage from housing **(13.5,11.8,Z=6.0)** to a **2 mm diameter front opening at housing X=13.5, Z=5.0**. Use a channel at least 1.5 mm clear diameter, avoid sharp steps/dead cavities, and keep its path separate from the speaker cavity. The gasket seals to the PCB underside; it must not plug the 0.5 mm bore. Reserve PCB X 7–13, Y 5–11 for the port/gasket and no copper near the bore. This duct's acoustic effect must be measured; dimensions are a mechanical starting point, not a calibrated microphone response.

| Zone, PCB X/Y | Maximum height above carrier top | Purpose |
|---|---:|---|
| X 22–98, Y 0–18 | 3.0 mm | Clearance below speaker cradle; no electrolytics/inductors here |
| X 80–110, Y 29–94, excluding socket/supports | 6.0 mm | Components below Pi; preserve 11.05 mm mating gap and Pi underside clearances |
| X 96–114, Y 25–44 | 0 mm carrier components | Antenna region, all copper excluded |
| X 25–78, Y 55–86 | 28.0 mm | Tall power capacitors; C105 seated height can reach 27 mm |
| X 25–65, Y 38–54 | 15.0 mm | Raised dump resistor; keep plastic and wire insulation at least 5 mm away |
| X 10–25, Y 48–58 | 22.4 mm including cable | Servo plug/bend volume, absolute top Z=30 |
| X 10?23, Y 59?69 | 18.0 mm | C106 servo bulk capacitor; seated height up to 17 mm |
| Remaining carrier area | 12.0 mm | General circuitry; individually respect connector/control exceptions |

Maximum planned speaker top is Z=43, leaving 7.8 mm below the internal ceiling. Tall capacitor top is at most Z=35.6. The Pi service volume stops at Z=28. These allowances fit the 50.8 mm housing height without using it as a component-height entitlement everywhere.

The jaw servo belongs in the moving-head mechanism and is not assigned a base PCB mounting location. Its approximate 23.2 × 12.5 × 22 mm body and mounting tabs must be integrated against its purchased drawing. Final linkage geometry, cable exit toward the head and shell-wall thickness are the remaining enclosure-specific inputs; they do not change this carrier outline.

## Routed-board changes

All electrical parts are placed inside the outline. D3 moved 0.5 mm left to clear the button body; its optical axis is now PCB (100.77,8.0). The resistor and servo capacitor height zones above supersede revision A. `Placement-coordinates.csv` contains every footprint origin and rotation from the final PCB. The two-layer signal routing and four-layer copper stack are described in `Fabrication-and-assembly.md`.

The STEP file is the bare carrier, without component models. The dimension tables define enclosure placement; the 3D preview contains generic or missing component models and does not represent the installed Pi or speaker.

Revision C retains all fixed mechanical coordinates. The three small protection parts occupy existing low-height circuitry space; the connector stack and enclosure dimensions are unchanged.
