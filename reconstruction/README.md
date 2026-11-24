# Кошечка: implementation notes

Open [the interactive viewer](index.html), [tracking-camera MP4](output/kitty.mp4), [fixed-camera MP4](output/kitty-travel.mp4), or [animated GIF](output/kitty.gif). The viewer works directly from a local file, with no server or network dependencies. It supports scrubbing, playback speed, view angle, camera tracking, two character-print polarities, silhouettes and wireframes. The original film is linked at its source, not distributed here.

This is a **source-based approximation**, not recovered original software or a frame-exact replica. It implements the published dynamics and shape-construction method. It does not reproduce the handmade grimaces, arched back, titles or montage. The geometry is estimated: the default `fitted` preset calibrates only the upper body, tail and camera against a few film samples (see [fidelity](../FIDELITY.md)).

## Small implementation

Start with [minimal.py](minimal.py): a small loop that advances four legs, constructs one pose and immediately writes one image. It does not retain animation frames, trajectories, JSON or event histories.

The motion equations, phase correction, RK4 step and leg-angle solver are together in [kitty/core.py](kitty/core.py) with named branches and documented numerical choices. Published constants and initial states are written directly beside the algorithm and checked against the archived tables. [geometry.py](kitty/geometry.py) supplies relative transforms, tapered solids and the estimated model. The large browser animation file is an optional export, not simulation state.

