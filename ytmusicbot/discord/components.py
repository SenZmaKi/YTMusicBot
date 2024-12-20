from typing import TYPE_CHECKING
import interactions
import ytmusicbot.youtube as youtube
from ytmusicbot.common.main import logger
from ytmusicbot.discord.common import ButtonID
from interactions.api.voice.player import Player

if TYPE_CHECKING:
    from ytmusicbot.discord.logic import Config


def song_embed_component(
    song: youtube.SongMetadata | youtube.SongMetadata,
) -> interactions.Embed:
    logger.debug(f"Embedding {song}")
    return interactions.Embed(
        title=song["title"],
        url=song["url"],
    ).set_thumbnail(url=song["thumbnail_url"])


def pause_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SECONDARY,
        emoji="⏸",
        custom_id=ButtonID.pause,
    )


def resume_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        emoji="▶️",
        custom_id=ButtonID.resume,
    )


def loop_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SECONDARY,
        emoji="🔁",
        custom_id=ButtonID.loop,
    )


def unloop_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        emoji="🔁",
        custom_id=ButtonID.unloop,
    )


def next_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        emoji="⏭️",
        custom_id=ButtonID.next,
    )


def previous_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        emoji="⏮️",
        custom_id=ButtonID.previous,
    )


def play_button(url: str) -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.GREEN,
        label="PLAY",
        emoji="🎵",
        custom_id=f"play-{url}",
    )


def queue_button(url: str) -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="QUEUE",
        emoji="➕",
        custom_id=f"queue-{url}",
    )


def increase_volume_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="+",
        emoji="🔊",
        custom_id=ButtonID.increase_volume,
    )


def decrease_volume_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="-",
        emoji="🔈",
        custom_id=ButtonID.decrease_volume,
    )


def mute_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SECONDARY,
        emoji="🔇",
        custom_id=ButtonID.mute,
    )


def unmute_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        emoji="🔇",
        custom_id=ButtonID.unmute,
    )


def shuffle_button() -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        emoji="🔀",
        custom_id=ButtonID.shuffle,
    )


def favourite_button(url: str) -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SECONDARY,
        emoji="❤️",
        custom_id=f"favourite-{url}",
    )


def unfavourite_button(url: str) -> interactions.Button:
    return interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        emoji="❤️",
        custom_id=f"unfavourite-{url}",
    )


def volume_control_component(config: "Config"):
    volume_bar = generate_volume_bar(config.volume, 15)
    volume_emoji = "🔊"
    if config.volume <= 0:
        volume_emoji = "🔇"
    elif config.volume <= 30:
        volume_emoji = "🔈"
    elif config.volume <= 65:
        volume_emoji = "🔉"
    muter_button = unmute_button() if config.mute else mute_button()
    buttons = [decrease_volume_button(), increase_volume_button(), muter_button]
    text = f"{volume_emoji}    {volume_bar}    {config.volume}%"
    return (text, buttons)


def generate_volume_bar(volume: int, length: int = 10) -> str:
    filled_length = int(
        length * volume / 100
    )  # Calculate the number of filled segments
    empty_length = length - filled_length  # Calculate the number of empty segments
    return (
        f"{'█' * filled_length}{'░' * empty_length}"  # Bar with filled and empty parts
    )


def now_playing_component(
    song: youtube.SongMetadata,
    player: Player | None,
    config: "Config",
    footer="Now playing",
) -> tuple[interactions.Embed, list[interactions.Button]]:
    is_paused = player and player.paused
    pauser_button = resume_button() if is_paused else pause_button()
    looper_button = unloop_button() if config.loop else loop_button()
    url = song["url"]
    favouriter_button = (
        unfavourite_button(url) if config.in_favourites(song) else favourite_button(url)
    )
    # NOTE: Discord only allows 5 buttons per row
    playback_buttons = [
        previous_button(),
        pauser_button,
        next_button(),
        favouriter_button,
        looper_button,
        # shuffle_button(),
    ]
    embed = song_embed_component(song).set_footer(footer)
    return embed, playback_buttons
