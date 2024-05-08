import logging
import asyncio

from bluesky.callbacks import CallbackBase
from lib import async_client_method_handler, AcquisitionState 


client_handler = async_client_method_handler


class Acquisition(CallbackBase):

    def __init__(self, app, channel):
        self.app = app
        self.channel = channel
        self.stop_sig = asyncio.Event()
        self.logger = logging.getLogger("Acquisition")

    def start(self, doc):
        self.logger.info(f"start: {doc}")
        self.timestamp = None
        self.state = AcquisitionState(doc)

        asyncio.create_task(self.watch_progress())

    def stop(self, doc):
        self.state.status = "done"
        self.logger.info(f"stop: {doc}")

        if doc.get("run_start") != self.state.start_doc.get("uid"):
            # for now, just drop the event if we don't know the state
            self.logger.error(f"start/stop event mismatches:  {self.state.start_doc} {doc}")
            return
        self.state.exit_status = doc.get("exit_status")
        self.state.last_time = doc.get("time")
        num_events = doc.get("num_events")  # .get("primary", 0)
        # don't update scan progress if scan is stopped at baseline
        if "primary" in num_events:
            self.state.seq_num = num_events["primary"]
        self.stop_sig.set()
        self.log_to_feed()

    def event(self, doc):
        # Technically, events from "baseline" measurements can screw up this tracker, 
        # they may be distinguishable by `descriptor` field, but might be tricky to tell 
        # which is which
        # since only an issue at first and last point, ignoring issue for now
        if "seq_num" in doc:
            self.state.seq_num = doc.get("seq_num")
            self.state.last_time = doc.get("time")
        self.logger.debug(f"EVENT: {doc}")
        self.logger.debug(f"STATE: {self.state.as_text()}")

    def descriptor(self, doc):
        self.logger.debug(f"DESCRIPTOR: {doc}")

    def store_acquisition_timestamp(self, response, exception):
        """callback for scan start, so we can edit the message"""
        self.timestamp = response["ts"]

    async def watch_progress(self):
        """continually update slack message with state"""
        while True:
            self.logger.debug("ATTEMPTING TO UPDATE PROGRESS")
            self.log_to_feed()
            try:
                await asyncio.wait_for(self.stop_sig.wait(), 20)
                self.stop_sig.clear()
                break
            except asyncio.TimeoutError:
                continue

    def log_to_feed(self):
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
