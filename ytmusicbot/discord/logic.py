import asyncio
import json
import os
import sys
import time
from pathlib import Path
import random
from dataclasses import dataclass, field
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
from ytmusicbot.discord.progress import render_progress
import ytmusicbot.youtube as youtube
from ytmusicbot.common.main import REPO, CREATOR_NAME, CREATOR_DISCORD_CHAT_URL, Cache

Context = disnake.ApplicationCommandInteraction | disnake.MessageInteraction


@dataclass
class PlaybackSession:
    guild_id: int
    config: Config = field(init=False)
    song_queue: SongQueue = field(init=False)
    player: disnake.VoiceClient | None = None
    playback_generation: int = 0
    request_generation: int = 0
    playback_started_at: float = 0.0
    playback_paused_at: float | None = None
    playback_paused_total: float = 0.0
    progress_message: disnake.Message | None = None
    progress_task: asyncio.Task | None = None
    playback_task: asyncio.Task | None = None
    transition_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    text_channel_id: int | None = None

    def __post_init__(self):
        namespace = str(self.guild_id)
        self.config = Config(namespace)
        self.song_queue = SongQueue(namespace)


sessions: dict[int, PlaybackSession] = {}
search_results = SearchResults()
discord_msg_limit = int(os.getenv("DISCORD_MSG_LIMIT", 2000))
PAGINATOR_PAGE_SIZE = 1500


def get_session(ctx: Context) -> PlaybackSession:
    guild_id = getattr(ctx, "guild_id", None)
    if guild_id is None and getattr(ctx, "guild", None):
        guild_id = ctx.guild.id
    if guild_id is None:
        raise DiscordException("Playback commands can only be used in a server")
    session = sessions.get(guild_id)
    if session is None:
        session = sessions[guild_id] = PlaybackSession(guild_id)
    channel_id = getattr(ctx, "channel_id", None)
    if channel_id:
        session.text_channel_id = channel_id
    return session


async def send_session(session: PlaybackSession, content=None, **kwargs):
    """Send without relying on an interaction token that may have expired."""
    if session.text_channel_id is None:
        return None
    channel = bot.get_channel(session.text_channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(session.text_channel_id)
        except Exception:
            logger.exception("Could not resolve playback status channel")
            return None
    try:
        return await channel.send(content=content, **kwargs)
    except Exception:
        logger.exception("Could not send playback status")
        return None


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
        # A component response represents the complete new state of that
        # message. Explicitly clear stale content, embeds, controls and files.
        kwargs = {"content": content, "view": view}
        if embed is not None:
            kwargs["embed"] = embed
        elif embeds is not None:
            kwargs["embeds"] = embeds
        else:
            kwargs["embed"] = None
        if file is not None:
            kwargs.update(file=file, attachments=[])
        else:
            kwargs["attachments"] = []
        await ctx.response.edit_message(**kwargs)
        return await ctx.original_response()
    else:
        logger.debug(f"Sending {content} {embed=} {components=}")
        sender = (
            ctx.followup.send if ctx.response.is_done() else ctx.response.send_message
        )
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


async def search(
    ctx: Context,
    query: str,
    max_results: int,
    include_playlists: bool = False,
):
    logger.debug(f"Searching for {query}")
    await defer(ctx)
    results = await asyncio.to_thread(
        youtube.search, query, max_results, include_playlists
    )
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
    session: PlaybackSession, voice_client: disnake.VoiceClient, generation: int
):
    logger.debug("Handling next song")
    if not session.player:
        return
    if voice_client != session.player or generation != session.playback_generation:
        logger.debug("Player changed")
        return
    if session.config.repeat_mode == "song":
        logger.debug("Looping")
        if not session.song_queue.current:
            return
        start_song(session, session.song_queue.current, user_invoked=False)
    else:
        next_index = session.song_queue.current_index + 1
        if next_index >= len(session.song_queue.queue):
            if session.config.repeat_mode == "queue":
                session.song_queue.current_index = 0
                start_song(session, session.song_queue.current, user_invoked=False)
                return
            await stop_player(session, True)
            session.song_queue.clear()
            await send_session(session, "Queue finished")
            return
        session.song_queue.current_index = next_index
        start_song(session, session.song_queue.current, user_invoked=False)


