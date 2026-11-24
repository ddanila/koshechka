# Compact C animation pipeline

This C99 implementation advances four legs, solves the constrained joints, transforms tapered solids, projects one primitive at a time, fills a packed bitmap, and streams monochrome Ш frames. It allocates no application heap memory and stores no movie history. It uses the same reconstructed algorithm, not mainframe emulation.

```sh
make -C native
native/build/kitty | ffmpeg -f image2pipe -framerate 24 -i - -pix_fmt yuv420p kitty.mp4
native/build/kitty --preset baseline --trace > trajectory.csv
native/build/kitty --events > events.csv
native/build/kitty --help
.venv/bin/python scripts/native_presets.py --check
.venv/bin/python scripts/check_native.py
.venv/bin/python scripts/native_memory.py
```

Default output is concatenated binary PBM images, 960×600, using a 160×100 occupancy bitmap and a 120-byte output row. `--ink` reverses which region carries Ш. `--mask` emits the raw 160×100 occupancy mask; in that diagnostic encoding, set occupancy is a black PBM pixel. `--vertices` emits transformed solid vertices. `--trace` and `--events` are separate CSV modes. Events use integer IDs: 1 rear reversal, 2 front reversal, 3 touchdown; leg order is right rear, right front, left rear, left front. Viewer lift-off observations are an exporter diagnostic, not an additional controller event.

Options include duration, frame rate, step size, camera angle, tracking/fixed camera, continuous walking, coupling and head turn. Both `baseline` and the default `fitted` preset are compiled from canonical Python models. The generated-header check compares structure exactly and floating constants within 1e-12 to accommodate platform libm rounding. Custom JSON and the experimental literal mode remain Python-only. Inference choices and numerical repairs are shared with Python.

## Validation

Normal builds disable floating-point contraction and fast-math. GCC and Clang builds are checked against Python for both presets in default, cruise and uncoupled scenarios. Branch/event sequence must match; allowed errors are 1e-9 for state/coefficient values, 1e-8 for vertices, and one integration step for event times. The recorded macOS runs have maximum state errors below 2e-13, vertex errors below 8e-13 and identical event times. [Recorded results](../research/native-parity-macos-arm64.json).

The rasterizer includes pixel centers on or inside the projected convex hull. Pillow uses a different integer scan conversion. Tests allow differences only within one cell of a primitive edge; the recorded maximum is 175/16,000 cells for baseline and 166 for fitted. This is not pixel identity. Address/undefined-behavior sanitizer builds run the same checks.

## Measured storage

The [Clang arm64 report](../research/native-memory-macos-arm64.json) records 544 bytes for four legs, 5,760 bytes for mutable nodes, 2,000 bytes for the occupancy bitmap, and a 120-byte output row. Two compiled model snapshots occupy another 11,520 bytes of constants. A conservative sum of application stack frames, counting the sole recursive traversal at depth four, is 11,888 bytes; this already includes the leg/node arrays. The executable file is 51,912 bytes on that build, including platform metadata; sizes vary with compiler and platform.

The geometry stores full double-precision rotations rather than the paper's packed angles. This is deliberately simple and inspectable, not an optimized historical footprint. libc/libm, loader, I/O buffering and system memory are excluded from application accounting. See the separate [45-bit memory estimate](../MEMORY-BUDGET.md); neither modern executable size nor Python RSS demonstrates BESM-4 fit.
