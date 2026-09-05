import disnake

from ytmusicbot.discord.common import (
    ButtonID,
    DiscordException,
    bot,
    discord_token,
    logger,
)
from ytmusicbot.discord.caches import url_mapping
from ytmusicbot.discord import logic


@bot.event
async def on_ready():
    logger.info("Logged in as %s", bot.user)


@bot.slash_command(description="Search for a song on YouTube")
async def search(
    inter: disnake.ApplicationCommandInteraction,
    query: str,
    max_results: int = 3,
    include_playlists: bool = False,
):
    await logic.search(inter, query, max_results, include_playlists)


@bot.slash_command(description="Play a song")
async def play(inter: disnake.ApplicationCommandInteraction, title_or_url: str):
    await logic.play(title_or_url, inter)


@bot.slash_command(name="queue", description="Queue a song")
async def queue_command(
    inter: disnake.ApplicationCommandInteraction, title_or_url: str
):
    await logic.queue(title_or_url, inter)


@bot.slash_command(description="Clear the song queue")
async def clear_queue(inter: disnake.ApplicationCommandInteraction):
    await logic.clear_queue(inter)


@bot.slash_command(name="next", description="Play the next song")
async def next_command(inter: disnake.ApplicationCommandInteraction):
    await logic.next_(inter)


@bot.slash_command(description="Play the previous song")
async def previous(inter: disnake.ApplicationCommandInteraction):
    await logic.previous(inter)


@bot.slash_command(description="Pause playback")
async def pause(inter: disnake.ApplicationCommandInteraction):
    await logic.pause(inter)


@bot.slash_command(description="Resume playback")
async def resume(inter: disnake.ApplicationCommandInteraction):
    await logic.resume(inter)


@bot.slash_command(description="Stop playback")
async def stop(inter: disnake.ApplicationCommandInteraction):
    await logic.stop(inter)


@bot.slash_command(description="Show the song queue")
async def show_queue(inter: disnake.ApplicationCommandInteraction):
    await logic.show_queue(inter)


@bot.slash_command(description="Remove a song from the queue")
async def dequeue(inter: disnake.ApplicationCommandInteraction, song_number: int):
    await logic.dequeue(inter, song_number)


@bot.slash_command(description="Remove the next song")
async def dequeue_next(inter: disnake.ApplicationCommandInteraction):
    await logic.dequeue_next(inter)


@bot.slash_command(description="Remove the previous song")
async def dequeue_previous(inter: disnake.ApplicationCommandInteraction):
    await logic.dequeue_previous(inter)


@bot.slash_command(description="Remove the current song")
async def dequeue_current(inter: disnake.ApplicationCommandInteraction):
    await logic.dequeue_current(inter)


@bot.slash_command(description="Skip to a numbered song")
async def skip_to(inter: disnake.ApplicationCommandInteraction, song_number: int):
    await logic.skip_to(inter, song_number)


@bot.slash_command(description="Set playback volume")
async def set_volume(inter: disnake.ApplicationCommandInteraction, volume: int):
    await logic.set_volume(inter, volume)


@bot.slash_command(description="Increase volume by 10 percent")
async def increase_volume(inter: disnake.ApplicationCommandInteraction):
    await logic.increase_volume(inter)


@bot.slash_command(description="Decrease volume by 10 percent")
async def decrease_volume(inter: disnake.ApplicationCommandInteraction):
    await logic.decrease_volume(inter)


@bot.slash_command(description="Mute playback")
async def mute(inter: disnake.ApplicationCommandInteraction):
    await logic.mute(inter)


@bot.slash_command(description="Unmute playback")
async def unmute(inter: disnake.ApplicationCommandInteraction):
    await logic.unmute(inter)


@bot.slash_command(description="Show the current song")
async def now_playing(inter: disnake.ApplicationCommandInteraction):
    await logic.now_playing(inter)


@bot.slash_command(name="loop", description="Enable looping")
async def loop_command(inter: disnake.ApplicationCommandInteraction):
    await logic.loop(inter)


@bot.slash_command(description="Disable looping")
async def unloop(inter: disnake.ApplicationCommandInteraction):
    await logic.unloop(inter)


