import os
import re
import logging
import pathlib

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from bluesky.callbacks.zmq import RemoteDispatcher

from slack_event_model import Acquisition
from lib import async_client_method_handler as client_handler


logging.basicConfig(level=logging.DEBUG)

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
desired_message = re.compile(
    r"\s*(?P<user><@\w+>)\s+(?P<command>(fetch|plot))\s*(?P<args>([\w+]+\s*)*)"
)


@app.event("app_mention")
async def parse_user_request(event, say):
    match = re.match(desired_message, event["text"])
    if match is None:
        await say(f":thinking_face: I didn't understand request `{event['text']}`")
        return
    command = match["command"]
    if command == "fetch":
        status = fetch(app, match['args'], event)
        if status != 1:
            await say(
                f"I need a single match, but I found {status} acquisition(s) matching your" \
                + f"specifier `{match['args']}` :weary:"
            )
    elif command == "plot":
        specifier, *channels = match["args"].split()
        status = plot(app, specifier, event, channels if channels else [""])
        logging.debug("status {status}")


def plot(app, specifier, meta, channels):
    paths = _find_acquisition_file(specifier)
    status = len(paths)
    if status == 1:
        file_uploads = []
        for channel in channels:
            for cpath in paths[0].glob(f"{channel}*.png"):
                file_uploads.append(dict(file=str(cpath), title=cpath.name))
        logging.info(f"paths {paths} | channels {channels} | file_uploads {file_uploads}")
        # truncate files to 10
        note = ""
        if len(file_uploads) > 10:
            file_uploads = file_uploads[:10]
            note = "We truncated the images uploaded to 10."
        status = len(file_uploads) > 0
        scan_folder = paths[0].parts[-2]
        if status:
            client_handler(
                app.client.files_upload_v2,
                initial_comment=f"<@{meta['user']}> images from `{scan_folder}`. {note}",
                channel=meta["channel"],
                file_uploads=file_uploads,
                thread_ts=meta.get("thread_ts", meta["ts"]),
            )
    return status


def _find_acquisition_file(specifier):
    return list(pathlib.Path("/data").glob(f"*{specifier}*"))


def fetch(app:AsyncApp, specifier, meta):
    paths = _find_acquisition_file(specifier)
    status = len(paths)
    if status == 1:
        path = paths[0] / "primary.wt5"
        scan_name = path.parts[-2]
        # TODO: check existence, check file size
        client_handler(
            app.client.files_upload_v2,
            initial_comment=f"<@{meta['user']}> fetched from `{scan_name}`",
            channel=meta["channel"],
            filename= f"{scan_name}_primary.wt5",
            thread_ts=meta.get("thread_ts", meta["ts"]),
            file=str(path),
        )
    return status


@app.event("message")
async def handle_message(body, logger):
    logger.debug(body)


async def main():
    handler = AsyncSocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])
    await handler.connect_async()

    loop = asyncio.get_running_loop()
    dispatcher = RemoteDispatcher("zmq-proxy:5568", loop=loop)
    dispatcher.subscribe(Acquisition(app, os.environ.get("SLACK_CHANNEL")))
    await dispatcher._poll()

    await handler.disconnect_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

