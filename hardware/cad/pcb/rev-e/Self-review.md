# Revision E closure and open validation

The unverified32.1k R107 purchasing MPN is fixed with catalogue32.0k RT0805BRD0732KL. Schematic, PCB, BOM, calculations and drawings are synchronized. The incomplete external BOM now includes missing essentials.

Power mitigation changes R101 and C101: about2.02A Pi/audio overcurrent threshold and about25.5ms nominal startup. A constrained1.65A Pi/audio plus0.80A servo target replaces the unsupported4.1A allocation. Lower startup demand and a smaller operating load increase calculated margin without adding placements. This reduces capability; it is not an equivalent4.1A redesign.

The full power-margin issue is not physically closed. Power-acceptance.md defines measurable requirements and includes maximum eFuse resistance, initial/temperature resistor tolerances, an explicitly assumed MOSFET hot factor and PCB loss. Validate the real supply, thermal conditions, startup and transients before relying on the jaw or Pi. The remaining tests cannot be performed against CAD files. Source checks did not justify adding a replacement input MOSFET as an unvalidated drop-in.

Purchasing, supplier baskets and orders are deferred. No claim is made that every remaining MPN is stocked. Clean DRC/ERC and a logic truth table do not prove power, audio, RF or mechanical behavior.
