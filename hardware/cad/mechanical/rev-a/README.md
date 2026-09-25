# A1-4RD / Alfred — printable prototype, revision A

STEP parts and a reference assembly, plus millimetre STL exports. The native SolidWorks files are kept offline.
Designed from alfred.jpg and the routed carrier PCB mechanical interface from the earlier task.
The face has solid eyeballs, iris relief, pupils, half-lowered lids, eyebrows, a long nose, ears and a moustache. The chin is a separate moving part. This is a stylized CAD interpretation of the reference, not a scanned likeness.

## Scale and coordinates

Overall nominal height 202 mm (7.95 inches), including base. Plinth footprint 137 x 111.6 mm, with a small additional projection at the front lettering. Main base wall 3 mm. Internal chamber 127 x 101.6 x 50.8 mm, measured above the floor at global Z=3 mm. Global X goes right, Y goes back, Z goes up. Internal front-left floor corner is (0,0,3).

Carrier PCB 120 x 94 x 1.6 mm. PCB front-left XY=(3.5,3.8). Underside Z=9, top Z=10.6. Four M3 pilot supports at (7.5,7.8), (119.5,7.8), (7.5,93.8), (119.5,93.8). Pi support hardware remains M2.5 and mounts on the PCB, not the enclosure floor.

The PCB, Pi, commercial servo, servo horn, speaker and fasteners are NOT included as detailed component models. Purchased-part compatibility is based on the preceding PCB interface and listed nominal dimensions. Measure the actual header stack, switch, servo shaft location and speaker before the final print.

## Files and parts

| Part | Material | Assembly / print note |
|---|---|---|
| 01_Plinth | Bronze PLA | Speaker front, USB/SD rear; print top face on bed, cavity upward, inspect supports around grille |
| 02_Bottom_cover | PETG | PCB supports; print floor on bed |
| 03_Speaker_mount | PETG | Padded 72 x 19 x 32 mm pocket; bond to inner front wall at model position; no supports through PCB |
| 04_Speaker_lid | PETG | Removable roof; retain with removable tape or a light strap |
| 05_Microphone_duct | PETG | Print open channel upward, clean bore, bond to bottom cover |
| 06_Microphone_duct_lid | PETG | 0.5 mm roof; use 0.1 mm layers; 0.2 mm thin gasket seat around PCB mic bore |
| 07_Button_stem | PETG | Insert from underneath BEFORE bonding cap |
| 08_Torso | Bronze PLA | Hollow wiring space, jacket and bow tie; support as needed; M3 attachment from inside plinth |
| 09_Alfred_head | Bronze PLA | Solid eyes and face; rear service opening; print with supports kept away from eye details where possible |
| 10_Moving_jaw | Bronze PLA or PETG | Separate chin, axle cheeks and rearward drive arm; ream bores |
| 11_Name_plaque | Bronze PLA | A1-4RD lettering raised 0.8 mm; place flat back on bed; bond to front |
| 12_Servo_cradle | PETG | Strap mounting with an M2 base screw; confirm actual FS90 body/shaft position |
| 13_Drive_link | PETG | Print flat; 35.114 mm pivot-center distance; M2 clearances |
| 14_Rear_cover | Bronze PLA | Removable prototype cover; retain with narrow removable tape around rear seam |
| 15_Fit_coupon | PETG | First print: servo body sample and 3.2 mm bores |
| 16_Button_cap | Bronze PLA | Bond onto installed stem; keep glue out of guide |

Use one of each. Assembly contains the 15 installed printed components; the coupon is separate. The assembly is a fixed positional reference, not a mated motion simulation. The linkage is positioned at the closed-jaw reference.

All part files share assembly coordinates. In Bambu Studio import individual STLs as separate objects and use Lay on Face / Drop to Bed; do not print their floating assembly Z coordinates. No printer-specific G-code is supplied.

## Jaw mechanism

Use a 3 mm metal axle, approximately 50 mm long, trimmed to the actual head width and retained at both ends. Printed main axle bores are 3.2 mm in the head and 3.3 mm in the jaw. Ream to a free-running fit; do not force a screw thread through a bearing surface.

Reference jaw pivot: (Y,Z)=(52,143). The jaw drive point is 10 mm behind the pivot, at (62,143) when closed. Reference servo shaft: (58,176), axis parallel to X. Use an 8 mm horn radius and the 35.114 mm link. The rod occupies X=79.5..81.9. Use M2 screws, washers/spacers and locknuts to maintain free pivots. Keep the supplied servo spline/horn; no printed spline is provided.

| Jaw opening | Reference crank angle |
|---:|---:|
| 0 degrees | 180.000 degrees |
| 5 | 173.513 |
| 10 | 166.483 |
| 15 | 158.776 |
| 20 | 150.181 |

