# This is in __main__.py instead of main.py because otherwise the bot
# commands don't get registered


import interactions
from ytmusicbot.discord.common import (
    ButtonID,
    logger,
    DiscordException,
    bot,
    bot_restarted,
    make_bot,
    scopes,
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
    dequeue_current,
    stop,
    random_,
    skip_to,
    stop_bot,
    restart_bot,
    favourite,
    unfavourite,
    show_favourites,
    play_favourites,
)


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


@interactions.component_callback(ButtonID.favourite_rx)
async def on_favourite_cmp(ctx: interactions.ComponentContext):
    url_match = ButtonID.favourite_rx.match(ctx.custom_id)
    if not url_match:
        raise DiscordException("Invalid custom id")
    url = url_match.group(1)
    await favourite(url, ctx)


@interactions.component_callback(ButtonID.unfavourite_rx)
async def on_unfavourite_cmp(ctx: interactions.ComponentContext):
    url_match = ButtonID.unfavourite_rx.match(ctx.custom_id)
    if not url_match:
        raise DiscordException("Invalid custom id")
    url = url_match.group(1)
    await unfavourite(url, ctx)


@interactions.slash_command(
    name="show_favourites",
    description="Show your favourite songs",
    scopes=scopes,
)
async def on_show_favourites_cmd(ctx: interactions.SlashContext):
    await show_favourites(ctx)


@interactions.slash_command(
    name="play_favourites",
    description="Play your favourite songs",
    scopes=scopes,
)
async def on_play_favourites_cmd(ctx: interactions.SlashContext):
    await play_favourites(ctx)


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
            name="title_or_url",
            description="The YouTube title/url of the song/playlist to play",
            required=True,
            type=interactions.OptionType.STRING,
        ),
    ],
    scopes=scopes,
)
async def on_play_cmd(ctx: interactions.SlashContext, title_or_url: str):
    await play(title_or_url, ctx)


@interactions.slash_command(
    name="queue",
    description="Queue a song",
    options=[
        interactions.SlashCommandOption(
            name="title_or_url",
            description="The YouTube title/url of the song/playlist to queue",
            required=True,
            type=interactions.OptionType.STRING,
        ),
    ],
    scopes=scopes,
)
async def on_queue_cmd(ctx: interactions.SlashContext, title_or_url: str):
    await queue(title_or_url, ctx)


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
    name="dequeue_current",
    description="Remove the current song from the queue",
    scopes=scopes,
)
async def on_dequeue_current_cmd(ctx: interactions.SlashContext):
    await dequeue_current(ctx)


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


@interactions.slash_command(
    name="skip_to",
    description="Skip to a song in the queue",
    options=[
        interactions.SlashCommandOption(
            name="song_number",
            description="The number of the song to skip to",
            required=True,
            type=interactions.OptionType.INTEGER,
        ),
    ],
)
async def on_skip_to_cmd(ctx: interactions.SlashContext, song_number: int):
    await skip_to(ctx, song_number)


@interactions.slash_command(
    name="owner",
    description="Owner only commands",
    sub_cmd_name="stop_bot",
    sub_cmd_description="Stop the bot",
    scopes=scopes,
)
@interactions.check(interactions.is_owner())
async def on_stop_bot_cmd(ctx: interactions.SlashContext):
    await stop_bot(ctx)


@interactions.slash_command(
    name="owner",
    description="Owner only commands",
    sub_cmd_name="restart_bot",
    sub_cmd_description="Restart the bot",
    scopes=scopes,
)
@interactions.check(interactions.is_owner())
async def on_restart_bot_cmd(ctx: interactions.SlashContext):
    await restart_bot(ctx)


def main():
    global bot_restarted, bot
    logger.debug("Starting bot")
    bot.start()
    if bot_restarted[0]:
        logger.debug("Bot restarted")
        bot_restarted[0] = False
        bot = make_bot()
        main()


main()
