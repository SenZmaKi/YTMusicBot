import json
import logging
import os
from pathlib import Path
import shutil
import threading
from dotenv import load_dotenv
from typing import Callable, Generic, TypeVar

load_dotenv()


logger = logging.getLogger("ytmusibot")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ytmusibot.log"),
    ],
)

logger_blocklist = [
    "interactions",
    "asyncio",
]
REPO = "https://github.com/SenZmaKi/YTMusicBot"
CREATOR_NAME = "SenZmaKi"
CREATOR_DISCORD_CHAT_URL = "https://discordapp.com/users/760954192399040522"

for module in logger_blocklist:
    logging.getLogger(module).setLevel(logging.WARNING)

cache_dir = Path("cache")
if cache_dir.exists() and os.getenv("CLEAR_CACHE") == "1":
    logger.debug("Clearing cache")
    shutil.rmtree(cache_dir)

cache_dir.mkdir(exist_ok=True)


K = TypeVar("K")
V = TypeVar("V")


class Cache(Generic[K, V]):
    all: list["Cache"] = []

    def __init__(
        self,
        name: str,
        parent_logger: logging.Logger,
        default_data: dict[K, V],
        on_reset: Callable[[], None] | None = None,
    ):
        self.default_data = default_data
        self.name = name
        self.file_path = cache_dir / f"{name}.json"
        self.file_lock = threading.Lock()
        self.logger = parent_logger.getChild(f"{name}_cache")
        self.data = self._load_data()
        self.on_reset = on_reset
        self.save()
        self.all.append(self)

    def _load_data(self) -> dict[K, V]:
        if self.file_path.exists():
            with self.file_lock, open(self.file_path, "r") as f:
                return json.load(f)
        return self.default_data

    def reset(self):
        self.data = self.default_data
        self.save()
        if self.on_reset:
            self.on_reset()

    def save(self):
        with self.file_lock, open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def get(self, key: K) -> V | None:
        return self.data.get(key)

    def __contains__(self, key: K) -> bool:
        return key in self.data

    def __delitem__(self, key: K):
        del self.data[key]
        self.save()

    def __getitem__(self, key: K) -> V:
        return self.data[key]

    def __setitem__(self, key: K, value: V):
        self.data[key] = value
        self.save()
