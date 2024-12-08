from typing import Any
import interactions
from ytmusicbot.discord.common import (
    ButtonID,
    logger,
    DiscordException,
)
from ytmusicbot.discord.logic import (
    decrease_volume,
    increase_volume,
    metrics,
    mute,
    reset_cache,
    search,
    play,
    pause,
    resume,
    next_,
    previous,
    clear_queue,
    set_volume,
    show_queue,
    queue,
    unmute,
    loop,
    unloop,
    now_playing,
    shuffle,
    repo,
    creator,
    dequeue,
    dequeue_next,
    dequeue_previous,
    stop,
    random_,
)

import os
from dotenv import load_dotenv

load_dotenv()

discord_token = os.getenv("DISCORD_TOKEN")

if not discord_token:
    raise DiscordException("Discord token not found in environment variables")

server_ids = os.getenv("SERVER_IDS")
if not server_ids:
    raise DiscordException("Server IDs not found in environment variables")
scopes: Any = server_ids.split(",")

bot = interactions.Client(token=os.getenv("DISCORD_TOKEN"))


@interactions.slash_command(
    name="search",
    description="Search for a song on YouTube",
    options=[
        interactions.SlashCommandOption(
            name="query",
            description="The search query",
            required=True,
            type=interactions.OptionType.STRING,
        ),
        interactions.SlashCommandOption(
            name="max_results",
            description="Maximum number of results to return",
            required=False,
            type=interactions.OptionType.INTEGER,
        ),
    ],
    scopes=scopes,
)
async def on_search_cmd(ctx: interactions.SlashContext, query: str, max_results=3):
    await search(ctx, query, max_results)


@interactions.component_callback(ButtonID.next)
async def on_next_cmp(ctx: interactions.ComponentContext):
    await next_(ctx)


@interactions.component_callback(ButtonID.previous)
async def on_previous_cmp(ctx: interactions.ComponentContext):
    await previous(ctx)


@interactions.slash_command(
    name="clear_queue",
    description="Clear the song queue",
    scopes=scopes,
)
async def on_clear_queue_cmd(ctx: interactions.SlashContext):
    await clear_queue(ctx)


@interactions.slash_command(
    name="next",
    description="Next song in the queue",
    scopes=scopes,
)
async def on_next_cmd(ctx: interactions.SlashContext):
    await next_(ctx)


@interactions.slash_command(
    name="previous",
    description="Previous song in the queue",
    scopes=scopes,
)
async def on_previous_cmd(ctx: interactions.SlashContext):
    await previous(ctx)


@interactions.component_callback(ButtonID.play_rx)
async def on_play_cmp(ctx: interactions.ComponentContext):
    url_match = ButtonID.play_rx.match(ctx.custom_id)
    if not url_match:
        raise DiscordException("Invalid custom id")
    url = url_match.group(1)
    await play(url, ctx)


@interactions.slash_command(
    name="pause",
    description="Pause the current song",
    scopes=scopes,
)
async def on_pause_cmd(ctx: interactions.SlashContext):
    await pause(ctx)


@interactions.component_callback(ButtonID.pause)
async def on_pause_cmp(ctx: interactions.ComponentContext):
    await pause(ctx)


@interactions.slash_command(
    name="resume",
    description="Resume the current song or last session",
    scopes=scopes,
)
async def on_resume_cmd(ctx: interactions.SlashContext):
    await resume(ctx)


@interactions.component_callback(ButtonID.resume)
async def on_resume_cmp(ctx: interactions.ComponentContext):
    await resume(ctx)


@interactions.slash_command(
    name="show_queue",
    description="Show the current song queue",
    scopes=scopes,
)
async def on_show_queue_cmd(ctx: interactions.SlashContext):
    await show_queue(ctx)


@interactions.component_callback(ButtonID.queue_rx)
async def on_queue_cmp(ctx: interactions.ComponentContext):
    url_match = ButtonID.queue_rx.match(ctx.custom_id)
    if not url_match:
        raise DiscordException("Invalid custom id")
    url = url_match.group(1)
    await queue(url, ctx)


@interactions.slash_command(
    name="set_volume",
    description="Set the volume",
    options=[
        interactions.SlashCommandOption(
            name="volume",
            description="The volume to set",
            required=True,
            type=interactions.OptionType.INTEGER,
        ),
    ],
    scopes=scopes,
)
async def on_set_volume_cmd(ctx: interactions.SlashContext, volume: int = 50):
    await set_volume(ctx, volume)


@interactions.slash_command(
    name="increase_volume",
    description="Increase the volume by 10%",
    scopes=scopes,
)
async def on_increase_volume_cmd(ctx: interactions.SlashContext):
    await increase_volume(ctx)


@interactions.slash_command(
    name="decrease_volume",
    description="Decrease the volume by 10%",
    scopes=scopes,
)
async def on_decrease_volume_cmd(ctx: interactions.SlashContext):
    await decrease_volume(ctx)


@interactions.slash_command(
    name="mute",
    description="Mute",
    scopes=scopes,
)
async def on_mute_cmd(ctx: interactions.SlashContext):
    await mute(ctx)


@interactions.slash_command(
    name="unmute",
    description="Unmute",
    scopes=scopes,
)
async def on_unmute_cmd(ctx: interactions.SlashContext):
    await unmute(ctx)


