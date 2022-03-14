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
    motortune,
    run_tune_test,
    run_intensity,
    run_setpoint,
    run_holistic,
)

from bluesky.plans import count
from bluesky.preprocessors import baseline_decorator
from bluesky.protocols import Movable

happi_client = happi.Client(database=happi.backends.backend("/happi_db.json"))

movables = []

# Host mapped name on windows and mac
host = "host.internal.docker" 
try:
    socket.gethostbyname(host)
except socket.gaierror:
    host = "172.17.0.1"  # Default host ip on Linux

for device in happi_client.all_items:
    try:
        if device.host in ("localhost", "127.0.0.1"):
            device.host = host
        vars()[device.name] = happi.from_container(device)
        if isinstance(vars()[device.name], Movable):
            movables.append(vars()[device.name])
    except Exception as e:
        print(e)

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
