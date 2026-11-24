# The phase cross: interpretation and experiment

The original scan of printed p.209 explicitly asks for a perpendicular cross minimizing the sum of squared distances to the four phase points; figure 21 labels the legs around that cross. The [source](https://etudes.ru/.data/localdocs/koshechka.djvu) supports ordinary Euclidean chord distance with prescribed leg order. It does not prescribe our numerical fallback near a zero resultant or exact angle-wrapping implementation.

Let the four offsets be oᵢ = −iπ/2 and adjusted angles aᵢ = φᵢ−oᵢ. For a cross rotation θ, squared chord distance gives

`J(θ) = Σ [2 − 2 cos(aᵢ−θ)] = 8 − 2(C cos θ + S sin θ)`,

where `C = Σ cos aᵢ` and `S = Σ sin aᵢ`. For nonzero resultant, `θ = atan2(S,C)` minimizes this objective. At exactly zero resultant every orientation has the same cost. Our threshold `1e-12` and first-leg fallback are numerical choices. Signed errors wrap to [−π,π]; only swing branch 3 uses them.

[Lean proofs](formal/README.md) verify the real-number objective reduction and minimizing direction, including degeneracy. They do not prove our floating-point `atan2` implementation or its near-zero threshold correct.

## Alternatives tested

[The independent experiment](research/experiments/phase.py) compares fixed-order chord distance, fixed-order squared wrapped angular distance, and chord distance with unrestricted assignments. The angular solver checks means for all circular cuts. The unrestricted solver enumerates assignments, using deterministic tie breaking; global quarter-turn relabelings are removed before counting order changes.

All three run the same accepted-step selection and RK4 scheme. The experimental chord method reproduces production state values exactly in the recorded runs. The alternative fits are never imported by production code.

| Scenario | Angular fit: maximum state difference | Unrestricted fit: maximum state difference |
| --- | ---: | ---: |
| Default stop | 0.326 | 0 |
| Continuous walking | 0.0389 | 0.420 |
| Coupling disabled | 0 | 0 |

These maxima span x, y, dx and dy; they are not purely position errors. The [full report](research/phase-results.json) includes events, final states, both objective values, wrapped error jumps, assignment changes and wrap/degenerate examples. Objective averages along different trajectories are not a fair standalone ranking of methods. Large jumps also occur with the existing phase mapping and hybrid branch transitions.

The production fit is retained: it agrees with the natural chord-distance reading and prescribed gait order. The alternatives demonstrate sensitivity, not evidence that the original program used a different method.

This regenerates the committed report:

```sh
.venv/bin/python research/experiments/phase.py > research/phase-results.json
```
