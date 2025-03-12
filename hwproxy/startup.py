import socket
import happi
from callback_wp import Callback_wp
import WrightTools as wt
from bluesky.preprocessors import subs_decorator, baseline_decorator
from bluesky.protocols import Movable
import wright_plans as wp
import wright_plans.attune as wpa
import bluesky.plans as bsp
import bluesky.plan_stubs as bpst

from bluesky.run_engine import RunEngine

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
'''
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
'''

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def list_scan_wp(detectors, *args, constants=None, per_step=None, md=None):
    yield from wp.list_scan_wp(detectors, *args, constants=constants, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def rel_list_scan_wp(detectors, *args, constants=None, per_step=None, md=None):
    yield from wp.rel_list_scan_wp(detectors, *args, constants=constants, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def list_grid_scan_wp(detectors, *args, constants=None, snake_axes=False, per_step=None, md=None):
    yield from wp.list_grid_scan_wp(detectors, *args, constants=constants, snake_axes=snake_axes, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def rel_list_grid_scan_wp(detectors, *args, constants=None, snake_axes=False, per_step=None, md=None):
    yield from wp.rel_list_grid_scan_wp(detectors, *args, constants=constants, snake_axes=snake_axes, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def scan_wp(detectors, *args, num=None, constants=None, per_step=None, md=None):
    yield from wp.scan_wp(detectors, *args, num=num, constants=constants, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def grid_scan_wp2(detectors, *args, constants=None, snake_axes=False, per_step=None, md=None):
    yield from wp.grid_scan_wp(detectors, *args, constants=constants, snake_axes=snake_axes, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def rel_grid_scan_wp(detectors, *args, constants=None, snake_axes=False, per_step=None, md=None):
    yield from wp.rel_grid_scan_wp(detectors, *args, constants=constants, snake_axes=snake_axes, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def rel_scan_wp(detectors, *args, num=None, constants=None, per_step=None, md=None):
    yield from wp.rel_scan_wp(detectors, *args, num=num, constants=constants, per_step=per_step, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def motortune(detectors, *args, opa, use_tune_points, motors, spectrometer=None, md=None):
    yield from wpa.motortune(detectors, *args, opa=opa, use_tune_points=use_tune_points, motors=motors, spectrometer=spectrometer, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def run_tune_test(detectors, *args, opa, spectrometer, md=None):
    yield from wpa.run_tune_test(detectors, *args, opa=opa, spectrometer=spectrometer, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def run_intensity(detectors, *args, opa, motor, width, npts, spectrometer, md=None):
    yield from wpa.run_intensity(detectors, *args, opa=opa, motor=motor, width=width, npts=npts, spectrometer=spectrometer, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def run_setpoint(detectors, *args, opa, motor, width, npts, spectrometer, md=None):
    yield from wpa.run_setpoint(detectors, *args, opa=opa, motor=motor, width=width, npts=npts, spectrometer=spectrometer, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def run_holistic(detectors, *args, opa, motor0, motor1, width, npts, spectrometer, md=None):
    yield from wpa.run_holistic(detectors, *args, opa=opa, motor0=motor0, motor1=motor1, width=width, npts=npts, spectrometer=spectrometer, md=md)

@subs_decorator(Callback_wp)
@baseline_decorator(movables)
def count(detectors, num=None, delay=0.0, per_shot=None, md=None):
    yield from bsp.count(detectors, num=num, delay=delay, per_shot=per_shot, md=md) 

pass