async def play_song_in_voice_channel(
    ctx: Context | None,
    session: PlaybackSession,
    song: youtube.SongMetadata,
    file_path: Path,
    user_invoked=True,
):
    logger.debug(f"Playing {file_path}")
    author_voice_state = get_author_voice_state(ctx) if ctx is not None else None

    if ctx is not None and not author_voice_state:
        logger.debug("Author not in channel")
        if session.player and session.player.is_connected():
            if user_invoked:
                logger.debug(
                    f"Telling author to join {session.player.channel.name} voice channel"
                )
                await send(
                    ctx,
                    f"Please join `{session.player.channel.name}` voice channel first",
                )
            else:
                logger.debug("Author left channel, stopping player")
                await stop_player(session, True)
        else:
            if user_invoked:
                logger.debug("Telling author to join a voice channel")
                await send(ctx, "Please join a voice channel first")

        return

    channel = (
        author_voice_state.channel if author_voice_state else session.player.channel
    )
    logger.debug("Connecting to voice channel %s", channel.id)
    try:
        # stop_player(disconnect=False) invalidates session.player so stale
        # callbacks cannot advance the queue, but Discord still owns a live
        # guild voice client. Reuse it instead of attempting a second connect.
        guild_voice_client = getattr(getattr(ctx, "guild", None), "voice_client", None)
        existing_voice_client = session.player or guild_voice_client
        if existing_voice_client and existing_voice_client.is_connected():
            if existing_voice_client.channel != channel:
                await existing_voice_client.move_to(channel)
            voice_state = existing_voice_client
        else:
            voice_state = await asyncio.wait_for(channel.connect(), timeout=20)
    except TimeoutError as exc:
        raise DiscordException(
            "Discord voice connection timed out after 20 seconds. "
            "The song downloaded successfully, but the voice handshake failed. "
            "Check the bot's Connect/Speak permissions and voice-library compatibility."
        ) from exc
    logger.debug(f"Voice client {voice_state}")

    if not song.get("duration"):
        duration = await asyncio.to_thread(youtube.get_media_duration, file_path)
        if duration:
            song["duration"] = duration
    session.song_queue.current = song
    logger.debug(f"Current song: {session.song_queue.current}")
    audio = disnake.PCMVolumeTransformer(
        disnake.FFmpegPCMAudio(str(file_path)), volume=session.config.volume_audio
    )
    logger.debug(f"Volume audio: {session.config.volume_audio}")
    session.playback_generation += 1
    generation = session.playback_generation
    session.playback_started_at = time.monotonic()
    session.playback_paused_at = None
    session.playback_paused_total = 0.0
    if voice_state.is_playing() or voice_state.is_paused():
        voice_state.stop()
    session.player = voice_state
    event_loop = asyncio.get_running_loop()

    def after_playback(error: Exception | None):
        if error:
            logger.error("Voice playback failed: %s", error)
        asyncio.run_coroutine_threadsafe(
            handle_next_song(session, voice_state, generation), event_loop
        )

    voice_state.play(audio, after=after_playback)
    try:
        if user_invoked and ctx is not None:
            await now_playing(ctx)
        else:
            await publish_now_playing(session)
    except Exception:
        # Status delivery must never be mistaken for an audio failure. Playback
        # has already started at this point.
        logger.exception("Could not publish now-playing status")


def append_to_queue(ctx: Context, song: youtube.SongMetadata):
    session = get_session(ctx)
    session.song_queue.append(song)
    if not session.song_queue.current:
        return
    if (
        session.song_queue.current["id"] != session.song_queue.next["id"]
        and session.song_queue.next["id"] == song["id"]
    ):
        asyncio.create_task(prefetch_song(session.song_queue.next))


async def prefetch_song(song: youtube.SongMetadata):
    try:
        await asyncio.to_thread(youtube.download_single, song["url"], song["id"])
    except Exception:
        # Prefetch is only an optimization; start_song will retry and report a
        # useful error if this track is actually reached.
        logger.exception("Could not prefetch %s", song["id"])


