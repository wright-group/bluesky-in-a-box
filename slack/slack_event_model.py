import asyncio
import logging

from functools import reduce

from bluesky.callbacks import CallbackBase


class Acquisition(CallbackBase):
    def __init__(self, app, channel):
        logging.info("Acquisition initialized")
        self.start_doc = None
        self.stop_doc = None
        self.app = app
        self.channel = channel
        self.shape = []

    def start(self, doc):
        logging.info(f"start: {doc}")
        self.start_doc = doc

        plan_name = self.start_doc.get("plan_name")
        uid = self.start_doc.get("uid")[:8]
        if "shape" in doc:
            self.shape = doc.get("shape")
        else:
            self.shape = (doc.get("num_points"),)
        time = self.start_doc.get("time")

        self.app.post_message(
            text=f"{plan_name} started: shape {self.shape} | uid {uid}",
            channel=self.channel
        )

    def stop(self, doc):
        logging.info(f"stop: {doc}")
        self.stop_doc = doc

        plan_name = self.start_doc.get("plan_name")
        uid = doc.get("run_start")[:8]
        exit_status = doc.get("exit_status")
        num_events = doc.get("num_events")["primary"]
        time = doc.get("time")
        percent = num_events / reduce(lambda x,y: x*y, list(self.shape)) * 100

        self.app.post_message(
            text=f"{plan_name} stopped ({exit_status}, {percent:0.0f}% complete): shape {self.shape} | uid {uid}",
            channel=self.channel
        )



    def descriptor(self, doc):
        ...

    def event(self, doc):
        ...


