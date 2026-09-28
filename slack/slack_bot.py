import os
import re
import logging
import pathlib
import shutil

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from bluesky.callbacks.zmq import RemoteDispatcher

from slack_event_model import Acquisition
from lib import async_client_method_handler as client_handler


logging.basicConfig(level=logging.INFO)

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


def plot(app:AsyncApp, paths:list[pathlib.Path], event:dict, channels:list[str]):
    """
    Upload a selection of images located within the folder path. 
    Total number of images uploaded is limited to 10.
    
    special args
    ------------
    channels: list of strings

        specifies the starting portions of image names to be considered for uploading.  
        If no channels are specified, all channels are selected
    """
    path = paths[0]
    kwargs = dict(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]),)
    if not channels:
        channels = [""]
    file_uploads = []
    for channel in channels:
        for cpath in path.glob(f"{channel}*.png"):
            file_uploads.append(dict(file=str(cpath), title=cpath.name))
    # truncate files to 10
    note = ""
    if len(file_uploads) > 10:
        file_uploads = file_uploads[:10]
        note = "We truncated the images uploaded to 10."
    scan_folder = path.parts[-1]
    if file_uploads:
        kwargs["initial_comment"] = f"<@{event['user']}> images from `{scan_folder}`. {note}"
    else:
        kwargs["initial_comment"] = "`{scan_folder}` had no images."
    client_handler(app.client.files_upload_v2, file_uploads=file_uploads, **kwargs)


def fetch(app:AsyncApp, paths:list[pathlib.Path], event:dict, *args):
    kwargs = dict(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]),)

    path = paths[0]
    scan_name = path.stem
    assert path.exists()

    try:
        shutil.make_archive(scan_name, "zip", str(path))
        client_handler(
            app.client.files_upload_v2,
            initial_comment=f"<@{event['user']}> fetched from `{scan_name}`",
            filename= f"{scan_name}_primary.wt5",
            file=str(path),
            **kwargs
        )
    finally:
        if (zipfile := pathlib.Path(f"{path.stem}.zip")).exists():
            os.remove(str(zipfile))


def _find_acquisition_file(specifier):
    return list(pathlib.Path("/data").glob(f"*{specifier}*"))


async def main():
    handler = AsyncSocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])
    await handler.connect_async()
    global user
    user = await app.client.auth_test()
    logging.info(user)

    dispatcher = RemoteDispatcher("zmq-proxy:5568")
    dispatcher.subscribe(Acquisition(app, os.environ.get("SLACK_CHANNEL")))
    await asyncio.to_thread(dispatcher.start)

    await handler.disconnect_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

