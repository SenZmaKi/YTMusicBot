import re
from ytmusicbot.common.main import logger
from ytmusicbot.common.main import load_dotenv
import os
import disnake
from disnake.ext import commands
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
def make_bot():
    intents = disnake.Intents.default()
    intents.voice_states = True
    return commands.InteractionBot(
        intents=intents,
        test_guilds=[int(scope) for scope in scopes],
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
    loop_queue = "loop_queue"
    unloop = "unloop"
    next = "next"
    previous = "previous"
    increase_volume = "increase_volume"
    decrease_volume = "decrease_volume"
    mute = "mute"
    unmute = "unmute"
    shuffle = "shuffle"
