"""Stream the reconstruction as RGB frames: no history, JSON, viewer or logs.

python reconstruction/minimal.py | ffmpeg -f rawvideo -pixel_format rgb24 \
    -video_size 960x600 -framerate 24 -i - -pix_fmt yuv420p kitty.mp4
Optional arguments: frame count (default 385), then preset (baseline or fitted).
"""
import sys
from kitty.core import initial_legs, step, speed
from kitty.geometry import cat, leaves
from kitty.render import render
from kitty.presets import model_for

model = model_for(sys.argv[2]) if len(sys.argv)>2 else model_for()

legs = initial_legs()
t, distance = 0., 0.
for index in range(int(sys.argv[1]) if len(sys.argv) > 1 else 385):
    target = index / 24
    while t < target - 1e-12:
        dt = min(.001, target - t)
        v = speed(t)[0]
        step(legs, t, dt)
        distance += dt * (v + speed(t + dt)[0]) / 2
        t += dt
    pose = {'t': target, 'legs': [leg.state for leg in legs]}
    tree, _ = cat(pose, model)
    # Fixed camera; 4.432 is the integral of the default speed schedule.
    picture = render(leaves(tree), angle=model['view_yaw_degrees'], shift=4.432/2-distance, span=9.)
    sys.stdout.buffer.write(picture.tobytes())
