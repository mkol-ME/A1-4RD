# Alfred carrier - revision E

Native KiCad 10 project for Pi Zero 2 W, ICS-43434 microphone, MAX98357A amplifier and one FS90 servo. Revision E replaces D for the next prototype evaluation. Purchasing is deferred.

- R107: verified 32.0k 0.1% part, with recalculated supervisor thresholds.
- R101: Pi/audio current limit lowered from about3.33A to2.02A nominal.
- C101:10nF; slower Pi/audio startup reduces nominal reservoir charging surge from0.94A to0.44A.
- External requirements now include the Pi, microSD, stencil/assembly and enclosure/linkage.

The supported design target is <=1.65A Pi/audio and <=0.80A servo; the earlier4.1A operating allocation is withdrawn. This is a deliberate reduction in supported load, not proof that all power-margin concerns are resolved. Read Power-acceptance.md. It includes source-voltage/path-loss criteria and tests that still require built hardware. The hardware latch still prevents restart after a detected fault until a deliberate new command edge.

Open Alfred.kicad_pro. Use the current BOM, Gerbers, assembly instructions and drawings together. Validation.txt records the completed CAD and offline checks. No physical board or target audio software has been tested; prototype power qualification is still open. Do not describe this release as production-qualified.
