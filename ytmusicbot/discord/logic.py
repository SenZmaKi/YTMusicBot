import asyncio
import json
import os
import sys
from pathlib import Path
import random
import disnake
from ytmusicbot.discord.common import (
    logger,
    DiscordException,
    bot,
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
Context = disnake.ApplicationCommandInteraction | disnake.MessageInteraction
player: disnake.VoiceClient | None = None
playback_generation = 0
config = Config()
song_queue = SongQueue()
search_results = SearchResults()
discord_msg_limit = int(os.getenv("DISCORD_MSG_LIMIT", 2000))
PAGINATOR_PAGE_SIZE = 1500


async def send(
    ctx: Context,
    content: str | None = None,
    embed: disnake.Embed | None = None,
    components: list[disnake.ui.Button] | None = None,
    embeds: list[disnake.Embed] | None = None,
    file: disnake.File | None = None,
    ephemeral=False,
):
    if embed is not None and embeds is not None:
        raise ValueError("Only one of embed or embeds may be provided")

    content_debug = content[:100] if content else content
    view = None
    if components:
        view = disnake.ui.View(timeout=None)
        for component in components:
            view.add_item(component)
    if isinstance(ctx, disnake.MessageInteraction) and not ctx.response.is_done():
        logger.debug(f"Editing origin {content_debug=} {embed=} {components=}")
        kwargs = {}
        if content is not None:
            kwargs["content"] = content
        if embed is not None:
            kwargs["embed"] = embed
        elif embeds is not None:
            kwargs["embeds"] = embeds
        if view is not None:
            kwargs["view"] = view
        if file is not None:
            kwargs.update(file=file, attachments=[])
        await ctx.response.edit_message(**kwargs)
        return await ctx.original_response()
    else:
        logger.debug(f"Sending {content} {embed=} {components=}")
        sender = ctx.followup.send if ctx.response.is_done() else ctx.response.send_message
        kwargs = {"ephemeral": ephemeral}
        if content is not None:
            kwargs["content"] = content
        if view is not None:
            kwargs["view"] = view
        if embed is not None:
            kwargs["embed"] = embed
        elif embeds is not None:
            kwargs["embeds"] = embeds
        if file is not None:
            kwargs["file"] = file
        if ctx.response.is_done():
            kwargs["wait"] = True
            return await sender(**kwargs)
        await sender(**kwargs)
        return await ctx.original_response()


async def owner_send(ctx: Context, content: str):
    await send(ctx, content, ephemeral=True)


async def search(ctx: Context, query: str, max_results: int):
    logger.debug(f"Searching for {query}")
    await defer(ctx)
    results = await asyncio.to_thread(youtube.search, query, max_results)
    if not results:
        await send(ctx, "No results found")
        return

    search_results.extend(results)
    for result in results:
        url = result["url"]
        embed = song_embed_component(result)
        components = [play_button(url), queue_button(url)]
        await send(ctx, embed=embed, components=components)


async def send_error(ctx: Context, exception: Exception):
    logger.error(exception)
    embed = disnake.Embed(
        title="Error",
        description=f"{exception}",
        color=0xFF0000,
    )
    await send(ctx, embed=embed)


def get_author_voice_state(
    ctx: Context,
) -> disnake.VoiceState | None:
    return getattr(ctx.author, "voice", None)


async def handle_next_song(
    ctx: Context, voice_client: disnake.VoiceClient, generation: int
):
    logger.debug("Handling next song")
    global player
    if not player:
        return
    if voice_client != player or generation != playback_generation:
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
    ctx: Context,
    song: youtube.SongMetadata,
    file_path: Path,
    user_invoked=True,
):
    logger.debug(f"Playing {file_path}")
    global player, playback_generation
    author_voice_state = get_author_voice_state(ctx)

    if not author_voice_state:
        logger.debug("Author not in channel")
        if player and player.is_connected():
            if user_invoked:
                logger.debug(
                    f"Telling author to join {player.channel.name} voice channel"
                )
                await send(
                    ctx,
                    f"Please join `{player.channel.name}` voice channel first",
                )
            else:
                logger.debug("Author left channel, stopping player")
                await stop_player(True)
        else:
            if user_invoked:
                logger.debug("Telling author to join a voice channel")
                await send(ctx, "Please join a voice channel first")

        return

    channel = author_voice_state.channel
    logger.debug("Connecting to voice channel %s", channel.id)
    try:
        if player and player.is_connected():
            if player.channel != channel:
                await player.move_to(channel)
            voice_state = player
        else:
            voice_state = await asyncio.wait_for(channel.connect(), timeout=20)
    except TimeoutError as exc:
        raise DiscordException(
            "Discord voice connection timed out after 20 seconds. "
            "The song downloaded successfully, but the voice handshake failed. "
            "Check the bot's Connect/Speak permissions and voice-library compatibility."
        ) from exc
    logger.debug(f"Voice client {voice_state}")

    song_queue.current = song
    logger.debug(f"Current song: {song_queue.current}")
    audio = disnake.PCMVolumeTransformer(
        disnake.FFmpegPCMAudio(str(file_path)), volume=config.volume_audio
    )
    logger.debug(f"Volume audio: {config.volume_audio}")
    playback_generation += 1
    generation = playback_generation
    if voice_state.is_playing() or voice_state.is_paused():
        voice_state.stop()
    player = voice_state
    event_loop = asyncio.get_running_loop()

    def after_playback(error: Exception | None):
        if error:
            logger.error("Voice playback failed: %s", error)
        asyncio.run_coroutine_threadsafe(
            handle_next_song(ctx, voice_state, generation), event_loop
        )

    voice_state.play(audio, after=after_playback)
    await now_playing(ctx)


