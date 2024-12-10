import asyncio
import json
import os
from pathlib import Path
import random
import sys
import threading
import traceback
from typing import cast
import interactions
from interactions.api.voice.audio import AudioVolume
from interactions.api.voice.player import Player
from ytmusicbot.discord.common import (
    logger,
    DiscordException,
    bot,
    bot_restarted,
)
from ytmusicbot.discord.components import (
    play_button,
    queue_button,
    song_embed_component,
    now_playing_component,
    volume_control_component,
)
from ytmusicbot.discord.caches import Config, SearchResults, SongQueue
import ytmusicbot.youtube as youtube
from ytmusicbot.common.main import REPO, CREATOR_NAME, CREATOR_DISCORD_CHAT_URL, Cache

player: Player | None = None
config = Config()
song_queue = SongQueue()
search_results = SearchResults()
discord_msg_limit = int(os.getenv("DISCORD_MSG_LIMIT", 2000))


async def send(
    ctx: interactions.InteractionContext,
    content: str | None = None,
    embed: interactions.Embed | None = None,
    components: list[interactions.Button] | None = None,
    embeds: list[interactions.Embed] | None = None,
    ephemeral=False,
):
    if (
        not ctx.responded
        and isinstance(ctx, interactions.ComponentContext)
        and components
    ):
        await ctx.edit_origin(content=content, embed=embed, components=components)
    else:
        await ctx.send(
            content=content,
            embed=embed,
            components=components,
            embeds=embeds,
            ephemeral=ephemeral,
        )


async def owner_send(ctx: interactions.InteractionContext, content: str):
    await send(ctx, content, ephemeral=True)


async def search(ctx: interactions.InteractionContext, query: str, max_results: int):
    logger.debug(f"Searching for {query}")
    results = youtube.search(query, max_results)
    if not results:
        await send(ctx, "No results found")

    search_results.extend(results)
    for result in results:
        url = result["url"]
        embed = song_embed_component(result)
        components = [play_button(url), queue_button(url)]
        await send(ctx, embed=embed, components=components)


def split_into_chunks(message: str, limit: int) -> list[str]:
    """
    Splits a message into chunks while respecting the character limit.
    """
    chunks = []
    while len(message) > limit:
        # Find the last newline before the limit
        split_index = message.rfind("\n", 0, limit)
        if split_index == -1:  # No newline found, split at the limit
            split_index = limit
        chunks.append(message[:split_index])
        message = message[split_index:]
    if message:
        chunks.append(message)
    return chunks


async def send_error(ctx: interactions.InteractionContext, exception: Exception):
    logger.error(exception)
    trace = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    msg_formatter = "```\n{}\n```"
    limit = discord_msg_limit - len(msg_formatter.format(""))
    chunks = split_into_chunks(trace, limit)
    for chunk in chunks:
        formatted_chunk = msg_formatter.format(chunk)
        embed = interactions.Embed(
            title=f"Error Occurred: {exception.__class__.__name__}",
            description=formatted_chunk,
            color=0xFF0000,
        )
        await send(ctx, embed=embed)


def get_author_voice_state(
    ctx: interactions.InteractionContext,
) -> interactions.VoiceState | None:
    if isinstance(ctx.author, interactions.User):
        raise DiscordException("Author is User instead of Member")

    author_voice_state = ctx.author.voice
    return author_voice_state


async def handle_next_song(ctx: interactions.InteractionContext):
    logger.debug("Handling next song")
    global player
    if not player:
        return
    player_buffer = player
    download_then_play_thread(
        song_queue.next, ctx, asyncio.get_running_loop(), only_download=True
    )
    await player_buffer._stopped.wait()
    if player_buffer != player:
        logger.debug("Player changed")
        return
    if config.loop:
        logger.debug("Looping")
        if not song_queue.current:
            return
        download_then_play_thread(
            song_queue.current,
            ctx,
            asyncio.get_running_loop(),
            user_invoked=False,
        )
    else:
        await next_(ctx, user_invoked=False)


