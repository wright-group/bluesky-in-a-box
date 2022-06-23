import contextlib
import json
import pathlib
import subprocess
import traceback

from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky.callbacks import CallbackBase
import numpy as np
import toolz
import WrightTools as wt

class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

class GenWT5(CallbackBase):
    def __init__(self):
        self.start_doc = None
        self.stop_doc = None
        self.descriptor_docs = {}
        self.descriptor_uid_to_docs = {}
        self.data = {}
        self.shape = {}
        self.scan_shape = {}
        self.run_dir = None
        self.bluesky_doc_dir = None
        self.detector_axes = {}
        self.axis_units = {}

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
            json.dump(self.start_doc, f, indent=2, cls=NumpyArrayEncoder)

        self.shape["primary"] = list(
            self.start_doc.get("shape", [self.start_doc.get("num_points")])
        )
        self.scan_shape["primary"] = tuple(self.shape["primary"])
        self.shape["baseline"] = (2,)
        self.scan_shape["baseline"] = (2,)
        # At present only "primary" and "baseline" have shapes associated
        # A shape is required to actually make the data object for the stream
        # Future usecases of additional streams (e.g. flyers) will need to deal
        # with their shapes appropriately.  KFS 2021-09-29

    def descriptor(self, doc):
        stream_name = doc["name"]
        self.descriptor_docs[stream_name] = doc
        self.descriptor_uid_to_docs[doc["uid"]] = doc

        with open(
            self.bluesky_doc_dir / f"{stream_name} descriptor.json", "wt"
        ) as f:
            json.dump(doc, f, indent=2, cls=NumpyArrayEncoder)

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
        dim_shapes = {}
        self.detector_axes[stream_name] = []
        for k, desc in doc["data_keys"].items():
            chan_shape = desc.get("shape", [])
            chan_dims = desc.get("dims", [])
            for d, s in zip(chan_dims, chan_shape):
                dim_shapes[d] = s
        dim_shapes = {k: dim_shapes[k] for k in sorted(dim_shapes)}
        for i, (k, v) in enumerate(dim_shapes.items()):
            sh = [1] * len(dim_shapes)
            sh[i] = v
            dim_shapes[k] = sh
            self.shape[stream_name] += [v]

        def joint_shape(*args):
            return tuple(max(a) for a in zip(*args)) 

        for k, desc in doc["data_keys"].items():
            chan_shapes[k] = list(self.scan_shape[stream_name] + joint_shape(*[dim_shapes[i] for i in desc.get("dims", [])]))
            if desc.get("independent", False):
                self.detector_axes[stream_name].append(k)

        self.data[stream_name].create_variable(
            "labtime",
            shape=self.scan_shape[stream_name] + (1,) * (len(self.shape[stream_name]) - len(self.scan_shape[stream_name])),
            units="s",
        )
        for k, chan_shape in chan_shapes.items():
            dtype = self.descriptor_docs[stream_name]["data_keys"][k]["dtype"]
            if dtype not in ["number", "array"]:
                print(f"Skipping {k} because we do not deal with dtype {dtype}")
                continue
            chan_shape += [1] * (len(self.shape[stream_name]) - len(chan_shape))
            units = self.descriptor_docs[stream_name]["data_keys"][k].get("units")
            if (
                any(
                    k in self.descriptor_docs[stream_name]["object_keys"].get(det, {})
                    for det in self.start_doc.get("detectors")
                )
                and not k in self.detector_axes[stream_name]
            ):
                self.data[stream_name].create_channel(k, shape=chan_shape, units=units)
            else:
                var = self.data[stream_name].create_variable(k, shape=chan_shape, units=units)
                var.label = k
            for vk, v in self.descriptor_docs[stream_name]["data_keys"].get(k, {}).items():
                if vk in ("shape", "units", "dtype"):
                    continue
                self.data[stream_name][k].attrs[vk] = v

        self.axis_units = self.start_doc.get("plan_axis_units", {})
        if "plan_pattern" in self.start_doc and stream_name == "primary":
            # Currently only applied to "primary", this may need further fleshing out for additional stream types
            if self.start_doc["plan_pattern"] == "outer_product":
                add_outer_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.axis_units)
            elif self.start_doc["plan_pattern"] == "outer_list_product":
                add_outer_list_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.axis_units)
            elif self.start_doc["plan_pattern"] == "inner_product":
                add_inner_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["plan_pattern_args"]["num"], self.start_doc["motors"], self.axis_units)
            elif self.start_doc["plan_pattern"] == "inner_list_product":
                add_inner_list_product_axes(self.data[stream_name], self.start_doc["plan_pattern_args"]["args"], self.start_doc["motors"], self.axis_units)

        if stream_name == "primary":
            for hw, (units, terms) in self.start_doc.get("plan_constants", {}).items():
                if len(terms) == 1 and terms[0][1] is None:
                    c = self.data[stream_name].create_constant(terms[0][0], units=units)

        # Add stationary hardware to the primary dataset
        # This assumes the order is baseline descriptor -> baseline reading -> primary descriptor
        # because the data is read from the wt5 file. This is the current order and is unlikely to
        # be changed, as it is the natural order for the way baseline works, but if e.g. both
        # descriptors come before the baseline event, the data would not be ready here.
        if stream_name == "primary" and "baseline" in self.data:
            primary = self.data["primary"]
            baseline = self.data["baseline"]

            for var in baseline.variable_names:
                if not var in primary:
                    val = baseline[var][:1]
                    val = val.reshape((1,) * len(self.shape["primary"]))
                    primary.create_variable(values=val, **baseline[var].attrs)

        self.data[stream_name].flush()

        # what to do about md that is nested... attrs doesn't like that
        # What to do about lower dimensional axes... not trivial... could parse out from plan pattern, I guess... I think that is the intended way...

    def event(self, doc):
        stream_name = self.descriptor_uid_to_docs[doc["descriptor"]]["name"]
        pos = np.unravel_index(doc["seq_num"] - 1, self.scan_shape[stream_name])
        self.data[stream_name]["labtime"][pos + (...,)] = doc["time"]
        for var, entry in doc["data"].items():
            if var not in self.data[stream_name]:
                continue
            pos_var = [slice(None) if j > 1 else 0 for j in self.data[stream_name][var].shape]
            pos_var[: len(self.scan_shape[stream_name])] = pos
            self.data[stream_name][var][tuple(pos_var)] = entry
        self.data[stream_name].flush()

    def stop(self, doc):
        self.stop_doc = doc

        with open(self.bluesky_doc_dir / "stop.json", "wt") as f:
            json.dump(self.stop_doc, f, indent=2, cls=NumpyArrayEncoder)

        # end timestamp
        # exit_status/reason

        # transform (axes make filling harder than it needs to be)
        try:
            self.data["primary"].transform(
                *self.start_doc["motors"][: len(self.scan_shape["primary"])],
                *self.detector_axes["primary"],
            )
        except KeyError:
            self.data["primary"].transform("labtime", *self.detector_axes["primary"])

        for ax in self.data["primary"].axes:
            if ax.natural_name in self.axis_units:
                ax.convert(self.axis_units[ax.natural_name])

        self.data["primary"].flush()

        for name, descriptor_doc in self.descriptor_docs.items():
            with open(
                self.run_dir / f"{name} tree.txt", "wt"
            ) as f:
                with contextlib.redirect_stdout(f):
                    self.data[name].print_tree(verbose=True)

            filepath = self.data[name].filepath
            self.data[name].flush()
            self.data[name].close()

            for dev, hints in descriptor_doc["hints"].items():
                for chan in hints["fields"]:
                    try:
                        subprocess.call(["python", "./quick_plot.py", filepath, chan], timeout=10)
                    except Exception as e:
                        traceback.print_exc()
                        print(f"Failed to plot {chan}")


def add_outer_product_axes(data, pattern_args, motors, axis_units):
    pattern_args.insert(4, False)
    for i, (mot, (_, start, stop, npts, _)) in enumerate(zip(motors, toolz.partition(5, pattern_args))):
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
