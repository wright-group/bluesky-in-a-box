import socket

from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky.callbacks import CallbackBase
import yaqc

# Host mapped name on windows and mac
host = "host.docker.internal" 
try:
    socket.gethostbyname(host)
except socket.gaierror:
    host = "172.17.0.1"  # Default host ip on Linux

class SlackFeed(CallbackBase):
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
        self.slack_port = {"port":39900, "host":host}

    def start(self, doc):
        self.start_doc = doc
        path_parts = []
        path_parts.append(self.start_doc.get("plan_name"))
        path_parts.append(self.start_doc.get("Name"))
        path_parts.append(self.start_doc.get("uid")[:8])

        self.shape["primary"] = list(
            self.start_doc.get("shape", [self.start_doc.get("num_points")])
        )
        self.scan_shape["primary"] = tuple(self.shape["primary"])

        client = yaqc.Client(**self.slack_port)
        client.publish_wt5_start()

    def descriptor(self, doc):
        ...

    def event(self, doc):
        ...

    def stop(self, doc):
        self.stop_doc = doc

        client = yaqc.Client(**self.slack_port)
        client.publish_wt5_stop()

dispatcher = RemoteDispatcher("zmq-proxy:5568")
feed = SlackFeed()
dispatcher.subscribe(feed)
dispatcher.start()
