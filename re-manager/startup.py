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
from wright_plans.attune import motortune

from bluesky.plans import count
from bluesky.preprocessors import baseline_decorator
from bluesky.protocols import Movable

happi_client = happi.Client(database=happi.backends.backend("/happi_db.json"))

movables = []

for device in happi_client.all_items:
    try:
        vars()[device.name] = happi_client.load_device(name=device.name)
        if isinstance(vars()[device.name], Movable):
            movables.append(vars()[device.name])
    except Exception as e:
        print(e)

grid_scan_wp = baseline_decorator(movables)(grid_scan_wp)
