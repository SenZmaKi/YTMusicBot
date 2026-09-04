import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("SERVER_IDS", "1")

from ytmusicbot.discord import logic


def song(video_id: str):
    return {
        "id": video_id,
        "title": f"Song {video_id}",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": "https://example.com/thumb.jpg",
    }


class PlaybackTransitionTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_request_cancels_superseded_download(self):
        session = SimpleNamespace(
            request_generation=0,
            playback_task=None,
            transition_lock=asyncio.Lock(),
        )
        first_started = asyncio.Event()
        release_first = asyncio.Event()

        async def fake_to_thread(_function, _url, video_id):
            if video_id == "first":
                first_started.set()
                await release_first.wait()
            return f"{video_id}.webm", song(video_id)

        play_mock = AsyncMock()
        with (
            patch.object(logic.asyncio, "to_thread", side_effect=fake_to_thread),
            patch.object(logic, "play_song_in_voice_channel", play_mock),
        ):
            first_task = logic.start_song(session, song("first"))
            await first_started.wait()
            second_task = logic.start_song(session, song("second"))
            release_first.set()
            await asyncio.gather(first_task, second_task)

        play_mock.assert_awaited_once()
        self.assertEqual(play_mock.await_args.args[2]["id"], "second")

    async def test_reuses_connected_guild_voice_client_after_soft_stop(self):
        voice_client = SimpleNamespace(
            is_connected=lambda: True,
            channel=SimpleNamespace(id=42),
            is_playing=lambda: False,
            is_paused=lambda: False,
            play=lambda *_args, **_kwargs: None,
        )
        voice_client.move_to = AsyncMock()
        channel = SimpleNamespace(id=42)
        channel.connect = AsyncMock(side_effect=AssertionError("must reuse voice client"))
        ctx = SimpleNamespace(
            author=SimpleNamespace(voice=SimpleNamespace(channel=channel)),
            guild=SimpleNamespace(voice_client=voice_client),
        )
        session = SimpleNamespace(
            player=None,
            song_queue=SimpleNamespace(current=None),
            config=SimpleNamespace(volume_audio=0.5),
            playback_generation=0,
            playback_started_at=0.0,
            playback_paused_at=None,
            playback_paused_total=0.0,
        )

        transformer = SimpleNamespace()
        metadata = song("reuse")
        metadata["duration"] = 1.0
        with (
            patch.object(logic.disnake, "FFmpegPCMAudio", return_value=object()),
            patch.object(logic.disnake, "PCMVolumeTransformer", return_value=transformer),
            patch.object(logic, "now_playing", AsyncMock()),
        ):
            await logic.play_song_in_voice_channel(
                ctx, session, metadata, "reuse.webm", user_invoked=True
            )

        channel.connect.assert_not_awaited()
        self.assertIs(session.player, voice_client)


if __name__ == "__main__":
    unittest.main()
