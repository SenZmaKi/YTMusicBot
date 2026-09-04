import tempfile
import unittest
from pathlib import Path

import ytmusicbot.common.main as common
from ytmusicbot.discord.caches import Config, SongQueue


def song(video_id: str, *, duration: float | None = None):
    value = {
        "id": video_id,
        "title": f"Song {video_id}",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": "https://example.com/thumb.jpg",
    }
    if duration is not None:
        value["duration"] = duration
    return value


class SongQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cache_dir = common.cache_dir
        common.cache_dir = Path(self.temp_dir.name)

    def tearDown(self):
        common.cache_dir = self.original_cache_dir
        self.temp_dir.cleanup()

    def test_duplicate_video_ids_are_not_added(self):
        queue = SongQueue("duplicate_test")
        queue.append(song("same"))
        queue.append(song("same", duration=123))
        self.assertEqual([item["id"] for item in queue.queue], ["same"])

    def test_extend_deduplicates_input_and_existing_queue(self):
        queue = SongQueue("extend_test")
        queue.append(song("one"))
        queue.extend([song("one", duration=1), song("two"), song("two", duration=2)])
        self.assertEqual([item["id"] for item in queue.queue], ["one", "two"])

    def test_dequeue_current_advances_to_next_song(self):
        queue = SongQueue("dequeue_test")
        queue.extend([song("one"), song("two"), song("three")])
        queue.current_index = 1
        queue.dequeue(1)
        self.assertEqual(queue.current["id"], "three")
        self.assertEqual([item["id"] for item in queue.queue], ["one", "three"])

    def test_repeat_modes_preserve_song_loop_compatibility(self):
        config = Config("repeat_test")
        self.assertEqual(config.repeat_mode, "off")
        config.loop = True
        self.assertEqual(config.repeat_mode, "song")
        config.repeat_mode = "queue"
        self.assertFalse(config.loop)
        self.assertEqual(config.repeat_mode, "queue")
        config.loop = False
        self.assertEqual(config.repeat_mode, "off")


if __name__ == "__main__":
    unittest.main()
