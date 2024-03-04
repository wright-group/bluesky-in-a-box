import logging
import asyncio

from bluesky.callbacks import CallbackBase
from lib import async_client_method_handler, folder_like_name, AcquisitionState 


client_handler = async_client_method_handler


class Acquisition(CallbackBase):

    def __init__(self, app, channel):
        self.app = app
        self.channel = channel

    def start(self, doc):
        logging.debug(f"start: {doc}")
        self.start_doc = doc
        self.stopped = False
        self.timestamp = None

        if "shape" in doc:
            shape = doc.get("shape")
        elif "num_points" in doc:
            shape = (doc.get("num_points"),)

        self.state = AcquisitionState(
            name=folder_like_name(doc),
            status="running",
            shape=shape,
            start_time=self.start_doc.get("time"),
            last_time=self.start_doc.get("time"),
        )

        # client_handler(
        #     self.app.client.chat_postMessage,
        #     callback=self.store_acquisition_timestamp,
        #     text=self.state.as_text(),
        #     channel=self.channel
        # )
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
        self.state["last_time"] = doc.get("time")
        self.state["seq_num"] = doc.get("num_events")["primary"]

        text = self.state.as_text()
        self.stopped = True

        if self.timestamp:
            client_handler(
                self.app.client.chat_update,
                text=text,
                channel=self.channel,
                ts=self.timestamp
            )
        else:
            client_handler(self.app.client.chat_postMessage, text=text, channel=self.channel)

    def event(self, doc):
        # Technically, events from "baseline" measurements can screw up this tracker, 
        # they may be distinguishable by `descriptor` field, but might be tricky to tell 
        # which is which
        # since only an issue at first and last point, ignoring issue for now
        if "seq_num" in doc:
            self.state["seq_num"] = doc.get("seq_num")
            self.state["last_time"] = doc.get("time")
        logging.debug(f"EVENT: {doc}")
        logging.info(f"STATE: {self.state.as_text()}")

    def descriptor(self, doc):
        logging.debug(f"DESCRIPTOR: {doc}")

    def store_acquisition_timestamp(self, response, exception):
        """callback for scan start, so we can edit the message"""
        self.timestamp = response["ts"]

    async def watch_progress(self):
        """continually update slack message with state
        """
        uid = self.start_doc.get("uid")
        # TODO: use a stopped event to trigger this
        while True:
            logging.debug("ATTEMPTING TO UPDATE PROGRESS")
            if uid == self.start_doc.get("uid") or self.stopped:
                break
            if self.timestamp:
                client_handler(
                    self.app.client.chat_update, 
                    text=self.state.as_text(), 
                    channel=self.channel, 
                    ts=self.timestamp
                )
            else:
                client_handler(
                    self.app.client.chat_postMessage,
                    callback=self.store_acquisition_timestamp,
                    text=self.state.as_text(),
                    channel=self.channel
                )
            # try:
            #     await asyncio.wait_for(self._stop_sig.wait(), 60)
            #     break
            # except asyncio.TimeoutError:
            #     continue
            await asyncio.sleep(60)

