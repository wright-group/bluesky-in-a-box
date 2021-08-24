import happi

from wright_plans import (
    list_scan,
    rel_list_scan,
    list_grid_scan,
    rel_list_grid_scan,
    scan_nd,
    scan,
    grid_scan,
    rel_grid_scan,
    rel_scan,
)
from wright_plans.attune import motortune

from bluesky.protocols import Readable

import pickle
print(pickle.dumps(Readable))


happi_client = happi.Client(database=happi.backends.backend("~/.local/share/happi/db.json"))

for device in happi_client.all_devices:
    try:
        vars()[device.name] = happi_client.load_device(name=device.name)
    except Exception as e:
        print(e)


print("STARTUP.PY NAMESPACE")
for key in dir():
    print(f"    {key}")
