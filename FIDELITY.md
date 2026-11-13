# Measuring the match to the computed film

The default **fitted** preset adjusts only the estimated upper body, tail and camera. The original **baseline** remains reproducible with `reconstruction/run.py --preset baseline`. Neither preset changes the controller, total limb length, joint constraints or speed schedule.

## Evidence and registration

Eight frames were reviewed from the [Mathematical Etudes film](https://etudes.ru/etudes/cat-animation/): 41–44 seconds and 66–69 seconds. The first two frames of each shot calibrate the fit; the following two are held out. [Approximate observations](research/landmarks.json) include the back endpoints, tail tip, mean ear tips and muzzle endpoint, with 10–14 pixel uncertainty. These are manually estimated observations by Astra GPT, not precise ground truth. Original pixels and annotated images remain outside this repository.

The archived classification is only a starting point. Frames at 39 and 64 seconds are partly off-screen. Reviewed enlarged samples at 74, 78 and 82 seconds have clipped tails, whiskers or feet; they were excluded from numerical fitting. Later shots may reuse earlier animation at a different scale or polarity. Unique file hashes do not establish independent animation content. Solid-black artist scenes were excluded; a character background alone does not identify computer-generated animation.

Each shot has one scale, translation and constant horizontal image velocity. The shape fit uses five parameters: body length/height, tail extension/rise and yaw. It never warps individual frames. Leg phase is aligned separately by searching one offset per shot against calibration silhouettes. Both square file pixels and the webpage's 4:3 display interpretation are tested. The committed default uses square file pixels, avoiding an unverified stretch.

The annotations do **not** identify hidden joints, left/right feet, shoulder positions or individual limb-length ratios. Those parameters remain at the baseline values. The footage has no clearly marked floor and the samples are too sparse to establish contact times; no contact-timing accuracy score is claimed. Stationary planted feet and joint constraints are checked in the reconstructed model instead.

## Results and limits

| Display interpretation | Baseline held-out landmark error | Fitted error | Reduction | Baseline silhouette IoU | Fitted IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Square pixels | 0.601 | 0.535 | 11.0% | 0.144 | 0.289 |
| 4:3 display | 0.596 | 0.535 | 10.3% | 0.157 | 0.279 |

Landmark error is mean Euclidean distance divided by observed back length. IoU measures the approximate subject envelope after smoothing printer strokes, extracting local contrast, closing gaps and retaining the subject component. Thin whiskers and blurred white boundaries are uncertain; alternate extraction thresholds are included in the [complete results](research/fidelity-results.json). Both tested thresholds preserve the overlap improvement.

The candidate passes the predeclared relative gate: at least 10% less held-out landmark error, no overlap decrease, and valid geometry with unchanged contact dynamics. **The absolute errors remain large.** In particular, a constant image-velocity registration cannot explain all observed slowing, film jitter or editing. Body thickness reaches the imposed upper bound. This is a modest calibration of missing shape parameters, not recovery of the historical model or a close frame match. The two aspect interpretations yield different yaw estimates, illustrating ambiguity between camera and transfer geometry.

Reproduce with the private archive path supplied explicitly:

```sh
python -m pip install -r requirements-research.txt
python research/experiments/fidelity.py --archive /path/to/cat --output /tmp/fidelity-results.json
python scripts/check_research.py
```

The experiment writes numeric results only and does not change the production preset. Synthetic tests verify exact registration recovery and ensure held-out measurements cannot affect the fitting parameters. The selected model snapshot is versioned separately; original regression fixtures remain untouched.