def append_to_queue(ctx: Context, song: youtube.SongMetadata):
    song_queue.append(song)
    if not song_queue.current:
        return
    if (
        song_queue.current["id"] != song_queue.next["id"]
        and song_queue.next["id"] == song["id"]
    ):
        download_then_play_thread(
            song_queue.next,
            ctx,
            asyncio.get_running_loop(),
            user_invoked=False,
            only_download=True,
        )


async def load_title_or_url(
    title_or_url: str, ctx: Context, should_show_queue: bool, should_defer=True
):

    if should_defer:
        await defer(ctx)
    id, is_playlist = youtube.get_id(title_or_url)
    if not id:
        results = youtube.search(title_or_url, max_results=1)
        if not results:
            await send(ctx, f'No results found for "{title_or_url}"')
            return
        search_results.extend(results)
        title_or_url = results[0]["url"]
        id, is_playlist = youtube.get_id(title_or_url)
        if not id:
            raise DiscordException(f"Invalid url {title_or_url}")
    if is_playlist:
        try:
            for idx, sm in enumerate(youtube.get_songs_in_playlist(title_or_url)):
                logger.debug(f"Appending {sm}")
                append_to_queue(ctx, sm)
                if idx == 0:
                    yield sm
        except youtube.YoutubeException as e:
            await send_error(ctx, e)
        else:
            if should_show_queue:
                await show_queue(ctx)

    else:
        song = search_results.get(id)
        if not song:
            try:
                song = youtube.get_song_metadata(title_or_url)
                search_results.append(song)
            except youtube.YoutubeException as e:
                await send_error(ctx, e)
                return
        append_to_queue(ctx, song)
        logger.debug(f"Added {song} to queue")
        yield song
        if should_show_queue:
            embed = song_embed_component(song).set_footer(text="Queued")
            await send(ctx, embed=embed)


async def play(title_or_url: str, ctx: Context):
    logger.debug(f"Play {title_or_url}")
    await clear_queue(ctx, is_user_invoked=False, disconnect_player=False)
    is_first = True
    async for song in load_title_or_url(title_or_url, ctx, should_show_queue=False):
        if is_first:
            is_first = False
            download_then_play_thread(
                song,
                ctx,
                asyncio.get_running_loop(),
            )


async def queue(title_or_url: str, ctx: Context):
    logger.debug(f"Queue {title_or_url}")
    async for _ in load_title_or_url(title_or_url, ctx, should_show_queue=True):
        pass


async def favourite(url: str, ctx: Context):
    logger.debug(f"Favourite {url}")
    async for song in load_title_or_url(url, ctx, should_show_queue=False, should_defer=False):
        config.append_favourite(song)
    await now_playing(ctx)


async def unfavourite(url: str, ctx: Context):
    logger.debug(f"Unfavourite {url}")
    config.remove_favourite(url)
    await now_playing(ctx)


