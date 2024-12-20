import re
from ytmusicbot.common.main import logger
from ytmusicbot.common.main import load_dotenv
import os
import interactions
from typing import Any


class DiscordException(Exception):
    pass


logger = logger.getChild("discord")

load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

if not discord_token:
    raise DiscordException("Discord token not found in environment variables")

server_ids = os.getenv("SERVER_IDS")
if not server_ids:
    raise DiscordException("Server IDs not found in environment variables")
scopes: Any = server_ids.split(",")
# List to allow changes to reflect across files
bot_restarted = [False]


def make_bot():
    return interactions.Client(
        token=discord_token,
        send_not_ready_messages=True,
        sync_interactions=True,
        delete_unused_application_cmds=True,
        auto_defer=True,
    )


bot = make_bot()


class ButtonID:
    play_rx = re.compile("play-(.*)")
    queue_rx = re.compile("queue-(.*)")
    favourite_rx = re.compile("favourite-(.*)")
    unfavourite_rx = re.compile("unfavourite-(.*)")
    pause = "pause"
    resume = "resume"
    loop = "loop"
    unloop = "unloop"
    next = "next"
    previous = "previous"
    increase_volume = "increase_volume"
    decrease_volume = "decrease_volume"
    mute = "mute"
    unmute = "unmute"
    shuffle = "shuffle"
