import asyncio
import logging
# from slack_sdk.errors import SlackApiError


def folder_like_name(start_doc):
    path_parts = []
    # ddk: ignore wt to keep dependencies simple
    # timestamp = wt.kit.TimeStamp(self.start_doc["time"])
    # path_parts.append(timestamp.path)
    path_parts.append(start_doc.get("plan_name"))
    path_parts.append(start_doc.get("Name", ""))
    path_parts.append(start_doc.get("uid")[:8])
    return " ".join(x for x in path_parts if x)


def status_color(status):
    if status in ["running", "success"]:
        color = "green"
    else:
        color = "red"
    return color


def async_client_method_handler(client_method, callback=None, **kwargs):
    """
    starts client_method task and ties a callback function 
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