@interactions.component_callback(ButtonID.increase_volume)
async def on_increase_volume_cmp(ctx: interactions.ComponentContext):
    await increase_volume(ctx)


@interactions.component_callback(ButtonID.decrease_volume)
async def on_decrease_volume_cmp(ctx: interactions.ComponentContext):
    await decrease_volume(ctx)


@interactions.component_callback(ButtonID.mute)
async def on_mute_cmp(ctx: interactions.ComponentContext):
    await mute(ctx)


@interactions.component_callback(ButtonID.unmute)
async def on_unmute_cmp(ctx: interactions.ComponentContext):
    await unmute(ctx)


@interactions.slash_command(
    name="now_playing",
    description="Show the current song",
    scopes=scopes,
)
async def on_now_playing_cmd(ctx: interactions.SlashContext):
    await now_playing(ctx)


@interactions.slash_command(
    name="unloop",
    description="Disable looping",
    scopes=scopes,
)
async def on_unloop_cmd(ctx: interactions.SlashContext):
    await unloop(ctx)


@interactions.slash_command(
    name="loop",
    description="Enable looping",
    scopes=scopes,
)
async def on_loop_cmd(ctx: interactions.SlashContext):
    await loop(ctx)


@interactions.component_callback(ButtonID.unloop)
async def on_unloop_cmp(ctx: interactions.ComponentContext):
    await unloop(ctx)


@interactions.component_callback(ButtonID.loop)
async def on_loop_cmp(ctx: interactions.ComponentContext):
    await loop(ctx)


@interactions.component_callback(ButtonID.shuffle)
async def on_shuffle_cmp(ctx: interactions.ComponentContext):
    await shuffle(ctx)


@interactions.slash_command(
    name="shuffle",
    description="Shuffle the song queue",
    scopes=scopes,
)
async def on_shuffle_cmd(ctx: interactions.SlashContext):
    await shuffle(ctx)


@interactions.slash_command(
    name="repo",
    description="Link to the bot's source code",
    scopes=scopes,
)
async def on_repo_cmd(ctx: interactions.SlashContext):
    await repo(ctx)


@interactions.slash_command(
    name="creator",
    description="Link to the bot's creator",
    scopes=scopes,
)
async def on_creator_cmd(ctx: interactions.SlashContext):
    await creator(ctx)


@interactions.slash_command(
    name="play",
    description="Play a song",
    options=[
        interactions.SlashCommandOption(
            name="url",
            description="The YouTube url of the song/playlist to play",
            required=True,
            type=interactions.OptionType.STRING,
        ),
    ],
    scopes=scopes,
)
async def on_play_cmd(ctx: interactions.SlashContext, url: str):
    await play(url, ctx)


@interactions.slash_command(
    name="queue",
    description="Queue a song",
    options=[
        interactions.SlashCommandOption(
            name="url",
            description="The YouTube url of the song/playlist to queue",
            required=True,
            type=interactions.OptionType.STRING,
        ),
    ],
    scopes=scopes,
)
async def on_queue_cmd(ctx: interactions.SlashContext, url: str):
    await queue(url, ctx)


@interactions.slash_command(
    name="dequeue",
    description="Remove a song from the queue",
    options=[
        interactions.SlashCommandOption(
            name="song_number",
            description="The number of the song to dequeue",
            required=True,
            type=interactions.OptionType.INTEGER,
        ),
    ],
    scopes=scopes,
)
async def on_dequeue_cmd(ctx: interactions.SlashContext, song_number: int):
    await dequeue(ctx, song_number)


@interactions.slash_command(
    name="dequeue_next",
    description="Remove the next song from the queue",
    scopes=scopes,
)
async def on_dequeue_next_cmd(ctx: interactions.SlashContext):
    await dequeue_next(ctx)


@interactions.slash_command(
    name="dequeue_previous",
    description="Remove the previous song from the queue",
    scopes=scopes,
)
async def on_dequeue_previous_cmd(ctx: interactions.SlashContext):
    await dequeue_previous(ctx)


@interactions.slash_command(
    name="owner",
    description="Owner only commands",
    sub_cmd_name="reset_cache",
    sub_cmd_description="Reset all the bot's cache",
    scopes=scopes,
)
@interactions.check(interactions.is_owner())
async def on_reset_cache_cmd(ctx: interactions.SlashContext):
    await reset_cache(ctx)


@interactions.slash_command(
    name="owner",
    description="Owner only commands",
    sub_cmd_name="metrics",
    sub_cmd_description="Show the bot's metrics",
    scopes=scopes,
)
@interactions.check(interactions.is_owner())
async def on_metrics_cmd(ctx: interactions.SlashContext):
    await metrics(ctx)


@interactions.slash_command(
    name="stop",
    description="Stop the current song",
    scopes=scopes,
)
async def on_stop_cmd(ctx: interactions.SlashContext):
    await stop(ctx)


@interactions.slash_command(
    name="random",
    description="Play a random song",
    scopes=scopes,
)
async def on_random_cmd(ctx: interactions.SlashContext):
    await random_(ctx)


# NOTE: This has to be at the very bottom right after all commands 
#       have been registered by the decorators
def main():
    logger.debug("Starting bot")
    bot.start()


if __name__ == "__main__":
    main()
