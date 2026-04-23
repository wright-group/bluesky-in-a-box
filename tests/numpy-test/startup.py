from bluesky.plans import count
from bluesky.preprocessors import baseline_decorator

# Movable devices to read baseline before and after scans
movables = []

# Cache of describe keys used to determine if sub-devices should be ejected from the namespace
all_device_keys = {}

dev = None
prev_dev = None

# Wrap all of the plans with baseline which reads movables before and after
count = baseline_decorator(movables)(count)
