import contextlib
import json
import pathlib

from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky.callbacks import CallbackBase
import numpy as np
import toolz
import WrightTools as wt


class GenWT5(CallbackBase):
    def __init__(self):
        self.start_doc = None
        self.stop_doc = None
        self.descriptor_docs = {}
        self.data = {}
        self.shape = {}
        self.scan_shape = {}
        self.run_dir = None
        self.bluesky_doc_dir = None
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

        self.shape["primary"] = list(
            self.start_doc.get("shape", [self.start_doc.get("num_points")])
        )
        self.scan_shape["primary"] = tuple(self.shape["primary"])

    def descriptor(self, doc):
        stream_name = doc["name"]
        self.descriptor_docs[stream_name] = doc

        with open(
            self.bluesky_doc_dir / f"{stream_name} descriptor.json", "wt"
        ) as f:
            json.dump(doc, f, indent=2)

        self.data[stream_name] = wt.Data(
            self.run_dir / f"{stream_name}.wt5",
            name=stream_name,
            edit_local=True,
        )

        for k, v in self.start_doc.items():
            try:
                self.data[stream_name].attrs[k] = v
            except:
                print(
                    f"Skipping key {repr(k)} from start document in metadata because it cannot be placed in HDF5 attrs"
                )
        self.data[stream_name].attrs["created"] = wt.kit.TimeStamp(self.start_doc["time"]).RFC3339

        # compute full shape, channel shapes
        # handling of dims may need adjustment for cameras...
        chan_shapes = {}
        self.dims[stream_name] = {}
        for k, desc in doc["data_keys"].items():
            chan_shape = desc.get("shape", [])
            chan_dims = desc.get("dims", [])
            if any(dim in self.dims[stream_name] for dim in chan_dims):
                chan_shapes[k] = self.dims[stream_name][chan_dims[0]]
            else:
                chan_shapes[k] = (
                    list(self.scan_shape[stream_name])
                    + [1] * (len(self.shape[stream_name]) - len(self.scan_shape[stream_name]))
                    + list(chan_shape)
                )
                self.shape[stream_name] += desc.get("shape", [])
                for dim in chan_dims:
                    self.dims[stream_name][dim] = chan_shapes[k]

        self.data[stream_name].create_variable(
            "labtime",
            shape=self.scan_shape[stream_name] + (1,) * (len(self.shape[stream_name]) - len(self.scan_shape[stream_name])),
            units="s",
        )
        for k, chan_shape in chan_shapes.items():
            chan_shape += [1] * (len(self.shape[stream_name]) - len(chan_shape))
            units = self.descriptor_docs[stream_name]["data_keys"][k].get("units")
            if (
                any(
                    k in self.descriptor_docs[stream_name]["object_keys"][det]
                    for det in self.start_doc.get("detectors")
                )
                and not k in self.dims[stream_name]
            ):
                self.data[stream_name].create_channel(k, shape=chan_shape, units=units)
            else:
                self.data[stream_name].create_variable(k, shape=chan_shape, units=units)
            for vk, v in self.descriptor_docs[stream_name]["data_keys"][k].items():
                if vk in ("shape", "units", "dtype"):
                    continue
                self.data[stream_name][k].attrs[vk] = v

        if "plan_pattern" in self.start_doc:
            if self.start_doc["plan_pattern"] == "outer_product":
                add_outer_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.start_doc["plan_axis_units"])
            elif self.start_doc["plan_pattern"] == "outer_list_product":
                add_outer_list_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.start_doc["plan_axis_units"])
            elif self.start_doc["plan_pattern"] == "inner_product":
                add_inner_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["plan_pattern_args"]["num"], self.start_doc["motors"], self.start_doc["plan_axis_units"])
            elif self.start_doc["plan_pattern"] == "inner_list_product":
                add_inner_list_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.start_doc["plan_axis_units"])

        for hw, (units, terms) in self.start_doc.get("plan_constants", {}).items():
            terms.append([-1, hw])
            const_term = -1 * ([t for t in terms if t[1] is None] or [[0]])[0][0]
            terms = list(filter(lambda x: x[1] is not None, terms))
            if const_term < 0:
                terms = [[-1 * coeff, var] for coeff, var in terms]
            c = self.data[stream_name].create_constant(
                "+".join(f"{coeff}*{var}_readback" for coeff, var in terms)
            )
            c.units = units

        self.data[stream_name].flush()

        # what to do about md that is nested... attrs doesn't like that
        # What to do about lower dimensional axes... not trivial... could parse out from plan pattern, I guess... I think that is the intended way...

    def event(self, doc):
        stream_name = "primary" # TODO get stream name properly
        print(self.scan_shape[stream_name])
        pos = np.unravel_index(doc["seq_num"] - 1, self.scan_shape[stream_name])
        self.data[stream_name]["labtime"][pos + (...,)] = doc["time"]
        for var, entry in doc["data"].items():
            pos_var = [slice(None) if j > 1 else 0 for j in self.data[stream_name][var].shape]
            pos_var[: len(self.scan_shape[stream_name])] = pos
            self.data[stream_name][var][tuple(pos_var)] = entry
        self.data[stream_name].flush()

    def stop(self, doc):
        try:
            self.stop_doc = doc

            with open(self.bluesky_doc_dir / "stop.json", "wt") as f:
                json.dump(self.stop_doc, f, indent=2)

            # end timestamp
            # exit_status/reason

            # transform (axes make filling harder than it needs to be)
            try:
                self.data["primary"].transform(
                    *(
                        f"{x}_readback"
                        for x in self.start_doc["motors"][: len(self.scan_shape["primary"])]
                    ),
                    *self.dims["primary"],
                )
            except KeyError:
                self.data["primary"].transform("labtime", *self.dims["primary"])

            self.data["primary"].flush()

            for name, descriptor_doc in self.descriptor_docs.items():
                with open(
                    self.run_dir / f"{name} tree.txt", "wt"
                ) as f:
                    with contextlib.redirect_stdout(f):
                        self.data[name].print_tree(verbose=True)

                for dev, hints in descriptor_doc["hints"].items():
                    for chan in hints["fields"]:
                        if not chan in self.data[name].channel_names:
                            continue
                        try:
                            wt.artists.quick2D(
                                self.data[name],
                                channel=chan,
                                autosave=True,
                                save_directory=self.run_dir,
                                fname=chan,
                            )
                        except (wt.exceptions.DimensionalityError, IndexError):
                            wt.artists.quick1D(
                                self.data[name],
                                channel=chan,
                                autosave=True,
                                save_directory=self.run_dir,
                                fname=chan,
                            )
        finally:
            for d in self.data.values():
                d.flush()
                d.close()


