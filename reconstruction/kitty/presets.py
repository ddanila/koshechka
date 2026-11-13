"""Named model snapshots; calibration never silently rewrites the baseline."""
from copy import deepcopy
import json
from pathlib import Path
from .geometry import BASELINE_MODEL

PRESETS = {"baseline": BASELINE_MODEL,
           "fitted": json.loads((Path(__file__).with_name("models")/"fitted.json").read_text())}
DEFAULT_PRESET = "fitted"

def model_for(name=DEFAULT_PRESET):
    return deepcopy(PRESETS[name])