The [project README](../README.md#try-it) shows how to pipe it into FFmpeg.

The streaming path uses constant memory with respect to movie duration: four current leg states, one small geometry tree, and image buffers. The Python interpreter, Pillow and enlarged RGB preview are modern conveniences; this is not a claim that their runtime fits BESM-4 RAM. A packed printer bitmap and native implementation are estimated in the [memory accounting](../MEMORY-BUDGET.md). The history collector in `kitty/experiment.py` and the viewer/export machinery are optional tools around this core.

**Front-elbow direction:** for each leg, two mirror-image bends satisfy beta = c·gamma and reach the same endpoint, so endpoint tests alone cannot tell them apart. The solver takes the negative-gamma root, which puts the front elbow behind the shoulder-to-foot line as in the computed film frames. A direction-specific regression test checks this.

## Run the full export

From the repository root, after following the installation instructions in the [project README](../README.md):

```sh
.venv/bin/python reconstruction/run.py
```

This produces 385 poses over 16 simulation seconds at 24 fps, two MP4s, a GIF, a contact sheet, model parameters, browser data and a CSV trace of all four legs. MP4 encoding requires FFmpeg; `--no-video` skips it. Pillow is the only Python dependency used outside the standard library; it is already in the root requirements file. Python 3.9 or later is sufficient.

```sh
# A separate experiment: continuous walking, no head turn, no video encoding.
.venv/bin/python reconstruction/run.py --cruise --no-head-turn --duration 12 --no-video --output /tmp/kitty-cruise
```

The test suite is described under [Check it](../README.md#check-it) in the project README.

`--dt` changes integration step size; `--no-coupling` disables phase correction. `--model` reads a JSON file based on [model.json](output/model.json). This exposes the major dimensions; the head details are in `geometry.py`. Shoulder height must remain at the published 0.75; the exporter rejects a conflicting value. Files written to an alternate output directory do not automatically replace the viewer's `output/animation.js`.

`--literal` runs the printed decision thresholds and stopping sign without the repairs below. It is an experimental comparison mode, **not a second working animation**: at the default small step it fails with “Swing selected before K2 was initialized.” No fallback to keyframes is performed. This does not establish how the original implementation behaved at its unknown step size.

## What comes from the article

| Component | Implementation and source |
|---|---|
| Six leg acceleration pairs | `kitty/core.py`, table 1, pp.205–206 |
| Branch decisions and remembered K1…K7 | Table 2, p.206; updates only on accepted integration samples |
| Initial conditions and constants | Written explicitly in the core from tables 3–5; initial states and coefficients checked against the preserved CSVs |
| Phase mapping and leg order | pp.208–209; right rear → right front → left rear → left front |
| Joint constraints | Figure 8 and p.202: alpha = d*y, beta = c*gamma, c = −1.2 rear / 0.8 front |
| Tree of relative frames | pp.197–201, including the four sibling segments under each leg |
| Tapered six-faced primitives | pp.194–196; only leaves draw, projected shapes are united |
| Orientation convention | pp.196–197: longitudinal direction measured from negative Z, azimuth, roll |
| Orthographic shadow | Onto global YZ, viewing along X |
| Binary character printing | White cat on a Ш background, p.194; reversed presentation is a viewing option |

The scene has **29 rendered primitives**: torso, tail, neck, ten head parts and sixteen leg segments. There is no skin mesh, skeletal animation library, learned motion model or prescribed cyclic foot path.

The leg solver writes the three segment directions as `theta1 = theta2 − c*gamma`, `theta3 = theta2 + gamma`. The complex resultant

```text
Q(gamma) = L1 exp(−i c gamma) + L2 + L3 exp(i gamma)
```

reduces the endpoint constraint to `|Q| = shoulder-to-endpoint distance`. A bracketed scalar solve selects the negative bend, with the front-leg branch checked against the computed film frames. The fourth segment then follows `alpha = d*y`. This signed-angle interpretation and branch choice are reconstruction decisions; the paper does not supply its actual solver code.

## Explicit estimates and numerical changes

- **Missing shape lists:** the paper explicitly omits them. Default leg lengths are 0.40, 0.36, 0.29 (total 1.05), foot length 0.18, and d=1.0. Torso, head, tail, whisker and ear dimensions are estimated. These are not recovered historical parameters. [Model](output/model.json), [geometry code](kitty/geometry.py).
- **Speed:** initial speed 0.554 is published. Cruise to t=4, cosine deceleration to zero at t=12, and the simulation's units-to-seconds mapping are chosen here. Body displacement integrates that speed. The default viewer follows the body; turn off “Follow the cat” or use the fixed-camera MP4 to see translation.
- **Head:** a smooth 65-degree turn from t=9 to t=12 is an inferred schedule. No body bob, tail wag or artist performance is added.
- **Integrator:** fixed maximum step 0.001, classical RK4, with branch/coefficients/phase correction frozen within each step. Output-frame boundaries may shorten a step. Discrete events therefore have first-order timing accuracy, despite RK4 within a branch. No claim of the original integrator or frame rate is made.
- **Tiny velocities:** the printed epsilon=0.001 zeroing rule can suppress accumulated acceleration at a small step and select swing before K2 is initialized. The default uses true sign crossings and does not repeatedly zero that band. The literal mode preserves the printed behavior.
- **Ground contact:** the default clamps y to zero and resets endpoint velocity to `(v, 0)` at contact. This enforces the paper's stationary-foot condition rather than retaining a small numerical touchdown error.
- **Landing endpoint:** the cubic touches y=0 with zero derivative, so an integrator can miss the double root and lift off again. The default remembers its specified end time and terminates landing on the first accepted sample at/after that time.
- **Stopping sign:** default branch 4 uses +K3, as required for braking an already descending endpoint; literal mode uses the printed −K3. This branch is implemented and tested separately but is **not exercised by the default clip**. The default run exercises branches 1, 2, 3, 5 and 6. Arbitrary new speed schedules have not been validated.
- **Singularity:** `|l-rho|` has a 1e−6 guard, with activations counted. The default run activates it zero times. Unreachable leg shapes raise an error rather than stretching the limbs silently.
- **Phase fitting:** minimize squared chord distances on the unit circle to a cross with fixed leg correspondence. Circular-mean fitting handles wraparound; a vanishing resultant chooses the first leg as reference. This is one concrete interpretation of the paper's underspecified distance/optimization convention. It does not guarantee perfect quarter-cycle spacing under all speeds.
- **KM1/KM2:** use the printed values 1 and 15 as M1/M2. Preserve the paper's 5M=2 despite its inconsistency with the claimed speed bound.
- **Printing:** 160×100 character cells, a hand-defined 5×5 Ш glyph in a 6×6 cell, and an 18-degree object yaw are display estimates. There is no simulated film grain, optical distortion, exposure or jitter. Pillow and browser Canvas can differ by an edge cell in polygon rasterization.

## Checks and comparison

The core tests cover front-elbow direction and source-table initial values, world-stationary stance, final rest, timestep convergence, endpoint/joint constraints, right-handed coordinate frames including vertical axes, nested scale/translation, landing boundary conditions, wrapped phase fitting and selectable stopping sign.

- Largest endpoint reconstruction residual: less than **1e−10** model units.
- Largest difference in sampled endpoint position when halving dt: **0.00130** model units.
- Largest sampled planted-foot displacement in world coordinates: **1.5e−10** model units per frame.
- All four legs finish grounded with zero velocity; maximum foot-endpoint height is about **0.258**.
- The viewer supports four rendering modes, scrubbing and camera controls, including a narrow mobile layout.

[Numerical report](output/verification.json) · [controller events](output/diagnostics.json) · [contact sheet](output/contact-sheet.jpg).

Qualitative comparison against the computed portions of the original film guided the baseline geometry. The [fidelity study](../FIDELITY.md) then registered eight film samples (per-shot scale, translation and leg-phase offset) and fitted the upper body, tail and camera; the remaining error is still large. Artist shots were not used as motion targets. The source film and comparison screenshots are not redistributed.

Open refinements: foot trajectories and contact timing from a clean computed sequence, the limb-length ratios, and the speed schedule. The fitted preset does not constrain any of these.

## Presets and inspection

`run.py --preset fitted` (the default) uses the measured upper-body calibration; `--preset baseline` retains the previous model. `--model` still overrides either with custom JSON. The controller and default trajectory are unchanged. [Fidelity results](../FIDELITY.md) document the limits of the fit. The streaming runner accepts frame count and then preset, for example `python reconstruction/minimal.py 385 baseline`.

The optional inspector supports frame stepping, leg highlighting and event navigation. Selection pauses playback. Events at integration times between displayed samples navigate to the first following sample; lift-off time is the observed accepted endpoint, not an interpolated physical root. Older exports continue to play without event diagnostics.
