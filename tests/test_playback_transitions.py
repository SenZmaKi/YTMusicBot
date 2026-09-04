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


if __name__ == "__main__":
    unittest.main()