async def resolve_songs(title_or_url: str) -> list[youtube.SongMetadata]:
    id, is_playlist = youtube.get_id(title_or_url)
    if not id:
        results = await asyncio.to_thread(youtube.search, title_or_url, 1)
        if not results:
            raise DiscordException(f'No results found for "{title_or_url}"')
        search_results.extend(results)
        title_or_url = results[0]["url"]
        id, is_playlist = youtube.get_id(title_or_url)
        if not id:
            raise DiscordException(f"Invalid url {title_or_url}")
    if is_playlist:
        songs = await asyncio.to_thread(
            lambda: list(youtube.get_songs_in_playlist(title_or_url))
        )
        search_results.extend(songs)
        return songs
    song = search_results.get(id)
    if not song:
        song = await asyncio.to_thread(youtube.get_song_metadata, title_or_url)
        search_results.append(song)
    return [song]


async def play(title_or_url: str, ctx: Context):
    logger.debug(f"Play {title_or_url}")
    session = get_session(ctx)
    session.request_generation += 1
    intent_generation = session.request_generation
    await defer(ctx)
    songs = await resolve_songs(title_or_url)
    file_path, metadata = await asyncio.to_thread(
        youtube.download_single, songs[0]["url"], songs[0]["id"]
    )
    if intent_generation != session.request_generation:
        return
    await stop_player(session, False)
    session.song_queue.clear()
    session.song_queue.extend(songs)
    await play_song_in_voice_channel(
        ctx, session, metadata, file_path, user_invoked=True
    )


async def queue(title_or_url: str, ctx: Context):
    logger.debug(f"Queue {title_or_url}")
    await defer(ctx)
    songs = await resolve_songs(title_or_url)
    for song in songs:
        append_to_queue(ctx, song)
    if len(songs) == 1:
        embed = song_embed_component(songs[0]).set_footer(text="Queued")
        await send(ctx, embed=embed)
    else:
        await show_queue(ctx)


async def favourite(url: str, ctx: Context):
    logger.debug(f"Favourite {url}")
    session = get_session(ctx)
    songs = await resolve_songs(url)
    for song in songs:
        session.config.append_favourite(song)
    if session.player and session.song_queue.current:
        await now_playing(ctx)
    else:
        await send(ctx, f"Added **{songs[0]['title']}** to favourites")


async def unfavourite(url: str, ctx: Context):
    logger.debug(f"Unfavourite {url}")
    get_session(ctx).config.remove_favourite(url)
    session = get_session(ctx)
    if session.player and session.song_queue.current:
        await now_playing(ctx)
    else:
        await send(ctx, "Removed from favourites")


async def show_favourites(ctx: Context):
    logger.debug("Show favourites")
    config = get_session(ctx).config
    if not config.favourites:
        await send(ctx, "No favourites")
        return

    favourites_list = [
        f"**{i + 1}.** {song['title']}" for i, song in enumerate(config.favourites)
    ]
    await send_lines(ctx, favourites_list)


async def play_favourites(ctx: Context):
    logger.debug("Play favourites")
    session = get_session(ctx)
    if not session.config.favourites:
        await send(ctx, "No favourites")
        return
    await defer(ctx)
    await stop_player(session, False)
    session.song_queue.clear()
    for song in session.config.favourites:
        append_to_queue(ctx, song)
    if not session.song_queue.current:
        return
    start_song(session, session.song_queue.current, ctx=ctx)


async def pause(ctx: Context):
    logger.debug("Pause")
    session = get_session(ctx)
    if (
        not session.player
        or not session.player.is_playing()
        or session.player.is_paused()
        or not session.song_queue.current
    ):
        await send(ctx, "No song is currently playing")
        return
    session.player.pause()
    session.playback_paused_at = time.monotonic()
    await now_playing(ctx, "Paused")


async def defer(ctx: Context):
    if not ctx.response.is_done():
        await ctx.response.defer()


