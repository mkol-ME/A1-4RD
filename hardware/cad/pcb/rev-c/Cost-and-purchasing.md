# Price optimization for one Alfred

**The purchase list is leaner, but the improved circuit itself is slightly more expensive.** No order was placed and this is not a complete current-price quotation.

| Comparison | USD allowance |
|---|---:|
| Revision B fitted board components | 40.62 |
| Revision B recommended purchase quantities | 60.80 |
| Revision C lean purchase, fitted board components | 43.06 |
| Reduction versus previous recommended purchase basket | 17.74 |
| External parts, PCB and hardware inherited allowances | 55.35 |
| Revision C combined planning allowance, excluding Pi | 98.41 |

These comparisons use the old component allowances except the newly selected MOSFET ($1.76 each) and clamp diode ($0.17). They mix estimates and two checked indexed price entries; they are not a claim of checkout savings. Shipping, tax, assembly labor, stencil, minimum PCB order quantities and enclosure printing are additional. A fabricator's minimum batch charge can exceed the inherited $20 PCB allowance.

## Changes made

- Purchase one each of the large electrolytics and other single-use expensive parts for one board, rather than the earlier automatic five-piece quantities. This is where most of the apparent basket reduction comes from.
- Use the fitted quantities in `BOM-grouped.csv`. A separate optional-spares column adds small inexpensive resistor/capacitor spares; it does not automatically add expensive capacitors or ICs. For professional assembly, use the assembler's required attrition allowance instead.
- R304 is **do not fit**, saving one placement while selecting 9 dB amplifier gain. Its optional 100k part number is already shared by other fitted resistors, so do not remove that entire MPN from the purchase order.
- R2 now shares the existing 100k resistor value; R114/R115 share the existing 10k value.
- FDS6673BZ was selected for guaranteed low-voltage gate operation and sourcing. It costs more than the old AO4407A allowance. The AO4409 candidate was rejected after the distributor identified it as obsolete.
- MMSZ5V1T1G uses the existing SOD-123 footprint family. The initially considered Diodes part was out of stock.

Keep the four-layer board, 35 um copper on all layers, the two eFuses, reservoir capacitors and servo energy dump. Their removal would need new electrical and thermal validation. ENIG remains the preferred finish for the fine-pitch parts. The mechanical footprint and connectors remain compatible with the existing Alfred enclosure plan.

## Ordering

Consolidate the electronics purchase with one authorized distributor when shipping/setup savings outweigh small unit-price differences. Use cut tape for a single build; avoid custom reeling fees. Hand-solder the THT socket, connectors, electrolytics, LED and button after reflow, or obtain a separate quote for that work. Compare total assembled-board quotes, not just bare-board prices.

Specify **onsemi FDS6673BZ**, not a marketplace part carrying a similar AO number. The microphone remains the previously selected EOL ICS-43434; obtain genuine stock before ordering boards. It was retained to preserve the existing footprint and acoustic port, not selected as a new long-life production component.

Source checks, 2026-09-10: [FDS6673BZ availability and price in distributor substitute table](https://www.digikey.com/en/products/detail/alpha-omega-semiconductor-inc/AO4409/1855795), [MMSZ5V1T1G availability and price in distributor substitute table](https://www.digikey.com/en/products/detail/diodes-incorporated/BZT52C5V1-7-F/717736). Recheck the final cart; stock is not reserved.
