# Selected mathematical claims checked by Lean

This project pins Lean 4.19.0 and the matching Mathlib revision in its toolchain and dependency manifest. With [elan installed](https://lean-lang.org/install/manual/):

```sh
cd formal
lake exe cache get
lake build
cd ..
python scripts/check_formal.py
```

On a newer macOS where the old cache executable cannot launch, use `lake env lean --run .lake/packages/mathlib/Cache/Main.lean get` from this directory. The proof checker itself runs normally.

[The proofs](Koshechka.lean) establish:

- `landing_initial`: the cubic starts at the specified height and vertical velocity.
- `landing_derivative`: the velocity expression is the actual derivative of that cubic.
- `landing_final`: for positive duration it ends at zero height and velocity.
- `chord_linear` and `cross_linear`: squared unit-circle chord distance reduces to the resultant's dot product with the cross direction.
- `resultant_minimum` and `normalized_attains`: the normalized nonzero resultant attains the global minimum.
- `degenerate_cross`: a zero resultant gives the same reduced cost for every direction.
- `phase_unit`: sine/cosine phase points satisfy the required unit-circle hypothesis.

These correspond to coefficient group II and `phase_fit` in [the Python controller](../reconstruction/kitty/core.py). The cross proof assumes fixed leg assignment; rotating each phase by its offset makes the target a common unit vector. The actual `atan2`, floating-point rounding, near-zero fallback, RK4, branch events, geometry and historical fidelity are **not** formally verified.

The audit rejects unfinished proofs and project-defined axioms. Printed dependencies are only Lean's standard `propext`, `Classical.choice` and `Quot.sound`; no `sorryAx` is accepted. Lean/Mathlib are development dependencies, not animation runtime dependencies.