async def show_favourites(ctx: Context):
    logger.debug("Show favourites")
    if not config.favourites:
        await send(ctx, "No favourites")
        return

    favourites_list = [
        f"**{i+1}.** {song['title']}" for i, song in enumerate(config.favourites)
    ]
    await send_lines(ctx, favourites_list)


async def play_favourites(ctx: Context):
    logger.debug("Play favourites")
    if not config.favourites:
        await send(ctx, "No favourites")
        return
    await defer(ctx)
    await clear_queue(ctx, is_user_invoked=False, disconnect_player=False)
    for song in config.favourites:
        append_to_queue(ctx, song)
    if not song_queue.current:
        return
    download_then_play_thread(song_queue.current, ctx, asyncio.get_running_loop())


async def pause(ctx: Context):
    logger.debug("Pause")
    if not player or player.is_paused() or not song_queue.current:
        await send(ctx, "No song is currently playing")
        return
    player.pause()
    await now_playing(ctx, "Paused")


async def defer(ctx: Context):
    if not ctx.response.is_done():
        await ctx.response.defer()


async def resume(ctx: Context):
    logger.debug("Resume")
    if song_queue.current:
        if player:
            if not player.is_paused():
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


async def send_volume_control(ctx: Context):
    text, buttons = volume_control_component(config)
    await send(ctx, text, components=buttons)


def set_player_current_audio_volume():
    if player and isinstance(player.source, disnake.PCMVolumeTransformer):
        player.source.volume = config.volume_audio


async def set_volume(ctx: Context, volume: int):
    if volume < 0 or volume > 100:
        await send(ctx, "Volume must be between 0% and 100%")
        return
    config.volume = volume
    set_player_current_audio_volume()
    await send_volume_control(ctx)


async def increase_volume(ctx: Context):
    if config.volume >= 100:
        await send(ctx, "Volume is already at maximum")
        return
    new_volume = config.volume + 10
    if new_volume > 100:
        new_volume = 100
    await set_volume(ctx, new_volume)


async def decrease_volume(ctx: Context):
    if config.volume <= 0:
        await send(ctx, "Volume is already at minimum")
        return
    new_volume = config.volume - 10
    if new_volume < 0:
        new_volume = 0
    await set_volume(ctx, new_volume)


async def mute(ctx: Context):
    logger.debug("Mute")
    if config.mute:
        await send(ctx, "Already muted")
        return
    config.mute = True
    set_player_current_audio_volume()
    await send_volume_control(ctx)


async def unmute(ctx: Context):
    logger.debug("Unmute")
    if not config.mute:
        await send(ctx, "Already unmuted")
        return
    config.mute = False
    set_player_current_audio_volume()
    await send_volume_control(ctx)


async def next_(ctx: Context, user_invoked=True):
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


async def previous(ctx: Context):
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
    global player, playback_generation
    if not player:
        return
    player_buffer = player
    player = None
    playback_generation += 1
    if player_buffer:
        player_buffer.stop()
        if disconnect and player_buffer.is_connected():
            await player_buffer.disconnect(force=True)


async def clear_queue(
    ctx: Context, is_user_invoked=True, disconnect_player=True
):
    logger.debug("Clear queue")
    if not song_queue.current and is_user_invoked:
        await send(ctx, "Queue is empty")
        return
    await stop_player(disconnect_player)
    song_queue.clear()
    if is_user_invoked:
        await send(ctx, "Queue cleared")


async def send_lines(ctx: Context, lines: list[str]):
    pages: list[str] = []
    page = ""
    for line in lines:
        candidate = f"{page}\n{line}" if page else line
        if len(candidate) > PAGINATOR_PAGE_SIZE:
            pages.append(page)
            page = line
        else:
            page = candidate
    if page:
        pages.append(page)
    for page in pages:
        await send(ctx, page)


async def show_queue(ctx: Context):
    logger.debug("Show queue")
    if not song_queue.current:
        await send(ctx, "Queue is empty")
        return

    if not player:
        playback_status = "⏹️"
    elif player.is_paused():
        playback_status = "⏸️"
    else:
        playback_status = "▶️"
    queue_list = [
        f"***{playback_status} {song['title']}***"
        if i == song_queue.current_index
        else f"**{i+1}.** {song['title']}"
        for i, song in enumerate(song_queue.queue)
    ]
    await send_lines(ctx, queue_list)


