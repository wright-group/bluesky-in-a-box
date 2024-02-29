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
    r"(?P<user><@\w+>)\s+(?P<command>(fetch|plot))\s+(?P<args>\w+)"
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
        await say(f"Not yet implemented!")
        specifier, *channels = match["args"].split()
        status = plot(app, specifier, channels, event)


def plot(app, specifier, channels, meta):
    paths = _find_acquisition_file(specifier)
    status = len(paths)
    if status == 1:
        file_uploads = []
        scan_folder = paths[0].parts[-2]
        for channel, path in zip(channels, map(lambda x: paths[0] / f"{x}.png", channels)):
            if path.exists():
                file_uploads.append(dict(file=path, title=channel))

        status = len(file_uploads) > 0
        if status:
            client_handler(
                app.client.files_upload_v2,
                initial_comment=f"<@{meta['user']}> fetched from `{scan_folder}`",
                channel=meta["channel"],
                file_uploads=file_uploads,
                thread_ts=meta["ts"],
            )

    return status


def _find_acquisition_file(specifier):
    return [path for path in pathlib.Path("/data").glob(f"*{specifier}*")]


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
            thread_ts=meta["ts"],
            file=str(path),
        )
    return status


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

