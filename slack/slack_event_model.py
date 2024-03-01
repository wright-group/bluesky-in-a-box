from functools import reduce
import logging
import asyncio
import time

from bluesky.callbacks import CallbackBase
from lib import async_client_method_handler, folder_like_name, icon 


client_handler = async_client_method_handler


class Acquisition(CallbackBase):

    text_template = "{name} {status} | {shape} | {progress:0.1f}% complete | {dt} elapsed | {status_icon}"

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
        self.stopped = False
        self.timestamp = None

        if "shape" in doc:
            self.shape = doc.get("shape")
        elif "num_points" in doc:
            self.shape = (doc.get("num_points"),)

        self.state = dict(
            name=folder_like_name(doc),
            status="running",
            status_icon=icon("running"),
            shape=self.shape,
            progress=0.,
            start_time=self.start_doc.get("time"),
        )
        text = self.text_template.format(**self.state)

        client_handler(
            self.app.client.chat_postMessage,
            callback=self.store_acquisition_timestamp,
            text=text,
            channel=self.channel
        )
        asyncio.create_task(self.watch_progress())

    def stop(self, doc):
        self.state["status"] = "done"
        logging.debug(f"stop: {doc}")

        if doc.get("run_start") != self.start_doc.get("uid"):
            # for now, just drop the event if we don't know the state
            # TODO: add a default dict to handle unset parameters
            logging.error(f"start/stop event mismatches:  {self.start_doc} {doc}")
            return
        self.state["exit_status"] = doc.get("exit_status")
        self.state["dt"] = self._dt_fmt(doc.get("time") - self.state["start_time"])
        self.state["progress"] = self._progress(doc.get("num_events")["primary"])
        self.state["status_icon"] = icon(self.state["exit_status"])

        text = self.text_template.format(**self.state)
        self.stopped = True

        if self.timestamp:
            client_handler(self.app.client.chat_update, text=text, channel=self.channel, ts=self.timestamp)
        else:
            client_handler(self.app.client.chat_postMessage, text=text, channel=self.channel)

    def descriptor(self, doc):
        if doc.get("descriptor") == self.start_doc.get("uid"):
            if "seq_num" in doc:
                self.state["progress"] = self._progress(doc.get("seq_num")["primary"])
            if "time" in doc:
                self.state["dt"] = self._dt_fmt(doc.get("time") - self.state["start_time"])
        logging.debug(f"DESCRIPTOR: {doc}")
        logging.info(f"STATE: {self.state}")

    def event(self, doc):
        logging.debug(f"EVENT: {doc}")

    def _progress(self, num_events):
        return num_events / reduce(lambda x,y: x*y, list(self.shape)) * 100
    
    def _dt_fmt(self, dt):
        hours = int(dt // 3600)
        minutes = int(dt % 3600) // 60
        seconds = int(round(dt % 60, 0))
        return "{h}:{m}:{s} elapsed".format(
            h=str(hours), m=str(minutes).zfill(2), s=str(seconds).zfill(2)
        )

    def store_acquisition_timestamp(self, response, exception):
        """callback for scan start, so we can edit the message"""
        self.timestamp = response["ts"]

    async def watch_progress(self):
        """continually update slack message with state
        """
        uid = self.start_doc.get("uid")
        # TODO: use a stopped event to trigger this
        while True:
            await asyncio.sleep(60)
            if uid == self.start_doc.get("uid") or self.stopped:
                break
            if self.timestamp:
                client_handler(
                    self.app.client.chat_update, 
                    text=self.text_template.format(**self.state), 
                    channel=self.channel, 
                    ts=self.timestamp
                )
