# Plan

Recorded 24 November 2026. Update the status lines as milestones close; change a goal or target only with a dated note explaining the evidence.

## Primary goal: a close, measured match to the computed film

The current `fitted` preset reduces held-out landmark error by about 11%, but the absolute mismatch is still large ([fidelity study](FIDELITY.md)). The goal is to make the reconstruction match the computer-generated parts of the 1968 film closely enough that the remaining difference is comparable to annotation uncertainty, not to model error.

**Done when**, on a held-out set frozen before any fitting (square file pixels):

| Measure | Current `fitted` | Target |
| --- | ---: | ---: |
| Mean landmark error / back length | 0.535 | **≤ 0.25** |
| Silhouette IoU, both extraction thresholds | 0.289 | **≥ 0.50** |
| Foot-contact timing | not measured | **measured; median error ≤ 2 logical frames** |

and in addition:

- the leg controller equations, published constants and initial states are unchanged;
- joint constraints hold, planted feet stay stationary, and all tests pass;
- the result is published as a named preset with an updated [FIDELITY.md](FIDELITY.md), and no original film frames enter the repository.

For scale: back length is about 180 pixels in the reviewed frames, and landmarks carry 10–14 pixels of uncertainty, so annotation noise alone contributes roughly 0.07. A target of 0.25 is still about three times that.

### Milestones

1. **Evaluation set.** Review enough of the archived film to identify clean computed sequences: at least 40 logical frames from at least three shots. Resolve exposure reuse so repeated exposures share one partition. Freeze a held-out partition of at least 12 logical frames, including one shot never used for calibration, and score `baseline` and `fitted` on it. The previously inspected held-out frames (41–44 s, 66–69 s) count as seen and move to calibration.
2. **Leg evidence.** Annotate visible feet, contacts and, where visible, knee and elbow positions. Report contact timing for the current presets for the first time.
3. **Registration and speed.** Replace the constant per-shot image velocity with a fitted speed schedule. The speed schedule is an estimate in this reconstruction, so it is in scope.
4. **Fit and promote.** Fit limb-length ratios, shoulder placement, body/head/tail shape, camera and speed schedule against calibration frames only. Promote a new preset only if it meets the targets above on the frozen held-out set.

**Re-scope rule.** If milestone 1 shows the targets are unreachable for reasons outside the model (film jitter, exposure reuse, unresolvable printer lattice), revise the targets here with the evidence. Do not quietly relax the held-out protocol.

**Out of scope:** changing the published controller, the artist-drawn scenes, per-frame warping, and any claim of a frame-exact replica.

**Status:** milestone 1 in progress. 85 of 2,108 archived exposures reviewed; held-out partition not yet frozen.

## Contingency: publishing the original source

Permission to publish the original cat source code is pending ([attribution](ATTRIBUTION.md)). If it is granted:

1. Publish the code with its provenance, separately from the reconstruction's MIT-licensed code.
2. Replace estimated shape lists and schedules with the original values as a new preset.
3. Write a comparison of the reconstruction's interpretations and repairs against the original, updating [PAPER-TO-CODE.md](PAPER-TO-CODE.md).

This would take priority over the primary goal, because it settles questions that film fitting can only estimate.

**Status:** waiting for permission.

## Background track: historical sources

Pursued alongside the primary goal; progress depends on libraries and publishers. Details are in the [research guide](RESEARCH.md#historical-programming-and-libraries).

- Higher-resolution scans of the two 1968 continuous-paper output sections in *Ankunft einer Katze*. These are the most useful acquisition for the primary goal.
- The two-part 1965 Б-61 library volumes.
- The 1967 BESM-4 ИС-22 instruction, the ИС-22 series and the elementary-functions manual.

## Parked

- **Running the cat on an emulated M-20/BESM-4** within 4,096 words, matching the Python trajectory. This would replace the [memory estimate](MEMORY-BUDGET.md) with a demonstration. Revisit after the primary goal, or earlier if the original source becomes available.
- **Exercising branch 4 (stop) in a full clip** and a working literal mode. Both are documented gaps with no film evidence to check them against.
