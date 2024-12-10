import os
import random
from typing import Literal, TypedDict
from ytmusicbot.discord.common import (
    logger,
    DiscordException,
)
import ytmusicbot.youtube as youtube
from ytmusicbot.common.main import Cache, load_dotenv


load_dotenv()

class ConfigData(TypedDict):
    volume: int
    loop: bool
    mute: bool


class Config(Cache[Literal["data"], ConfigData]):
    def __init__(self) -> None:
        super().__init__(
            "config", logger, {"data": {"volume": 50, "loop": False, "mute": False}}
        )

    @property
    def mute(self):
        return self["data"]["mute"]

    @mute.setter
    def mute(self, value: bool):
        self["data"]["mute"] = value
        self.save()

    @property
    def loop(self):
        return self["data"]["loop"]

    @loop.setter
    def loop(self, value: bool):
        self["data"]["loop"] = value
        self.save()

    @property
    def volume(self):
        return self["data"]["volume"]

    @property
    def volume_audio(self):
        volume = self.volume / 100
        return 0 if self.mute else volume

    @volume.setter
    def volume(self, value: int):
        self["data"]["volume"] = value
        self.save()


class SongQueueData(TypedDict):
    queue: list[youtube.SongMetadata]
    current_index: int


class SongQueue(Cache[Literal["data"], SongQueueData]):
    def __init__(self) -> None:
        super().__init__(
            "song_queue",
            logger,
            default_data={
                "data": {
                    "queue": [],
                    "current_index": 0,
                }
            },
        )

    @property
    def current(self) -> youtube.SongMetadata | None:
        return self.queue[self.current_index] if self.queue else None

    @current.setter
    def current(self, value: youtube.SongMetadata):
        for idx, song in enumerate(self.queue):
            if song["id"] == value["id"]:
                logger.debug(f"Setting current song to {song}")
                self.current_index = idx
                return
        logger.debug(f"Song {value} not found in queue")
        raise DiscordException(f"Song {value} not found in queue")

    @property
    def current_index(self) -> int:
        return self["data"]["current_index"]

    @current_index.setter
    def current_index(self, value: int):
        self["data"]["current_index"] = value
        self.save()

    @property
    def queue(self) -> list[youtube.SongMetadata]:
        return self["data"]["queue"]

    def dequeue(self, index: int):
        if not self.current:
            return
        current_buffer = self.current
        was_current = self.queue[index]["id"] == current_buffer["id"]
        self.queue.pop(index)
        if self.queue:
            if was_current:
                self.current_index = index
            else:
                self.current = current_buffer
        else:
            self.current_index = 0
        self.save()

    @queue.setter
    def queue(self, value: list[youtube.SongMetadata]):
        self["data"]["queue"] = value
        self.save()

    @property
    def next_index(self) -> int:
        index = self.current_index + 1
        if index >= len(self.queue):
            index = 0
        return index

    @property
    def next(self) -> youtube.SongMetadata:
        next_song = self.queue[self.next_index]
        self.logger.debug(f"Next song: {next_song}")
        return next_song

    @property
    def previous_index(self) -> int:
        index = self.current_index - 1
        if index < 0:
            index = len(self.queue) - 1
        return index

    @property
    def previous(self) -> youtube.SongMetadata:
        previous_song = self.queue[self.previous_index]
        self.logger.debug(f"Previous song: {previous_song}")
        return previous_song

    def append(self, value: youtube.SongMetadata) -> None:
        if value not in self.queue:
            self.queue = [*self.queue, value]

    def extend(self, value: list[youtube.SongMetadata]) -> None:
        missing = [song for song in value if song not in self.queue]
        if missing:
            self.queue = [*self.queue, *missing]

    def clear(self) -> None:
        self.logger.debug("Clearing queue")
        self.queue = []
        self.current_index = 0

    def shuffle(self):
        self.logger.debug("Shuffling queue")
        current_buffer = self.current
        if not current_buffer:
            return
        random.shuffle(self.queue)
        self.current = current_buffer
        self.save()

    def __contains__(self, value: youtube.SongMetadata) -> bool:
        for song in self.queue:
            if song["id"] == value["id"]:
                return True
        return False


class SearchResults(Cache[Literal["data"], list[youtube.SongMetadata]]):
    max_results = int(os.getenv("MAX_SEARCH_RESULTS", 1000))

    def __init__(self) -> None:
        super().__init__("search_results", logger, {"data": []})

    def get(self, id: str) -> youtube.SongMetadata | None:
        try:
            return next(m for m in self["data"] if m["id"] == id)
        except StopIteration:
            return None

    def extend(self, value: list[youtube.SongMetadata]) -> None:
        self["data"].extend(value)
        self.save()

    def append(self, value: youtube.SongMetadata) -> None:
        self["data"].append(value)
        self.save()

    def save(self) -> None:
        self.data["data"] = self["data"][-SearchResults.max_results :]
        super().save()