async def resume(ctx: Context):
    logger.debug("Resume")
    session = get_session(ctx)
    if session.song_queue.current:
        if session.player and (
            session.player.is_playing() or session.player.is_paused()
        ):
            if not session.player.is_paused():
                await send(ctx, "Already playing")
                return
            session.player.resume()
            if session.playback_paused_at is not None:
                session.playback_paused_total += (
                    time.monotonic() - session.playback_paused_at
                )
                session.playback_paused_at = None
        else:
            await defer(ctx)
            start_song(session, session.song_queue.current, ctx=ctx)
            return
    else:
        await send(ctx, "Queue is empty")
        return
    author_voice_state = get_author_voice_state(ctx)
    if author_voice_state:
        await now_playing(ctx)


async def send_volume_control(ctx: Context):
    text, buttons = volume_control_component(get_session(ctx).config)
    await send(ctx, text, components=buttons)


def set_player_current_audio_volume(session: PlaybackSession):
    if session.player and isinstance(
        session.player.source, disnake.PCMVolumeTransformer
    ):
        session.player.source.volume = session.config.volume_audio


async def set_volume(ctx: Context, volume: int):
    if volume < 0 or volume > 100:
        await send(ctx, "Volume must be between 0% and 100%")
        return
    session = get_session(ctx)
    session.config.volume = volume
    set_player_current_audio_volume(session)
    await send_volume_control(ctx)


async def increase_volume(ctx: Context):
    config = get_session(ctx).config
    if config.volume >= 100:
        await send(ctx, "Volume is already at maximum")
        return
    new_volume = config.volume + 10
    if new_volume > 100:
        new_volume = 100
    await set_volume(ctx, new_volume)


async def decrease_volume(ctx: Context):
    config = get_session(ctx).config
    if config.volume <= 0:
        await send(ctx, "Volume is already at minimum")
        return
    new_volume = config.volume - 10
    if new_volume < 0:
        new_volume = 0
    await set_volume(ctx, new_volume)


async def mute(ctx: Context):
    logger.debug("Mute")
    session = get_session(ctx)
    config = session.config
    if config.mute:
        await send(ctx, "Already muted")
        return
    config.mute = True
    set_player_current_audio_volume(session)
    await send_volume_control(ctx)


async def unmute(ctx: Context):
    logger.debug("Unmute")
    session = get_session(ctx)
    config = session.config
    if not config.mute:
        await send(ctx, "Already unmuted")
        return
    config.mute = False
    set_player_current_audio_volume(session)
    await send_volume_control(ctx)


async def next_(ctx: Context, user_invoked=True):
    logger.debug("Next")
    session = get_session(ctx)
    if not session.song_queue.current:
        if user_invoked:
            await send(ctx, "No song in queue")
        return
    if user_invoked and not youtube.downloads.get(session.song_queue.next["id"]):
        await defer(ctx)
    session.song_queue.current_index = session.song_queue.next_index
    start_song(session, session.song_queue.current, ctx=ctx, user_invoked=user_invoked)


async def previous(ctx: Context):
    logger.debug("Previous")
    session = get_session(ctx)
    if not session.song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not youtube.downloads.get(session.song_queue.previous["id"]):
        await defer(ctx)
    session.song_queue.current_index = session.song_queue.previous_index
    start_song(session, session.song_queue.current, ctx=ctx)


async def stop_player(session: PlaybackSession, disconnect: bool):
    logger.debug("Stopping player")
    session.request_generation += 1
    if session.playback_task and session.playback_task is not asyncio.current_task():
        session.playback_task.cancel()
    session.playback_task = None
    if not session.player:
        return
    player_buffer = session.player
    session.player = None
    session.playback_generation += 1
    if session.progress_task:
        session.progress_task.cancel()
        session.progress_task = None
    if player_buffer:
        player_buffer.stop()
        if disconnect and player_buffer.is_connected():
            await player_buffer.disconnect(force=True)


