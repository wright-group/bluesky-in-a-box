import WrightTools as wt
import numpy as np
import sys
import pathlib

data = wt.open(sys.argv[1])
run_dir = pathlib.Path(sys.argv[1]).parent
chan = sys.argv[2]
cmap = wt.artists.colormaps["default"].resampled(2**12)

if not chan in data.channel_names:
    sys.exit(0)


ndim = np.sum(np.array(data[chan].shape) > 1)
if ndim > 2:
    print(f"Not plotting due to ndim {data[chan].shape}")
    sys.exit(0)

def orthogonal(*shapes):
    ret = True
    for elems in zip(*shapes):
        elems = np.array(elems)
        # Check for non ones where the first entry is one
        # This happens for e.g. array detectors which are funcitonaly orthogonal but still have the scan shape
        if elems[0] == 1 and (elems > 1).any():
            return True
        # Don't return immediately to allow the first condition to short circuit true
        if np.sum(elems > 1) > 1:
            ret = False
    return ret


transform = data.axis_names
# TODO consider not transforming and just identifying axes and then use edit-local since nothing is written
data.transform(*[x for x in transform if not orthogonal(data[chan].shape, data[x].shape)])
# locally change object name to get a more meaningful plot title
name = " ".join(run_dir.parts[-1].split()[2:])
data.natural_name = name

if ndim == 2:
    wt.artists.quick2D(
        data,
        channel=chan,
        xaxis = -2,
        yaxis = -1,
        autosave=True,
        save_directory=run_dir,
        cmap=cmap,
        fname=chan,
    )
elif ndim == 1:
    wt.artists.quick1D(
        data,
        channel=chan,
        axis = -1,
        autosave=True,
        save_directory=run_dir,
        fname=chan,
    )

