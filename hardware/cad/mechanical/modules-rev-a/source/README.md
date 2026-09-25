# Regenerating the geometry

Install requirements.txt into a separate Python environment, then run build_module_cad.py. It uses the source STEP geometry and saved manufacturer PCB snapshots and regenerates this package's CAD, assembly, placement and clearance outputs. Back up manual changes first. New geometry is parameterized in the script; imported original parts remain STEP solids.

Manufacturer board files and attribution/license texts are retained under board-sources. Original Adafruit board designs are credited to Adafruit Industries and their respective designers; see each supplied README and license. New enclosure changes were made for the Alfred project. Reference blocks are simplified fit envelopes, not manufacturer-certified component models.