These are geometric angles in the YZ plane, NOT servo PWM commands. Calibrate the horn's center and actual shaft position before connecting the linkage. The bracket allows strap mounting rather than relying on unverified tab holes. If the purchased shaft cannot be placed at the reference coordinate, modify the bracket/link before operation. Start with a small travel range and limit normal operation to 0..20 degrees. Do not drive the servo into a stop.

The final head/torso include a BRep clearance feature calculated from sampled jaw positions and a 2% enlargement of the jaw around its pivot. Earlier sketches/features remain in the native file, but this final clearance body does not automatically regenerate from upstream changes: recalculate it after changing jaw geometry or pivot placement.

## Hardware and fit

- Four M3 screws for the PCB, four M3 screws through the bottom cover, and two M3 screws from inside the base into the torso. Pilot holes are 2.6 mm; verify self-tapping fit on scrap. Select lengths to avoid bottoming or piercing the shell; PCB screws typically M3 x 6 with insulating washers, cover M3 x 8, torso M3 x 8 subject to washer thickness.
- Head has a 20 mm spigot and torso a 20.6 mm socket. Lightly bond after wiring/fit confirmation; rear cover permits servo access.
- Servo cradle uses an M2 screw into a 1.7 mm pilot, with a recessed head, and narrow cable ties through the rail slots.
- Speaker: Adafruit 4445 nominal 70 x 31 x 17 mm enclosed body, padded with thin foam. Mounting is by cradle, not its unverified screw pattern. Keep factory enclosure intact.
- The microphone duct must be sealed to the PCB underside around its 0.5 mm acoustic bore. Use a thin compressible gasket; keep adhesive, dust and filament out of the acoustic path.
- Button stem is based on a nominal 4.3 mm switch height above PCB top: 0.2 mm initial clearance and about 0.45 mm cap travel. Verify the actual B3F-1000 actuator height/travel and adjust stem length before bonding cap.
- Keep the Pi antenna area free of metal hardware and cable bundles. Provide a service loop in the neck.
- Rear USB opening: global X 23.5..43.5, Z 6.5..18.5. SD access: X 81.5..115.5, Z 19.5..31. Allow cable and card withdrawal space behind the figure.

## Bambu P1 print starting point

Use a 0.4 mm nozzle. Start with the appropriate Generic PLA / Generic PETG profile, then tune to the filament manufacturer. Decorative head and jaw: 0.12–0.16 mm layers; base/torso: 0.20 mm; 4 walls and 15–20% infill as a starting point. Mechanism: 4–5 walls; link 100% infill. Slow outer walls for the face and lettering. Inspect support contact and bore cleanup in the slicer. The thin microphone lid should be printed separately at 0.1 mm layers.

Bronze PLA is appropriate for the cosmetic shell; PETG is preferred for internal supports. Validate enclosure temperature with the real electronics running before long unattended use. ABS is unnecessary for this first prototype.

## Filament sourcing — checked 6 September 2026

1. [Polymaker Panchroma Metallic Bronze PLA, 1.75 mm, 1 kg](https://shop.polymaker.com/products/metallic-pla?variant=43595097407545): $24.99, selected Bronze variant available when checked. Manufacturer calls for at least a 0.4 mm nozzle, 190–230 C nozzle and 25–60 C bed. Bronze appearance comes from a decorative metallic effect; no plating needed.
2. [Polymaker PETG, Black / New Formula, 1.75 mm, 1 kg](https://shop.polymaker.com/products/petg?variant=45079221108793): $18.99, selected variant available when checked.

Two-spool subtotal $43.98 before tax/shipping; no purchase has been made. One bronze spool and one PETG spool are a practical starting purchase including test prints. If you already have PETG, buy only bronze. Availability can change.

Material references: [Polymaker metallic PLA](https://shop.polymaker.com/products/metallic-pla), [Prusa PETG guide](https://help.prusa3d.com/article/petg_2059), [FS90 specifications](https://www.pololu.com/product/2818/specs).

## Release status

This is an unbuilt prototype. Geometric checks cover the modeled printed parts; they do not establish purchased hardware fit, print tolerance, acoustic performance, motor calibration or thermal performance. See the validation JSON files for exact checks performed. Print the coupon and mechanism first, then the cosmetic pieces.


## Reinforced head and assembly guide

The final head has connected 4 mm side rails, upper/lower crossmembers, reinforced axle bearings and a thicker rear neck root. Use six walls on the head. See Alfred-assembly-guide.pdf for the exploded schematic, linkage dimensions and numbered assembly instructions.

Validation: all 16 STL meshes checked for watertightness, winding and connected components (mesh-validation.json); all native part bodies passed kernel checks. No static printed-part interferences were detected. Jaw/link motion was sampled at each integer degree from 0 through 20 against the modeled head, torso, cradle and rear cover; no collisions were detected at those samples. Purchased components were not included in that clearance check.
