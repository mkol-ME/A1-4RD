# Validation record

This record applies to the module prototype files in this directory, not the earlier custom PCB releases.

- All 18 printable STL files reopened with trimesh: watertight, consistent winding, positive volume.
- Exact BRep intersection tests found no volumetric intersections between the printed assembly and the included board/component/service envelopes, or between different module groups. Refer to clearance-check.json for the actual report.
- The same checks include the four base tray screw-head envelopes, the microphone solder-tail clearance, the servo-board reservoir capacitor and the USB-C plug envelope. Touching assembly interfaces (e.g. board seats and speaker floor) are intentional.
- New/revised STEP solids and the assembly were independently reimported. STEP-reimport-check.json records kernel validity and solid counts.
- The CAD runtime exits with code 1 without a Python traceback, even for a minimal import-and-version-print command. Export completion alone was therefore not treated as success: files were reopened and explicit geometry checks written separately. The runtime exit issue remains an environment limitation.
- Mesh checks do not establish print tolerances or strength. Board planar outlines/mounting holes come from manufacturer source files; tall components and connectors are simplified clearance envelopes, not certified supplier models. M2 fastener dimensions must be checked against the selected screws and washers; not all fasteners are individually modeled.
- The actual servo and horn are not modeled. The original cradle dimensions require a real fit check and possibly a revision; this package does not approve it. Previously supplied 0–20 degree jaw-motion results only concerned printed components.
- No physical power, thermal, audio, Wi-Fi, Pi boot, OS-driver or servo calibration tests were performed. The included overlay remains uncompiled on this Windows host.
- No purchasing or manufacturing action was performed. Basic module fuses/OE do not replicate the custom PCB's active fault protection.

Use the fit coupon and supervised bench sequence before final cosmetic printing.