async def play_song_in_voice_channel(
    ctx: interactions.InteractionContext,
    song_metadata: youtube.SongMetadata,
    file_path: Path,
    user_invoked=True,
):
    logger.debug(f"Playing {file_path}")
    global player
    if player and not player.stopped:
        return
    if isinstance(ctx.author, interactions.User):
        raise DiscordException("Author is User instead of Member")

    author_voice_state = get_author_voice_state(ctx)

    if not author_voice_state:
        logger.debug("Author not in channel")
        if player and player.state.connected:
            if user_invoked:
                logger.debug(
                    f"Telling author to join {player.state.channel.name} voice channel"
                )
                await send(
                    ctx,
                    f"Please join `{player.state.channel.name}` voice channel first",
                )
            else:
                logger.debug("Author left channel, stopping player")
                await stop_player(True)
        else:
            if user_invoked:
                logger.debug("Telling author to join a voice channel")
                await send(ctx, "Please join a voice channel first")

        return

    voice_state = await author_voice_state.channel.connect()
    logger.debug(f"Voice state {voice_state}")

    song_queue.current = song_metadata
    logger.debug(f"Current song: {song_queue.current}")
    audio = AudioVolume(file_path)
    logger.debug(f"Volume audio: {config.volume_audio}")
    await stop_player(disconnect=False)
    voice_state = ctx.voice_state
    player = Player(audio=audio, v_state=voice_state, loop=asyncio.get_running_loop())
    player.play()
    asyncio.create_task(handle_next_song(ctx))
    # Volume can only be set after the player is playing for some reason
    set_player_current_audio_volume()
    await now_playing(ctx)


def append_to_queue(
    ctx: interactions.InteractionContext, song_metadata: youtube.SongMetadata
):
    song_queue.append(song_metadata)
    if not song_queue.current:
        return
    if (
        song_queue.current["id"] != song_queue.next["id"]
        and song_queue.next["id"] == song_metadata["id"]
    ):
        download_then_play_thread(
            song_queue.next,
            ctx,
            asyncio.get_running_loop(),
            user_invoked=False,
            only_download=True,
        )


async def load_url(url: str, ctx: interactions.InteractionContext):
    id, is_playlist = youtube.get_id(url)
    if not id:
        await send(ctx, "Invalid YouTube url")
        return
    if is_playlist:
        await defer(ctx)
        try:
            for idx, sm in enumerate(youtube.get_songs_in_playlist(url)):
                logger.debug(f"Appending {sm}")
                append_to_queue(ctx, sm)
                if idx == 0:
                    yield sm
        except youtube.YoutubeException as e:
            await send_error(ctx, e)
        else:
            await show_queue(ctx)

    else:
        song_metadata = search_results.get(id)
        if not song_metadata:
            await defer(ctx)
            try:
                song_metadata = youtube.get_song_metadata(url)
                search_results.append(song_metadata)
            except youtube.YoutubeException as e:
                await send_error(ctx, e)
                return
        append_to_queue(ctx, song_metadata)
        logger.debug(f"Added {song_metadata} to queue")
        yield song_metadata
        embed = song_embed_component(song_metadata).set_footer(text="Queued")
        await send(ctx, embed=embed)


async def play(url: str, ctx: interactions.InteractionContext):
    logger.debug(f"Playing {url}")
    song_queue.clear()
    is_first = True
    async for song_metadata in load_url(url, ctx):
        if is_first:
            is_first = False
            download_then_play_thread(
                song_metadata,
                ctx,
                asyncio.get_running_loop(),
            )


async def queue(url: str, ctx: interactions.InteractionContext):
    logger.debug(f"Queueing {url}")
    async for _ in load_url(url, ctx):
        pass


async def pause(ctx: interactions.InteractionContext):
    logger.debug("Pausing")
    if not player or player.paused or not song_queue.current:
        await send(ctx, "No song is currently playing")
        return
    player.pause()
    await now_playing(ctx, "Paused")


async def defer(ctx: interactions.InteractionContext):
    if not ctx.deferred and not ctx.responded:
        await ctx.defer()


async def resume(ctx: interactions.InteractionContext):
    logger.debug("Resuming")
    if song_queue.current:
        if player:
            if not player.paused:
                await send(ctx, "Already playing")
                return
            player.resume()
        else:
            await defer(ctx)
            download_then_play_thread(
                song_queue.current,
                ctx,
                asyncio.get_running_loop(),
            )
            return
    else:
        await send(ctx, "Queue is empty")
        return
    author_voice_state = get_author_voice_state(ctx)
    if author_voice_state:
        await now_playing(ctx)


async def send_volume_control(ctx: interactions.InteractionContext):
    text, buttons = volume_control_component(config)
    await send(ctx, text, components=buttons)


def set_player_current_audio_volume():
    global player
    if player and player.current_audio:
        player.current_audio = cast(AudioVolume, player.current_audio)
        player.current_audio.volume = config.volume_audio


