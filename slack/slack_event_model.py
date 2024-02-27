from functools import reduce

from bluesky.callbacks import CallbackBase


def folder_like_name(start_doc):
    path_parts = []
    # ddk: ignore wt to keep dependencies simple
    # timestamp = wt.kit.TimeStamp(self.start_doc["time"])
    # path_parts.append(timestamp.path)
    path_parts.append(start_doc.get("plan_name"))
    path_parts.append(start_doc.get("Name"))
    path_parts.append(start_doc.get("uid")[:8])
    return " ".join(x for x in path_parts if x)


class Acquisition(CallbackBase):
    def __init__(self, app, channel):
        self.app = app
        self.channel = channel

        self.start_doc = None
        self.stop_doc = None
        self.shape = []
        self.message_id = ""  # TODO: tage the start message so we can just edit it on completion

    def start(self, doc):
        self.start_doc = doc

        if "shape" in doc:
            self.shape = doc.get("shape")
        elif "num_points" in doc:
            self.shape = (doc.get("num_points"),)
        time = self.start_doc.get("time")

        self.path = folder_like_name(doc)

        text = f"{self.path} started: shape {self.shape}",
        self.app.post_message(text=text, channel=self.channel)

    def stop(self, doc):
        self.stop_doc = doc

        plan_name = self.start_doc.get("plan_name")
        uid = doc.get("run_start")[:8]
        exit_status = doc.get("exit_status")
        num_events = doc.get("num_events")["primary"]
        time = doc.get("time")
        percent = num_events / reduce(lambda x,y: x*y, list(self.shape)) * 100

        text = f"{self.path} stopped ({exit_status}, {percent:0.0f}% complete): shape {self.shape} | uid {uid}"
        self.app.post_message(text=text, channel=self.channel)

    def descriptor(self, doc):
        ...

    def event(self, doc):
        ...


