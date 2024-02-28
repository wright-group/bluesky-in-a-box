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
async def user_request(event, say):
    message = event["text"]
    match = re.match(desired_message, message)
    if match is None:
        await say(f":thinking_face: I didn't understand request `{message}`")
        return
    else:
        command = match["command"]
        if command == "fetch":
            status = fetch_by_id(app, match['args'], event)
            if status != 1:
                await say(
                    f"I need a single match, but I found {status} acquisition(s) matching your" \
                    + f"specifier `{match['args']}` :weary:"
                )
        elif command == "plot":
            await say(f"Not yet implemented!")
            # plot_by_id(app, match['args'], message)


@app.event("message")
async def handle_message_events(body, logger):
    logger.debug(body)


def plot_by_id(app, id, message):
    raise NotImplementedError


def fetch_by_id(app:AsyncApp, specifier, meta):
    id_exists = [_ for _ in pathlib.Path("/data").glob(f"*{specifier}*")]
    status = len(id_exists)
    if status == 1:
        file = id_exists[0] / "primary.wt5"
        scan_name = file.parts[-2]
        client_handler(
            app.client.files_upload_v2,
            callback=None,
            initial_comment=f"<@{meta['user']}> fetched from {scan_name}",
            channel=meta["channel"],
            filename="primary.wt5",
            thread_ts=meta["ts"],
            file=str(file),
        )
    return status


async def main():
    handler = AsyncSocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])
    await handler.connect_async()

    loop = asyncio.get_running_loop()
    logging.info(f"loop:{loop}")
    dispatcher = RemoteDispatcher("zmq-proxy:5568", loop=loop)
    dispatcher.subscribe(Acquisition(app, os.environ.get("SLACK_CHANNEL")))
    logging.info("adding poll to loop")
    await dispatcher._poll()
    await handler.disconnect_async()
    logging.info("closing")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

