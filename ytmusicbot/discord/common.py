import re
from ytmusicbot.common.main import logger

logger = logger.getChild("discord")



class DiscordException(Exception):
    pass



class ButtonID:
    play_rx = re.compile("play-(.*)")
    queue_rx = re.compile("queue-(.*)")
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