async def clear_queue(ctx: Context, is_user_invoked=True, disconnect_player=True):
    logger.debug("Clear queue")
    session = get_session(ctx)
    if not session.song_queue.current and is_user_invoked:
        await send(ctx, "Queue is empty")
        return
    await stop_player(session, disconnect_player)
    session.song_queue.clear()
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
    session = get_session(ctx)
    if not session.song_queue.current:
        await send(ctx, "Queue is empty")
        return

    if not session.player or not (
        session.player.is_playing() or session.player.is_paused()
    ):
        playback_status = "⏹️"
    elif session.player.is_paused():
        playback_status = "⏸️"
    else:
        playback_status = "▶️"
    queue_list = [
        f"**{i + 1}.** ***{playback_status} {song['title']}***"
        if i == session.song_queue.current_index
        else f"**{i + 1}.** {song['title']}"
        for i, song in enumerate(session.song_queue.queue)
    ]
    await send_lines(ctx, queue_list)


async def loop(ctx: Context):
    logger.debug("Loop")
    get_session(ctx).config.loop = True
    await now_playing(ctx)


async def loop_queue(ctx: Context):
    logger.debug("Loop queue")
    get_session(ctx).config.repeat_mode = "queue"
    await now_playing(ctx, "Repeating queue")


async def unloop(ctx: Context):
    logger.debug("Unloop")
    get_session(ctx).config.loop = False
    await now_playing(ctx)


async def shuffle(ctx: Context):
    logger.debug("Shuffle")
    get_session(ctx).song_queue.shuffle()
    await show_queue(ctx)


async def is_valid_song_number(ctx: Context, song_number: int) -> bool:
    if song_number < 1 or song_number > len(get_session(ctx).song_queue.queue):
        await send(ctx, "Invalid song number")
        await show_queue(ctx)
        return False
    return True


async def dequeue(ctx: Context, song_number: int):
    logger.debug(f"Dequeue {song_number}")
    session = get_session(ctx)
    if not session.song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    index = song_number - 1
    was_playing = session.player is not None and session.player.is_playing()
    should_resume = False
    if index == session.song_queue.current_index:
        if len(session.song_queue.queue) > 1:
            should_resume = True
            await stop_player(session, False)
        else:
            await stop_player(session, True)
    session.song_queue.dequeue(index)
    await show_queue(ctx)
    if was_playing and should_resume:
        await resume(ctx)


async def dequeue_next(ctx: Context):
    logger.debug("Dequeue next")
    await dequeue(ctx, get_session(ctx).song_queue.next_index + 1)


async def dequeue_previous(ctx: Context):
    logger.debug("Dequeue previous")
    await dequeue(ctx, get_session(ctx).song_queue.previous_index + 1)


async def dequeue_current(ctx: Context):
    logger.debug("Dequeue current")
    await dequeue(ctx, get_session(ctx).song_queue.current_index + 1)


def playback_position(session: PlaybackSession) -> float:
    if not session.playback_started_at:
        return 0.0
    end = (
        session.playback_paused_at
        if session.playback_paused_at is not None
        else time.monotonic()
    )
    return max(0.0, end - session.playback_started_at - session.playback_paused_total)


def progress_file(
    session: PlaybackSession, song: youtube.SongMetadata
) -> disnake.File | None:
    duration = song.get("duration")
    if not duration:
        return None
    return disnake.File(
        render_progress(playback_position(session), duration), filename="progress.png"
    )


async def refresh_progress_message(
    session: PlaybackSession, message: disnake.Message, generation: int
):
    while generation == session.playback_generation and session.player:
        await asyncio.sleep(10)
        if (
            generation != session.playback_generation
            or not session.player
            or not session.song_queue.current
        ):
            return
        song = session.song_queue.current
        file = progress_file(session, song)
        if not file:
            return
        embed, _ = now_playing_component(song, session.player, session.config)
        embed.set_image(url="attachment://progress.png")
        try:
            await message.edit(embed=embed, file=file, attachments=[])
        except disnake.HTTPException:
            logger.exception("Could not refresh the playback progress message")
            return


