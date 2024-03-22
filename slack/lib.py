import asyncio
import logging
from functools import reduce
# from slack_sdk.errors import SlackApiError


class AcquisitionState:
    def __init__(self, doc):
        if "shape" in doc:
            shape = doc.get("shape")
        elif "num_points" in doc:
            shape = (doc.get("num_points"),)
        
        # extract axes (not useful for all scans)
        self.axes = None
        if doc.get("plan_name") == "grid_scan_wp":
            # [device, start, stop, npts, units]...
            axes = doc.get("dimensions")
            self.axes = [",".join(a[0]) for a in axes if a[1] == "primary"]

        self.start_doc = doc
        self.start_time = self.start_doc.get("time")
        self.last_time = self.start_time
        self.name = folder_like_name(doc)
        self.status = "running"
        self.shape = shape
        self.seq_num = 0
        self.exit_status = None
        self.plan_name = self.start_doc.get("plan_name")

    def as_text(self):
        return f"{self.name} {self.status} | {" ".join(self.shape, self.axes)} | " \
            f"{self.progress:0.1f}% complete | {self.dt} elapsed | " \
            f"{self.status_icon}"

    @property
    def size(self)->int:
        return reduce(lambda x,y: x*y, list(self.shape))

    @property
    def dt(self)->str:
        _dt = round(self.last_time - self.start_time, 0)
        hours = int(_dt // 3600)
        minutes = int(_dt % 3600) // 60
        seconds = int(_dt % 60)
        return "{h}:{m}:{s}".format(
            h=str(hours), m=str(minutes).zfill(2), s=str(seconds).zfill(2)
        )

    @property
    def progress(self)->float:
        return self.seq_num / self.size * 100

    @property
    def status_icon(self):
        if self.status == "running":
            icon = ""
        elif self.status == "done":
            if self.exit_status == "success":
                icon = ":white_check_mark:"
            else:
                icon = ":warning:"
        return icon


def folder_like_name(start_doc):
    path_parts = []
    # ddk: ignore wt to keep dependencies simple
    # timestamp = wt.kit.TimeStamp(self.start_doc["time"])
    # path_parts.append(timestamp.path)
    path_parts.append(start_doc.get("plan_name"))
    path_parts.append(start_doc.get("Name", ""))
    path_parts.append(start_doc.get("uid")[:8])
    return " ".join(x for x in path_parts if x)


def async_client_method_handler(client_method, callback=None, **kwargs):
    """
    queues client_method task and allows a callback action
    callback must except two arguments:  response and exception
    """
    if callback is None:
        callback = lambda x,y:None

    async def runner():
        response = None
        exception = None
        try:
            logging.debug(f"method {client_method}: kwargs {kwargs}")
            response = await client_method(**kwargs)
        except Exception as e:  # SlackApiError as e:
            logging.error(f"Error with {client_method}: {e}")
            exception = e

        callback(response, exception)

    asyncio.create_task(runner())


