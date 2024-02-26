import asyncio

from functools import reduce

from bluesky.callbacks import CallbackBase


class Acquisition(CallbackBase):
    def __init__(self, app, channel):
        self.start_doc = None
        self.stop_doc = None
        self.client = app
        self.channel = channel

    def start(self, doc):
        print(doc)
        self.start_doc = doc

        plan_name = self.start_doc.get("plan_name"),
        uid = self.start_doc.get("uid")[:8],
        shape = list(self.start_doc.get("shape", [self.start_doc.get("num_points")])),
        time = self.start_doc.get("time"),

        asyncio.create_task(
            self.app.post_message(
                text=f"{plan_name} started: shape {self.shape} | uid {uid}",
                channel=self.channel
            )
        )


    def stop(self, doc):
        print(doc)
        self.stop_doc = doc

        plan_name = self.start_doc.get("plan_name"),
        uid = doc.get("run_start")[:8],
        shape = list(self.start_doc.get("shape", [self.start_doc.get("num_points")])),
        exit_status = doc.get("exit_status")
        num_events = doc.get("num_events")["primary"],
        time = doc.get("time")
        percent = num_events / reduce(lambda x,y: x*y, self.shape) * 100

        asyncio.create_task(
            self.app.post_message(
                text=f"{plan_name} stopped ({exit_status}, {percent:0.0f}% complete): shape {num} | uid {uid}",
                channel=self.channel
            )
        )



    def descriptor(self, doc):
        ...

    def event(self, doc):
        ...


