from functools import reduce
import logging

from bluesky.callbacks import CallbackBase
from lib import async_client_method_handler, folder_like_name, status_color 


client_handler = async_client_method_handler


class Acquisition(CallbackBase):

    text_template = "{name} <span style='color:{color}'></span> {status} | {shape} | {progress:0.1f}% complete"

    def __init__(self, app, channel):
        self.app = app
        self.channel = channel

        self.start_doc = None
        self.state = None
        self.shape = []
        self.message_id = ""  # TODO: tag the start message so we can just edit it on completion

    def start(self, doc):
        logging.debug(f"start: {doc}")
        self.start_doc = doc
        self.timestamp = None

        if "shape" in doc:
            self.shape = doc.get("shape")
        elif "num_points" in doc:
            self.shape = (doc.get("num_points"),)

        self.state = dict(
            path=folder_like_name(doc),
            status="running",
            color=status_color("running"),
            shape=self.shape,
            progress=0.,
            start_time=self.start_doc.get("time"),
        )
        text = self.text_template.format(**self.kwargs)
        logging.debug(f"text: {text}")

        client_handler(
            self.app.client.post_message(text=text, channel=self.channel),
            callback=self.store_acquisition_timestamp
        )

    def stop(self, doc):
        self.state["status"] = "done"
        logging.debug(f"stop: {doc}")

        if doc.get("run_start") != self.start_doc.get("uid"):
            # for now, just drop the event if we don't know the state
            # TODO: add a default dict to handle unset parameters
            logging.error(f"start/stop event mismatches:  {self.start_doc} {doc}")
            return
        self.state["exit_status"] = doc.get("exit_status")
        self.state["stop_time"] = doc.get("time")
        self.state["progress"] = doc.get("num_events")["primary"] / reduce(lambda x,y: x*y, list(self.shape)) * 100

        text = self.text_template.format(**self.kwargs)
        logging.debug(f"text: {text}")

        if self.timestamp:
            client_handler(self.app.client.chat_update(text=text, channel=self.channel, ts=self.timestamp))
        else:
            client_handler(self.app.client.post_message(text=text, channel=self.channel))
        

    def descriptor(self, doc):
        logging.debug(f"descriptor: {doc}")

    def event(self, doc):
        logging.debug(f"event: {doc}")

    def store_acquisition_timestamp(self, response, exception):
        """callback for scan start, so we can edit the message"""
        self.timestamp = response["ts"]


