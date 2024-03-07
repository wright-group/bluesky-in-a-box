import os
import re
import logging
import pathlib

from typing import List, Optional

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from bluesky.callbacks.zmq import RemoteDispatcher

from slack_event_model import Acquisition
from lib import async_client_method_handler as client_handler

logging.basicConfig(level=logging.DEBUG)

user = {}
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
# get app's user name
desired_message = re.compile(
    r"\s*<@(?P<user>\w+)>\s+(?P<command>(fetch|plot))\s*(?P<args>([\w+]+\s*)*)"
)

def execute_command(app:AsyncApp, event:dict, match:re.Match):
    match = re.match(desired_message, event["text"])
    kwargs = dict(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]),)
    if not match:
        text = f":thinking_face: I didn't understand request `{event['text']}`"
    else:

        if match["command"] == "fetch":
            method = fetch
        elif match["command"] == "plot":
            method = plot
        specifier, *channels = match["args"].split()
        paths = _find_acquisition_file(specifier)
        if len(paths) == 1:
            method(app, paths, event, channels)
            return
        else:
            text = f"I need a single match, but I found {len(paths)} acquisition(s) matching your " \
                + f"specifier `{specifier}` :weary:"
    # if we didn't succeed, give back an informative message
    client_handler(app.client.chat_postMessage, text=text, **kwargs)


@app.event("app_mention")
async def parse_mention(event, say):
    execute_command(app, event, re.match(desired_message, event["text"]))


@app.event("message")
async def handle_message(body, logger):
    logger.debug(body)
    event = body["event"]
    mentioned = "<@{}>".format(user["user_id"]) in event["text"]
    if event["channel_type"] == "im" and mentioned:        
        execute_command(app, event, match = re.match(desired_message, event["text"]))
    else:
        logging.info("the message event was not an im type!")


def plot(app:AsyncApp, paths:str, event:dict, channels:List[str]):
    kwargs = dict(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]),)
    if not channels:
        channels = [""]
    file_uploads = []
    for channel in channels:
        for cpath in paths[0].glob(f"{channel}*.png"):
            file_uploads.append(dict(file=str(cpath), title=cpath.name))
    # truncate files to 10
    note = ""
    if len(file_uploads) > 10:
        file_uploads = file_uploads[:10]
        note = "We truncated the images uploaded to 10."
    scan_folder = paths[0].parts[-1]
    if file_uploads:
        kwargs["initial_comment"] = f"<@{event['user']}> images from `{scan_folder}`. {note}"
    else:
        kwargs["initial_comment"] = "`{scan_folder}` had no images."
    client_handler(app.client.files_upload_v2, file_uploads=file_uploads, **kwargs)


def fetch(app:AsyncApp, paths:str, event:dict, args):
    kwargs = dict(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]),)

    path = paths[0] / "primary.wt5"
    scan_name = path.parts[-2]
    assert path.exists()
    client_handler(
        app.client.files_upload_v2,
        initial_comment=f"<@{event['user']}> fetched from `{scan_name}`",
        filename= f"{scan_name}_primary.wt5",
        file=str(path),
        **kwargs
    )


def _find_acquisition_file(specifier):
    return list(pathlib.Path("/data").glob(f"*{specifier}*"))


async def main():
    handler = AsyncSocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])
    await handler.connect_async()
    global user
    user = await app.client.auth_test()
    logging.info(user)

    loop = asyncio.get_running_loop()
    dispatcher = RemoteDispatcher("zmq-proxy:5568", loop=loop)
    dispatcher.subscribe(Acquisition(app, os.environ.get("SLACK_CHANNEL")))
    await dispatcher._poll()

    await handler.disconnect_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

