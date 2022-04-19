import socket
import happi

from wright_plans import (
    list_scan_wp,
    rel_list_scan_wp,
    list_grid_scan_wp,
    rel_list_grid_scan_wp,
    scan_wp,
    grid_scan_wp,
    rel_grid_scan_wp,
    rel_scan_wp,
)
from wright_plans.attune import (
    motortune, run_tune_test,
    run_intensity,
    run_setpoint,
    run_holistic,
)

from bluesky.plans import count
from bluesky.preprocessors import baseline_decorator
from bluesky.protocols import Movable

happi_client = happi.Client(database=happi.backends.backend("/happi_db.json"))

# Movable devices to read baseline before and after scans
movables = []

# Cache of describe keys used to determine if sub-devices should be ejected from the namespace
all_device_keys = {}

# Host mapped name on windows and mac
host = "host.docker.internal" 
try:
    socket.gethostbyname(host)
except socket.gaierror:
    host = "172.17.0.1"  # Default host ip on Linux

for device in happi_client.all_items:
    # Skip devices marked inactive in happi
    if not device.active:
        continue
    try:
        # Translate localhost into internal host machine reference
        if device.host in ("localhost", "127.0.0.1"):
            device.host = host
        dev = happi.from_container(device)
        dev_keys = set(dev.describe().keys())
        for prev_dev_name, prev_dev_keys in all_device_keys.items():
            # Do not add this device (break for loop, skip else clause)
            # if all of my keys are in another device
            if dev_keys.issubset(prev_dev_keys):
                break
            # Eject (set to None) a subdevice previously added
            if prev_dev_keys.issubset(dev_keys):
                vars()[prev_dev_name] = None
                del all_device_keys[prev_dev_name]
        else:
            # Only runs if this is a new device (no break above)
            print("Adding", device.name)
            # Add to namespace
            vars()[device.name] = dev
            # Add keys to cache
            all_device_keys[dev.name] = dev_keys
            # Add to movables list if Movable
            if isinstance(dev, Movable):
                movables.append(dev)
    except Exception as e:
        print(e)

dev = None
prev_dev = None

# Wrap all of the plans with baseline which reads movables before and after
list_scan_wp = baseline_decorator(movables)(list_scan_wp)
rel_list_scan_wp = baseline_decorator(movables)(rel_list_scan_wp)
list_grid_scan_wp = baseline_decorator(movables)(list_grid_scan_wp)
rel_list_grid_scan_wp = baseline_decorator(movables)(rel_list_grid_scan_wp)
scan_wp = baseline_decorator(movables)(scan_wp)
grid_scan_wp = baseline_decorator(movables)(grid_scan_wp)
rel_grid_scan_wp = baseline_decorator(movables)(rel_grid_scan_wp)
rel_scan_wp = baseline_decorator(movables)(rel_scan_wp)
motortune = baseline_decorator(movables)(motortune)
run_tune_test = baseline_decorator(movables)(run_tune_test)
run_intensity = baseline_decorator(movables)(run_intensity)
run_setpoint = baseline_decorator(movables)(run_setpoint)
run_holistic = baseline_decorator(movables)(run_holistic)
count = baseline_decorator(movables)(count)
