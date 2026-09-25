# Revision D closure review

Revision C's review identified an insufficient nominal servo-enable margin and the lack of hardware protection against repeated restarts. Revision D changes the circuit and PCB to address both.

The input pair now has a specified 16.4 milliohm total maximum at -4.5 V/25 C, versus 24 milliohms previously. TPS389001DSET replaces the old comparator/reference/feedback network. A Nexperia 74AUP1G74DC latch asynchronously clears on detected undervoltage and cannot re-arm from voltage recovery alone.

Nominal cutoff/recovery thresholds are 4.8415/4.8710 V. Conservative static bounds are 4.783-4.901 V falling and 4.812-4.930 V rising. `Design-notes.md` documents calculations and the limited additional loss allowance at maximum load. Neither clean CAD checks nor the logic model prove that a built board maintains 4.75 V at the Pi pins through every transient.

Also corrected: manufacturing job dimensions use outline centerlines; R304 has no stencil apertures; changed component pin mapping was checked against manufacturer data; a slower-edge-tolerant AUP latch and 2.2k reset pullup replace the initial LVC candidate; a power flag declares externally supplied common ground for ERC.

Validation includes final DRC/ERC, schematic-pad comparison, a 65,536-sequence truth-table latch model, manufacturing exports and drawing inspection. Physical startup, transient response, fault-injection behavior, thermal/acoustic performance and target audio software remain prototype acceptance tests. No analog simulation or physical board test was performed. Sources and price assumptions are linked from the design and purchasing notes.