async def now_playing(
    ctx: Context,
    footer="Now playing",
):
    logger.debug("Now playing")
    session = get_session(ctx)
    if not session.song_queue.current or not session.player:
        await send(ctx, "No song is currently playing")
        return
    song = session.song_queue.current
    embed, buttons = now_playing_component(song, session.player, session.config, footer)
    file = progress_file(session, song)
    if file:
        embed.set_image(url="attachment://progress.png")
    session.progress_message = await send(
        ctx,
        embed=embed,
        components=buttons,
        file=file,
    )
    if session.progress_task:
        session.progress_task.cancel()
    if session.progress_message and song.get("duration"):
        session.progress_task = asyncio.create_task(
            refresh_progress_message(
                session, session.progress_message, session.playback_generation
            )
        )


async def publish_now_playing(session: PlaybackSession, footer="Now playing"):
    if not session.song_queue.current or not session.player:
        return
    song = session.song_queue.current
    embed, buttons = now_playing_component(song, session.player, session.config, footer)
    file = progress_file(session, song)
    if file:
        embed.set_image(url="attachment://progress.png")
    view = disnake.ui.View(timeout=None)
    for button in buttons:
        view.add_item(button)
    kwargs = {"embed": embed, "view": view}
    if file:
        kwargs["file"] = file
    session.progress_message = await send_session(session, **kwargs)
    if session.progress_task:
        session.progress_task.cancel()
    if session.progress_message and song.get("duration"):
        session.progress_task = asyncio.create_task(
            refresh_progress_message(
                session, session.progress_message, session.playback_generation
            )
        )


async def stop(ctx: Context):
    logger.debug("Stop")
    session = get_session(ctx)
    if not session.player:
        await send(ctx, "No song is currently playing")
        return

    await stop_player(session, True)
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
    for session in sessions.values():
        await stop_player(session, True)
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
    session = get_session(ctx)
    if not session.song_queue.current:
        await send(ctx, "No song in queue")
        return
    if not await is_valid_song_number(ctx, song_number):
        return
    await stop_player(session, False)
    session.song_queue.current_index = song_number - 1
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
    session = get_session(ctx)
    session.song_queue.clear()
    session.song_queue.extend(songs)
    search_results.extend(songs)
    await stop_player(session, False)
    await resume(ctx)


async def stop_bot(ctx: Context):
    logger.debug("Stop bot")
    await owner_send(ctx, "Stopping bot")
    for session in sessions.values():
        await stop_player(session, True)
    await bot.close()


async def restart_bot(ctx: Context):
    logger.debug("Restart bot")
    await owner_send(ctx, "Restarting bot")
    for session in sessions.values():
        await stop_player(session, True)
    await bot.close()
    os.execv(sys.executable, [sys.executable, *sys.argv])


def start_song(
    session: PlaybackSession,
    song: youtube.SongMetadata,
    ctx: Context | None = None,
    user_invoked: bool = True,
):
    session.request_generation += 1
    request_generation = session.request_generation
    if session.playback_task:
        session.playback_task.cancel()

    async def download_and_play():
        try:
            file_path, metadata = await asyncio.to_thread(
                youtube.download_single, song["url"], song["id"]
            )
            if request_generation != session.request_generation:
                return
            async with session.transition_lock:
                if request_generation != session.request_generation:
                    return
                await play_song_in_voice_channel(
                    ctx,
                    session,
                    metadata,
                    file_path=file_path,
                    user_invoked=user_invoked,
                )
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.exception("Download or playback failed for %s", song["id"])
            if request_generation != session.request_generation:
                return
            if user_invoked and ctx is not None:
                try:
                    await send_error(ctx, exc)
                except Exception:
                    logger.exception("Could not send playback error to Discord")
            else:
                await send_session(
                    session, f"Could not play **{song['title']}**; skipping it."
                )
                next_index = session.song_queue.current_index + 1
                if next_index < len(session.song_queue.queue):
                    session.song_queue.current_index = next_index
                    start_song(session, session.song_queue.current, user_invoked=False)
                else:
                    await stop_player(session, True)
                    session.song_queue.clear()
                    await send_session(session, "Queue finished")

    session.playback_task = asyncio.create_task(download_and_play())
    return session.playback_task
