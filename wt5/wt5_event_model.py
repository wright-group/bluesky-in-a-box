import contextlib
import json
import pathlib

from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky.callbacks import CallbackBase
import numpy as np
import WrightTools as wt


class GenWT5(CallbackBase):
    def __init__(self):
        self.start_doc = None
        self.stop_doc = None
        self.descriptor_doc = None
        self.data = None
        self.shape = None
        self.scan_shape = None
        self.run_dir = None
        self.bluesky_doc_dir = None
        self.stream_name = None
        self.dims = {}

    def start(self, doc):
        self.start_doc = doc
        timestamp = wt.kit.TimeStamp(self.start_doc["time"])
        path_parts = []
        path_parts.append(timestamp.path)
        path_parts.append(self.start_doc.get("plan_name"))
        path_parts.append(self.start_doc.get("Name"))
        path_parts.append(self.start_doc.get("uid")[:8])
        dirname = " ".join(x for x in path_parts if x)
        self.run_dir = pathlib.Path("/data") / dirname
        self.run_dir.mkdir(exist_ok=True, parents=True)
        self.bluesky_doc_dir = self.run_dir / "bluesky_docs"
        self.bluesky_doc_dir.mkdir(exist_ok=True)

        with open(self.bluesky_doc_dir / "start.json", "wt") as f:
            json.dump(self.start_doc, f, indent=2)

        self.shape = list(self.start_doc["shape"])
        self.scan_shape = tuple(self.shape)

    def descriptor(self, doc):
        self.descriptor_doc = doc
        self.stream_name = self.descriptor_doc["name"]

        with open(
            self.bluesky_doc_dir / f"{self.stream_name} descriptor.json", "wt"
        ) as f:
            json.dump(self.descriptor_doc, f, indent=2)

        self.data = wt.Data(
            self.run_dir / f"{self.stream_name}.wt5",
            name=self.stream_name,
            edit_local=True,
        )

        self.data.attrs["created"] = wt.kit.TimeStamp(self.start_doc["time"]).RFC3339

        # compute full shape, channel shapes
        # handling of dims may need adjustment for cameras...
        chan_shapes = {}
        self.dims = {}
        for k, desc in self.descriptor_doc["data_keys"].items():
            chan_shape = desc.get("shape", [])
            chan_dims = desc.get("dims", [])
            if any(dim in self.dims for dim in chan_dims):
                chan_shapes[k] = self.dims[chan_dims[0]]
            else:
                chan_shapes[k] = (
                    list(self.scan_shape)
                    + [1] * (len(self.shape) - len(self.scan_shape))
                    + list(chan_shape)
                )
                self.shape += desc.get("shape", [])
                for dim in chan_dims:
                    self.dims[dim] = chan_shapes[k]

        self.data.create_variable(
            "labtime",
            shape=self.scan_shape + (1,) * (len(self.shape) - len(self.scan_shape)),
            units="s",
        )
        for k, chan_shape in chan_shapes.items():
            chan_shape += [1] * (len(self.shape) - len(chan_shape))
            units = self.descriptor_doc["data_keys"][k].get("units")
            if any(
                k in self.descriptor_doc["object_keys"][mot]
                for mot in self.start_doc.get("motors")
            ):
                self.data.create_variable(k, shape=chan_shape, units=units)
            elif k in self.dims:
                self.data.create_variable(k, shape=chan_shape, units=units)
            else:
                self.data.create_channel(k, shape=chan_shape, units=units)
            # fill out var md
        self.data.flush()

        # fill md
        # what to do about md that is nested... attrs doesn't like that
        # What to do about lower dimensional axes... not trivial... could parse out from plan pattern, I guess... I think that is the intended way...

    def event(self, doc):
        pos = np.unravel_index(doc["seq_num"] - 1, self.scan_shape)
        self.data["labtime"][pos + (...,)] = doc["time"]
        for var, entry in doc["data"].items():
            pos_var = [slice(None) if j > 1 else 0 for j in self.data[var].shape]
            pos_var[: len(self.scan_shape)] = pos
            self.data[var][tuple(pos_var)] = entry
        self.data.flush()

    def stop(self, doc):
        try:
            self.stop_doc = doc

            with open(self.bluesky_doc_dir / "stop.json", "wt") as f:
                json.dump(self.stop_doc, f, indent=2)

            # end timestamp
            # exit_status/reason

            # transform (axes make filling harder than it needs to be)
            self.data.transform(
                *(f"{x}_readback" for x in self.start_doc["motors"][: len(self.scan_shape)]),
                *self.dims,
            )

            self.data.flush()

            for dev, hints in self.descriptor_doc["hints"].items():
                for chan in hints["fields"]:
                    if not chan in self.data.channel_names:
                        continue
                    try:
                        wt.artists.quick2D(
                            self.data, channel=chan, autosave=True, save_directory=self.run_dir, fname=chan
                        )
                    except wt.exceptions.DimensionalityError:
                        wt.artists.quick1D(
                            self.data, channel=chan, autosave=True, save_directory=self.run_dir, fname=chan
                        )

            with open(self.run_dir / f"{self.descriptor_doc['name']} tree.txt", "wt") as f:
                with contextlib.redirect_stdout(f):
                    self.data.print_tree(verbose=True)
        finally:
            self.data.flush()
            self.data.close()


dispatcher = RemoteDispatcher("zmq-proxy:5568")
gen = GenWT5()
dispatcher.subscribe(gen)
dispatcher.start()
edit_local = True
