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
        self.slack_port = {"port":39900, "host":host}
        self.client = yaqc.Client(**self.slack_port)

    def start(self, doc):
        print(doc)
        self.start_doc = doc
        out_doc = dict(
            plan_name = self.start_doc.get("plan_name"),
            uid = self.start_doc.get("uid")[:8],
            shape = list(self.start_doc.get("shape", [self.start_doc.get("num_points")])),
            time = self.start_doc.get("time"),
        )
        print(out_doc)

        client = yaqc.Client(**self.slack_port)
        client.publish_wt5_start(out_doc)

    def stop(self, doc):
        print(doc)
        self.stop_doc = doc
        out_doc = dict(
            plan_name = self.start_doc.get("plan_name"),
            uid = doc.get("run_start")[:8],
            shape = list(self.start_doc.get("shape", [self.start_doc.get("num_points")])),
            exit_status = doc.get("exit_status"),
            num_events = doc.get("num_events")["primary"],
            time = doc.get("time"),
            # TODO: include doc.get("num_events")["primary"] for completeness
        )
        print(out_doc)

        client = yaqc.Client(**self.slack_port)
        client.publish_wt5_stop(out_doc)

    def descriptor(self, doc):
        ...

    def event(self, doc):
        ...


dispatcher = RemoteDispatcher("zmq-proxy:5568")
feed = SlackFeed()
dispatcher.subscribe(feed)
dispatcher.start()
