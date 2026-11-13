# A reproducible data-memory estimate

Run `python3 scripts/memory_budget.py` from the checkout. It counts the current geometry (36 nodes, 29 leaves, depth 4) and prints every assumption as JSON.

This estimates a proposed compact native implementation with one primitive projected at a time. It is not measured Python memory, a recovered historical layout, or proof that a complete executable fits BESM-4.

| Component | Native bytes | 45-bit words |
| --- | ---: | ---: |
| Four-leg state | 544 | 76 |
| Shared constants/body state | 128 | 16 |
| RK4 workspace | 224 | 28 |
| Phase workspace | 152 | 19 |
| Leg solver workspace | 192 | 24 |
| Geometry/topology | 3456 | 196 |
| Traversal stack | 432 | 56 |
| Projection/hull workspace | 512 | 64 |
| Packed 160 × 100 bitmap | 2000 | 356 |
| **Total** | **7640** | **835** |

Native counts assume float64 scalars, uint32 indices/tags, packed storage without alignment padding or heap headers. Workspace rows are explicit allowances, not measured peak allocations. The alternative historical column uses one 45-bit word per working scalar; it does not promise modern float64 precision. These columns describe different representations and must not be added together.

The [1974 paper, pp. 199–200](https://etudes.ru/etudes/cat-animation/) describes eleven node parameters packed into four words, a header word, and child lists with three 15-bit fields per word, including a count field. The estimator applies that packing to our estimated geometry. It does not quantize the running model. The bitmap resolution is our choice, not recovered printer resolution.

The [Russian Virtual Computer Museum](https://www.computer-museum.ru/histussr/29-2.htm) lists BESM-4 RAM as 4096–8192 words of 45 bits. Our 835-word data estimate is about 20% of 4096 words, but excludes executable instructions, math-library code and internal scratch, system/I/O buffers and any uncounted implementation overhead. The original program's exact footprint is unknown.

Python, Pillow and browser objects, stored frame histories and diagnostics are excluded. Our actual Pillow occupancy image alone uses 16,000 bytes; a 960 × 600 RGB frame uses 1,728,000 bytes. The current renderer also materializes projected geometry. The [streaming runner](reconstruction/minimal.py) avoids retaining the movie, but it still uses those modern facilities.

## The implemented C port

The estimate above remains a hypothetical packed layout. The new [native implementation](native/README.md) has measured storage and compiler stack reports in [this platform-specific record](research/native-memory-macos-arm64.json). It stores full rotations and both model presets, so it is larger than the hypothetical layout. The report separates read-only constants, mutable state, stack bounds and executable sections, and excludes library/system overhead.
