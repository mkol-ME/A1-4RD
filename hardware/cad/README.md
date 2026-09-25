# Alfred CAD archive

These are the complete generated CAD deliverable folders for the Alfred physical prototype. Each revision is kept intact so its own README, checks, source files, and exports stay together. They are **design snapshots**, not proof of a built or qualified device.

| Folder | Contents | Status |
| --- | --- | --- |
| `mechanical/rev-a/` | Initial bust and enclosure; STEP, STL | Superseded by rev B |
| `mechanical/rev-b/` | Revised bust, jaw, enclosure; STEP, STL | Latest exterior baseline |
| `mechanical/module-fit-review/` | Fit review and next steps | Reference notes |
| `mechanical/modules-rev-a/` | Revised tray and fit models for off-the-shelf Pi/audio/power modules; STEP, STL, CadQuery source | Latest module-based prototype geometry; use with the rev B exterior parts named in its README |
| `pcb/rev-c/` | KiCad carrier project and fabrication exports | Superseded by rev D |
| `pcb/rev-d/` | KiCad carrier project and fabrication exports | Superseded by rev E |
| `pcb/rev-e/` | KiCad carrier project and fabrication exports | Latest custom-PCB candidate; unbuilt and purchasing deferred |

## Starting points

- For the printed body and currently proposed breakout-module prototype, start with `mechanical/rev-b/README.md` and `mechanical/modules-rev-a/README.md`.
- For the custom PCB design, start with `pcb/rev-e/README.md` and its power-acceptance and validation notes. Do not send its Gerbers for fabrication without the remaining physical checks.
- The repository's `hardware/v1-electronics-bom.pdf` is a separate early bench-shopping list. It is not a purchasing BOM for the module package or PCB rev E.

Large STEP and STL files are stored with Git LFS. The native SolidWorks files are kept offline; the STEP exports open in SolidWorks. Clone with Git LFS enabled to receive the actual models rather than pointer files.