async def loop(ctx: Context):
    logger.debug("Loop")
    config.loop = True
    await now_playing(ctx)


async def unloop(ctx: Context):
    logger.debug("Unloop")
    config.loop = False
    await now_playing(ctx)


async def shuffle(ctx: Context):
    logger.debug("Shuffle")
    song_queue.shuffle()
    await show_queue(ctx)


async def is_valid_song_number(
    ctx: Context, song_number: int
) -> bool:
    if song_number < 1 or song_number > len(song_queue.queue):
        await send(ctx, "Invalid song number")
        await show_queue(ctx)
        return False
    return True


async def dequeue(ctx: Context, song_number: int):
    logger.debug(f"Dequeue {song_number}")
    if not song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    index = song_number - 1
    was_playing = player is not None and player.is_playing()
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


async def dequeue_next(ctx: Context):
    logger.debug("Dequeue next")
    await dequeue(ctx, song_queue.next_index + 1)


async def dequeue_previous(ctx: Context):
    logger.debug("Dequeue previous")
    await dequeue(ctx, song_queue.previous_index + 1)


async def dequeue_current(ctx: Context):
    logger.debug("Dequeue current")
    await dequeue(ctx, song_queue.current_index + 1)


async def now_playing(
    ctx: Context,
    footer="Now playing",
):
    logger.debug("Now playing")
    if not song_queue.current or not player:
        await send(ctx, "No song is currently playing")
        return
    song = song_queue.current
    embed, buttons = now_playing_component(song, player, config, footer)
    await send(
        ctx,
        embed=embed,
        components=buttons,
    )


async def stop(ctx: Context):
    logger.debug("Stop")
    if not player:
        await send(ctx, "No song is currently playing")
        return

    await stop_player(True)
    await send(ctx, "Stopped the current song")


async def repo(ctx: Context):
    logger.debug("Repo")
    await send(ctx, f"You can find the source code for this bot at {REPO}")


async def creator(ctx: Context):
    logger.debug("Creator")
    await send(
        ctx,
        f"You can find the creator, {CREATOR_NAME}, on discord at {CREATOR_DISCORD_CHAT_URL}",
    )


async def reset_cache(ctx: Context):
    logger.debug("Reset cache")
    await stop_player(True)
    for cache in Cache.all:
        logger.debug(f"Resetting {cache.name}")
        await owner_send(ctx, f"Resetting {cache.name}")
        cache.reset()
    await owner_send(ctx, "Successfully reset all caches")


async def metrics(ctx: Context):
    logger.debug("Metrics")
    folder_metrics = youtube.download_folder_metrics()
    content = f"Downloads folder size: {folder_metrics.size_mbs:.2f} MB\nSize limit: {folder_metrics.size_limit_mbs} MB\nTotal downloads: {folder_metrics.total_downloads}"
    await owner_send(
        ctx,
        content=content,
    )


async def skip_to(ctx: Context, song_number: int):
    logger.debug(f"Skip to {song_number}")
    if not song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    await stop_player(False)
    song_queue.current_index = song_number - 1
    await resume(ctx)


async def random_(ctx: Context):
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


async def stop_bot(ctx: Context):
    logger.debug("Stop bot")
    await owner_send(ctx, "Stopping bot")
    await stop_player(True)
    await bot.close()


async def restart_bot(ctx: Context):
    logger.debug("Restart bot")
    await owner_send(ctx, "Restarting bot")
    await stop_player(True)
    await bot.close()
    os.execv(sys.executable, [sys.executable, *sys.argv])


def download_then_play_thread(
    song: youtube.SongMetadata,
    ctx: Context,
    event_loop: asyncio.AbstractEventLoop,
    only_download=False,
    user_invoked=True,
):
    async def download_and_play():
        try:
            file_path, metadata = await asyncio.to_thread(
                youtube.download_single, song["url"], song["id"]
            )
            if not only_download:
                await play_song_in_voice_channel(
                    ctx, metadata, file_path=file_path, user_invoked=user_invoked
                )
        except Exception as exc:
            logger.exception("Download or playback failed for %s", song["id"])
            if user_invoked and not only_download:
                try:
                    await send_error(ctx, exc)
                except Exception:
                    logger.exception("Could not send playback error to Discord")

    return asyncio.run_coroutine_threadsafe(download_and_play(), event_loop)