async def set_volume(ctx: interactions.InteractionContext, volume: int):
    if volume < 0 or volume > 100:
        await send(ctx, "Volume must be between 0% and 100%")
        return
    config.volume = volume
    set_player_current_audio_volume()
    await send_volume_control(ctx)


async def increase_volume(ctx: interactions.InteractionContext):
    if config.volume >= 100:
        await send(ctx, "Volume is already at maximum")
        return
    new_volume = config.volume + 10
    if new_volume > 100:
        new_volume = 100
    await set_volume(ctx, new_volume)


async def decrease_volume(ctx: interactions.InteractionContext):
    if config.volume <= 0:
        await send(ctx, "Volume is already at minimum")
        return
    new_volume = config.volume - 10
    if new_volume < 0:
        new_volume = 0
    await set_volume(ctx, new_volume)


async def mute(ctx: interactions.InteractionContext):
    if config.mute:
        await send(ctx, "Already muted")
        return
    config.mute = True
    set_player_current_audio_volume()
    await send_volume_control(ctx)


async def unmute(ctx: interactions.InteractionContext):
    if not config.mute:
        await send(ctx, "Already unmuted")
        return
    config.mute = False
    if player and player.current_audio:
        player.current_audio.volume = config.volume_audio  # type: ignore
    await send_volume_control(ctx)


async def next_(ctx: interactions.InteractionContext, user_invoked=True):
    logger.debug("Next")
    if not song_queue.current:
        if user_invoked:
            await send(ctx, "No song in queue")
        return
    if user_invoked and not youtube.downloads.get(song_queue.next["id"]):
        await defer(ctx)
    download_then_play_thread(
        song_queue.next,
        ctx,
        asyncio.get_running_loop(),
        user_invoked=user_invoked,
    )


async def previous(ctx: interactions.InteractionContext):
    logger.debug("Previous")
    if not song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not youtube.downloads.get(song_queue.previous["id"]):
        await defer(ctx)
    download_then_play_thread(
        song_queue.previous,
        ctx,
        asyncio.get_running_loop(),
    )


async def stop_player(disconnect: bool):
    logger.debug("Stopping player")
    global player
    if not player:
        return
    player_buffer = player
    player = None
    if player_buffer:
        player_buffer.stop()
        if disconnect and player_buffer.state.connected:
            await player_buffer.state.disconnect()


async def clear_queue(ctx: interactions.InteractionContext):
    logger.debug("Clearing queue")
    if not song_queue.current:
        await send(ctx, "Queue is empty")
        return
    await stop_player(True)
    song_queue.clear()
    await send(ctx, "Queue cleared")


async def show_queue(ctx: interactions.InteractionContext):
    logger.debug("Showing queue")
    if not song_queue.current:
        await send(ctx, "Queue is empty")
        return

    if not player:
        playback_status = "⏹️"
    elif player.paused:
        playback_status = "⏸️"
    else:
        playback_status = "▶️"
    queue_str = "\n".join(
        f"***{playback_status} {song['title']}***"
        if i == song_queue.current_index
        else f"**{i+1}.** _{song['title']}_"
        for i, song in enumerate(song_queue.queue)
    )
    chunks = split_into_chunks(queue_str, discord_msg_limit)
    for chunk in chunks:
        await send(ctx, chunk)


async def loop(ctx: interactions.InteractionContext):
    logger.debug("Looping")
    config.loop = True
    await now_playing(ctx)


async def unloop(ctx: interactions.InteractionContext):
    logger.debug("Unlooping")
    config.loop = False
    await now_playing(ctx)


async def shuffle(ctx: interactions.InteractionContext):
    logger.debug("Shuffling")
    song_queue.shuffle()
    await show_queue(ctx)


async def is_valid_song_number(
    ctx: interactions.InteractionContext, song_number: int
) -> bool:
    if song_number < 1 or song_number > len(song_queue.queue):
        await send(ctx, "Invalid song number")
        await show_queue(ctx)
        return False
    return True


async def dequeue(ctx: interactions.InteractionContext, song_number: int):
    logger.debug(f"Dequeuing {song_number}")
    if not song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    index = song_number - 1
    was_playing = player is not None and not player.paused
    should_resume = False
    if index == song_queue.current_index:
        if len(song_queue.queue) > 1:
            should_resume = True
            await stop_player(False)
        else:
            await stop_player(True)
    song_queue.dequeue(index)
    await show_queue(ctx)
    if was_playing and should_resume:
        await resume(ctx)


