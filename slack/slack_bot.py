import os
import re

import logging

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError


logging.basicConfig(level=logging.DEBUG)
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
            fetch_by_id(app, id, message)
        elif command == "plot":
            plot_by_id(app, id, message)

@app.command("/hello-socket-mode")
async def hello_command(ack, body):
    user_id = body["user_id"]
    await ack(f"Hi <@{user_id}>!")

@app.event("app_mention")
async def event_test(event, say):
    await say(f"Hi there, <@{event['user']}>!")

@app.event("message")
async def handle_message_events(body, logger):
    logger.debug(body)

handler = AsyncSocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])

return app, handler


class SlackApp(AsyncApp):
    async def post_message(self, **kwargs):
        try:
            result = await self.client.chat_postMessage(**kwargs)
            self.logger.info(result)

        except SlackApiError as e:
            self.logger.error(f"Error posting message: {e}")


def plot_by_id(app, id, message):
    print("plotting")
    ...

def fetch_by_id(app, id, message):
    print("fetching")
    ...