def add_outer_product_axes(data, pattern_args, motors, axis_units):
    for i, (mot, (_, start, stop, npts)) in enumerate(zip(motors, toolz.partition(4, pattern_args))):
        shape = [1] * data.ndim
        shape[i] = npts
        arr = np.linspace(start, stop, npts)
        arr = arr.reshape(tuple(shape))
        data.create_variable(f"{mot}_points", values=arr, units=axis_units.get(mot))

def add_outer_list_product_axes(data, pattern_args, motors, axis_units):
    for i, (mot, (_, lis)) in enumerate(zip(motors, toolz.partition(2, pattern_args))):
        shape = [1] * data.ndim
        shape[i] = len(lis)
        arr = np.array(lis)
        arr = arr.reshape(tuple(shape))
        data.create_variable(f"{mot}_points", values=arr, units=axis_units.get(mot))

def add_inner_product_axes(data, pattern_args, npts, motors, axis_units):
    for mot, (_, start, stop) in zip(motors, toolz.partition(3, pattern_args)):
        shape = [1] * data.ndim
        shape[0] = npts
        arr = np.linspace(start, stop, npts)
        arr = arr.reshape(tuple(shape))
        data.create_variable(f"{mot}_points", values=arr, units=axis_units.get(mot))

def add_inner_list_product_axes(data, pattern_args, motors, axis_units):
    for mot, (_, lis) in zip(motors, toolz.partition(2, pattern_args)):
        shape = [1] * data.ndim
        shape[0] = len(lis)
        arr = np.array(lis)
        arr = arr.reshape(tuple(shape))
        data.create_variable(f"{mot}_points", values=arr, units=axis_units.get(mot))


dispatcher = RemoteDispatcher("zmq-proxy:5568")
gen = GenWT5()
dispatcher.subscribe(gen)
dispatcher.start()
edit_local = True