async def dequeue_next(ctx: interactions.InteractionContext):
    logger.debug("Dequeuing next")
    await dequeue(ctx, song_queue.next_index + 1)


async def dequeue_previous(ctx: interactions.InteractionContext):
    logger.debug("Dequeuing previous")
    await dequeue(ctx, song_queue.previous_index + 1)


async def dequeue_current(ctx: interactions.InteractionContext):
    logger.debug("Dequeuing current")
    await dequeue(ctx, song_queue.current_index + 1)


async def now_playing(
    ctx: interactions.InteractionContext,
    footer="Now playing",
):
    logger.debug("Showing now playing")
    if not song_queue.current or not player:
        await send(ctx, "No song is currently playing")
        return
    embed, buttons = now_playing_component(song_queue.current, player, config, footer)
    await send(
        ctx,
        embed=embed,
        components=buttons,
    )


async def stop(ctx: interactions.InteractionContext):
    logger.debug("Stopping")
    if not player:
        await send(ctx, "No song is currently playing")
        return

    await stop_player(True)
    await ctx.send("Stopped the current song")


async def repo(ctx: interactions.InteractionContext):
    logger.debug("Repo")
    await send(ctx, f"You can find the source code for this bot at {REPO}")


async def creator(ctx: interactions.InteractionContext):
    logger.debug("Creator")
    await send(
        ctx,
        f"You can find the creator, {CREATOR_NAME} on discord at {CREATOR_DISCORD_CHAT_URL}",
    )


async def reset_cache(ctx: interactions.InteractionContext):
    logger.debug("Resetting cache")
    await stop_player(True)
    for cache in Cache.all:
        logger.debug(f"Resetting {cache.name}")
        await owner_send(ctx, f"Resetting {cache.name}")
        cache.reset()
    await owner_send(ctx, "Successfully reset all caches")


async def metrics(ctx: interactions.InteractionContext):
    logger.debug("Showing metrics")
    folder_metrics = youtube.download_folder_metrics()
    content = f"Downloads folder size: {folder_metrics.size_mbs:.2f} MB\nSize limit: {folder_metrics.size_limit_mbs} MB\nTotal downloads: {folder_metrics.total_downloads}"
    await owner_send(
        ctx,
        content=content,
    )


async def skip_to(ctx: interactions.InteractionContext, song_number: int):
    logger.debug(f"Skipping to {song_number}")
    if not song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    await stop_player(False)
    song_queue.current_index = song_number - 1
    await resume(ctx)


async def random_(ctx: interactions.InteractionContext):
    logger.debug("Random")
    await defer(ctx)
    all_songs: list[youtube.SongMetadata] = []
    for file in youtube.randoms_songs_dir.iterdir():
        with open(file, "r") as f:
            songs = json.load(f)
            all_songs.extend(songs)
    if not all_songs:
        await send(ctx, "No random songs available")
        return
    random.shuffle(all_songs)
    songs = all_songs[:50]
    song_queue.clear()
    song_queue.extend(songs)
    search_results.extend(songs)
    await stop_player(False)
    await resume(ctx)


async def stop_bot(ctx: interactions.InteractionContext):
    logger.debug("Stopping bot")
    await owner_send(ctx, "Stopping bot")
    await stop_player(True)
    await bot.stop()


async def restart_bot(ctx: interactions.InteractionContext):
    logger.debug("Restarting bot")
    global bot_restarted
    bot_restarted[0] = True
    await owner_send(ctx, "Restarting bot")
    await stop_bot(ctx)


def download_then_play_thread(
    song_metadata: youtube.SongMetadata,
    ctx: interactions.InteractionContext,
    event_loop: asyncio.AbstractEventLoop,
    only_download=False,
    user_invoked=True,
):
    def thread_func():
        nonlocal song_metadata
        try:
            file_path, song_metadata = youtube.download_single(
                song_metadata["url"], song_metadata["id"]
            )
        except youtube.YoutubeException as e:
            asyncio.run_coroutine_threadsafe(
                send_error(ctx, e),
                event_loop,
            )
        else:
            if not only_download:
                asyncio.run_coroutine_threadsafe(
                    play_song_in_voice_channel(
                        ctx,
                        song_metadata,
                        file_path=file_path,
                        user_invoked=user_invoked,
                    ),
                    event_loop,
                )

    thread = threading.Thread(target=thread_func)
    thread.start()
