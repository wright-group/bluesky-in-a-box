import yaqc_bluesky


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

from bluesky.protocols import Readable
from wright_plans.attune import motortune

from bluesky_autonomic import OPADevice

import pickle
print(pickle.dumps(Readable))

d1 = yaqc_bluesky.Device(38401)
d2 = yaqc_bluesky.Device(38402)
d0 = yaqc_bluesky.Device(38500)
wm = yaqc_bluesky.Device(39876)
daq = yaqc_bluesky.Device(38999)
opa = OPADevice(yaqc_bluesky.Device(39301))
