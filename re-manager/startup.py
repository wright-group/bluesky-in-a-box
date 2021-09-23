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

happi_client = happi.Client(database=happi.backends.backend("/happi_db.json"))

for device in happi_client.all_devices:
    try:
        vars()[device.name] = happi_client.load_device(name=device.name)
    except Exception as e:
        print(e)
