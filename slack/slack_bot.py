import os
import re
import logging
import pathlib

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from slack_event_model import Acquisition

from bluesky.callbacks.zmq import RemoteDispatcher


logging.basicConfig(level=logging.DEBUG)
logging.info(os.environ["SLACK_BOT_TOKEN"])
logging.info(os.environ["SLACK_APP_TOKEN"])


class SlackApp(AsyncApp):
    def post_message(self, **kwargs):
        try:
            logging.info(f"posting message to {kwargs['channel']}")
            asyncio.create_task(self.client.chat_postMessage(**kwargs))

        except Exception as e:  # SlackApiError as e:
            self.logger.error(f"Error posting message: {e}")

    def files_upload(self, **kwargs):
        try:
            logging.info(f"uploading file to {kwargs['channel']}")
            asyncio.create_task(self.client.files_upload_v2(**kwargs))

        except Exception as e:  # SlackApiError as e:
            self.logger.error(f"Error posting message: {e}")


app = SlackApp(token=os.environ["SLACK_BOT_TOKEN"])

desired_message = re.compile(
    r"(?P<name>\w+) (?P<command>(fetch|plot)) (?P<id>\w+)"
)

# bind app to event callbacks
@app.message(re.compile(desired_message))
async def parse_message(message, say):
    app.logger.info(f"we got a message: {message}")
    # message: https://api.slack.com/events/message
    match = re.match(desired_message, message["text"])
    if match is None:
        await say(":thinking_face: I didn't understand this request")
        return
    else:
        command = match["command"]
        await say(f"I understand you want me to {command} with id {match['id']}")
        if command == "fetch":
            fetch_by_id(app, match['id'], message)
        elif command == "plot":
            plot_by_id(app, match['id'], message)

@app.command("/hello-socket-mode")
async def hello_command(ack, body):
    user_id = body["user_id"]
    await ack(f"Hi <@{user_id}>!")

@app.event("app_mention")
async def event_test(event, say):
    await say(f"Hi there, <@{event['user']}>!" + f"event keys are {event.keys()}")

@app.event("message")
async def handle_message_events(body, logger):
    logger.debug(body)

def plot_by_id(app, id, message):
    print("plotting is not implemented yet")
    ...

def fetch_by_id(app:SlackApp, id, message):
    id_exists = [_ for _ in pathlib.Path("/data").glob(f"* {id}")]
    if id_exists:
        file = id_exists[0] / "primary.wt5"
        logging.debug(f"channel {message['channel']} file {file} exists? {file.exists()}")
        app.files_upload(
            initial_comment=f"<@{message['user']}> here is {id}!",
            channel=message["channel"],
            filename="primary.wt5",
            file=str(file),
        )

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