@bot.slash_command(description="Repeat the entire queue")
async def loop_queue(inter: disnake.ApplicationCommandInteraction):
    await logic.loop_queue(inter)


@bot.slash_command(description="Shuffle the queue")
async def shuffle(inter: disnake.ApplicationCommandInteraction):
    await logic.shuffle(inter)


@bot.slash_command(description="Show favourite songs")
async def show_favourites(inter: disnake.ApplicationCommandInteraction):
    await logic.show_favourites(inter)


@bot.slash_command(description="Play favourite songs")
async def play_favourites(inter: disnake.ApplicationCommandInteraction):
    await logic.play_favourites(inter)


@bot.slash_command(name="random", description="Play random songs")
async def random_command(inter: disnake.ApplicationCommandInteraction):
    await logic.random_(inter)


@bot.slash_command(description="Link to the bot source")
async def repo(inter: disnake.ApplicationCommandInteraction):
    await logic.repo(inter)


@bot.slash_command(description="Link to the bot creator")
async def creator(inter: disnake.ApplicationCommandInteraction):
    await logic.creator(inter)


async def require_owner(inter: disnake.ApplicationCommandInteraction) -> bool:
    if await bot.is_owner(inter.author):
        return True
    await logic.send(inter, "This command is owner-only", ephemeral=True)
    return False


@bot.slash_command(description="Owner-only commands")
async def owner(inter: disnake.ApplicationCommandInteraction):
    pass


@owner.sub_command(description="Reset all bot caches")
async def reset_cache(inter: disnake.ApplicationCommandInteraction):
    if await require_owner(inter):
        await logic.reset_cache(inter)


@owner.sub_command(description="Show bot metrics")
async def metrics(inter: disnake.ApplicationCommandInteraction):
    if await require_owner(inter):
        await logic.metrics(inter)


@owner.sub_command(description="Stop the bot")
async def stop_bot(inter: disnake.ApplicationCommandInteraction):
    if await require_owner(inter):
        await logic.stop_bot(inter)


@owner.sub_command(description="Restart the bot")
async def restart_bot(inter: disnake.ApplicationCommandInteraction):
    if await require_owner(inter):
        await logic.restart_bot(inter)


@bot.event
async def on_slash_command_error(
    inter: disnake.ApplicationCommandInteraction, error: Exception
):
    logger.exception("Slash command failed", exc_info=error)
    try:
        await logic.send_error(inter, error)
    except Exception:
        logger.exception("Could not send command error to Discord")


@bot.event
async def on_button_click(inter: disnake.MessageInteraction):
    try:
        custom_id = inter.component.custom_id
        exact_handlers = {
            ButtonID.next: logic.next_,
            ButtonID.previous: logic.previous,
            ButtonID.pause: logic.pause,
            ButtonID.resume: logic.resume,
            ButtonID.increase_volume: logic.increase_volume,
            ButtonID.decrease_volume: logic.decrease_volume,
            ButtonID.mute: logic.mute,
            ButtonID.unmute: logic.unmute,
            ButtonID.loop: logic.loop,
            ButtonID.unloop: logic.unloop,
            ButtonID.loop_queue: logic.loop_queue,
            ButtonID.shuffle: logic.shuffle,
        }
        if handler := exact_handlers.get(custom_id):
            await handler(inter)
            return
        for pattern, handler in (
            (ButtonID.play_rx, logic.play),
            (ButtonID.queue_rx, logic.queue),
            (ButtonID.favourite_rx, logic.favourite),
            (ButtonID.unfavourite_rx, logic.unfavourite),
        ):
            if match := pattern.fullmatch(custom_id):
                url_hash = match.group(1)
                url = url_mapping.get_url(url_hash)
                if url is None:
                    raise DiscordException(
                        "This button has expired. Run the command again to refresh it."
                    )
                await handler(url, inter)
                return
        raise DiscordException(f"Unknown component ID: {custom_id}")
    except Exception as error:
        logger.exception("Button interaction failed", exc_info=error)
        try:
            await logic.send_error(inter, error)
        except Exception:
            logger.exception("Could not send component error to Discord")


def main():
    logger.debug("Starting bot")
    bot.run(discord_token)


if __name__ == "__main__":
    main()
