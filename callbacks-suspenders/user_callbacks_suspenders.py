import logging
import asyncio
import pathlib
import os

import WrightTools as wt
from bluesky.callbacks import CallbackBase
from bluesky.suspenders import SuspenderBase
import time

class SimpleTestCallback(CallbackBase):
    # Simple Callback telling ReManager to print when 
    # an init, Event, Start, or Stop document is published.
    # Currently it also points out if the wt5 directory has been
    # found.
    def __init__(self):
        print("SimpleTestCallback initialized")
        super().__init__
        pass

    def start(self, doc):
        super().start(doc)
        self.start_doc=doc
        timestamp = wt.kit.TimeStamp(self.start_doc["time"])
        path_parts = []
        path_parts.append(timestamp.path)
        path_parts.append(self.start_doc.get("plan_name"))
        path_parts.append(self.start_doc.get("Name"))
        path_parts.append(self.start_doc.get("uid")[:8])
        dirname = " ".join(x for x in path_parts if x)
        self.run_dir = pathlib.Path("/data") / dirname
        self.bluesky_doc_dir = self.run_dir / "bluesky_docs"
        isdirectory=os.path.isdir(self.run_dir)
        print("run started")
        print("Run_dir found at start = "+str(isdirectory))
        print("")
        #super().start(doc)
        pass

    def stop(self, doc):
        super().stop(doc)
        self.stop_doc=doc
        isdirectory=os.path.isdir(self.run_dir)
        print("event found")
        print("Run_dir found at stop = "+str(isdirectory))
        print("")
        #super().stop(doc)
        pass

    def event(self, doc):
        # Technically, events from "baseline" measurements can screw up this tracker, 
        # they may be distinguishable by `descriptor` field, but might be tricky to tell 
        # which is which
        # since only an issue at first and last point, ignoring issue for now
        super().event(doc)
        self.event_doc=doc
        isdirectory=os.path.isdir(self.run_dir)
        print("event found")
        time.sleep(1.0)
        print("Run_dir found at event = "+str(isdirectory))
        print("")
        #super().event(doc)
        pass