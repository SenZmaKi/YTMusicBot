import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Any, Generator, NamedTuple, NotRequired, TypedDict
import yt_dlp
from pathlib import Path
from ytmusicbot.common.main import Cache, load_dotenv, logger, cache_dir
import sys


load_dotenv()

logger = logger.getChild("youtube")
IBYTES_TO_MBS = 1024**2
max_downloads_size_ibytes = (
    int(os.getenv("MAX_DOWNLOADS_SIZE_MBS", "1000")) * IBYTES_TO_MBS
)
randoms_songs_dir = Path("random_songs")
randoms_songs_dir.mkdir(exist_ok=True)


class YoutubeException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidURLException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Invalid Youtube URL: {url}")


class UnavailableVideoException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(
            f"Video {url} is unavailable, it could be private/deleted/invalid"
        )


class UnavailablePlaylistException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(
            f"Playlist {url} is unavailable, it could be private/empty/invalid"
        )


class EmptyPlaylistException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Playlist {url} is empty")


class ExtractVideoInfoException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Failed to extract video info from {url}")


class ExtractPlaylistInfoException(YoutubeException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Failed to extract playlist info from {url}")


YOUTUBE_HOME_URL = "https://www.youtube.com"
VIDEO_ID_RX = r"(?:^|\W)(?:youtube(?:-nocookie)?\.com/(?:.*[?&]v=|v/|e(?:mbed)?/|shorts/|[^/]+/.+/)|youtu\.be/)([\w-]+)"
PLAYLIST_MAGIC_STR = "list="


class SongMetadata(TypedDict):
    id: str
    title: str
    url: str
    thumbnail_url: str
    duration: NotRequired[float]


def canonical_video_url(video_id: str) -> str:
    return f"{YOUTUBE_HOME_URL}/watch?v={video_id}"


def list_contains_song(song_list: list[SongMetadata], song: SongMetadata) -> bool:
    for s in song_list:
        if s["id"] == song["id"]:
            return True
    return False


def search(
    query: str,
    max_results: int | None = 10,
    include_playlists: bool = False,
) -> list[SongMetadata]:
    limit = max_results if max_results is not None else 10
    if limit < 1:
        return []

    if include_playlists:
        encoded_query = urllib.parse.urlencode({"search_query": query})
        search_url = f"{YOUTUBE_HOME_URL}/results?{encoded_query}"
    else:
        search_url = f"ytsearch{limit}:{query}"

    try:
        search_info = search_youtube_dl.extract_info(search_url, download=False)
    except yt_dlp.utils.YoutubeDLError as error:
        raise YoutubeException(
            f'YouTube search failed for "{query}": {error}'
        ) from error

    entries = search_info.get("entries", []) if search_info else []
    results: list[SongMetadata] = []
    for entry in entries:
        if not entry or not entry.get("id") or not entry.get("title"):
            continue
        url = entry.get("url") or entry.get("webpage_url") or ""
        video_id, is_playlist = get_id(url)
        is_playlist_result = entry.get("_type") == "playlist" or "/playlist?" in url
        if is_playlist_result and is_playlist:
            if not include_playlists:
                continue
            result_url = url
        elif video_id:
            result_url = canonical_video_url(video_id)
        else:
            # Ignore channel and other non-playable search results.
            continue

        thumbnails = entry.get("thumbnails") or []
        thumbnail_url = entry.get("thumbnail") or ""
        if not thumbnail_url and thumbnails:
            thumbnail_url = thumbnails[-1].get("url", "")
        metadata: SongMetadata = {
            "id": entry["id"],
            "title": entry["title"],
            "url": result_url,
            "thumbnail_url": thumbnail_url,
        }
        if isinstance(entry.get("duration"), (int, float)):
            metadata["duration"] = float(entry["duration"])
        results.append(metadata)
        if len(results) >= limit:
            break

    logger.debug(
        "Search results for query=%r, max_results=%s: %s", query, limit, results
    )
    return results


class DownloadResponse(NamedTuple):
    file_path: Path
    metadata: SongMetadata


class Downloads(Cache[str, SongMetadata]):
    def __init__(self) -> None:
        super().__init__("downloads", logger, {}, on_reset=clear_downloads)
        self.currently_downloading: set[str] = set()

    def download_file_path(self, id: str) -> Path | None:
        try:
            file = next(download_folder.glob(f"{id}.*"))
            logger.debug(f"Checked {file} exists")
            return file
        except StopIteration:
            logger.debug(f"No file found for {id}")
            return None

    def url(self, id: str) -> str:
        return f"{YOUTUBE_HOME_URL}/watch?v={id}"

    def add(self, metadata: SongMetadata):
        id = metadata["id"]
        if not self.download_file_path(id):
            self.logger.debug(f"File system out of sync, downloading {id}")
            download_single(metadata["url"], id)

        self[metadata["id"]] = metadata
        self.logger.debug(f"Added {id}")

    def remove(self, id: str):
        if file := self.download_file_path(id):
            self.logger.debug(f"File system out of sync, deleting {file}")
            file.unlink()

        del self[id]
        self.logger.debug(f"Removed {id}")

    def get(self, id: str) -> SongMetadata | None:
        metadata = super().get(id)
        file_path = self.download_file_path(id)
        if metadata and not file_path:
            self.logger.debug(f"Database out of sync, removing {id}")
            self.remove(id)
            metadata = None
        elif not metadata and file_path:
            self.logger.debug(f"Database out of sync, adding {id}")
            url = self.url(id)
            metadata = get_song_metadata(url)
            self.add(metadata)
        self.logger.debug(f"Checked {id} in DB, result: {metadata is not None}")
        return metadata


class DownloadFolderMetrics(NamedTuple):
    size: int
    size_mbs: float
    total_downloads: int
    size_limit_mbs: float


def download_folder_metrics() -> DownloadFolderMetrics:
    files = list(download_folder.iterdir())
    size = sum(f.stat().st_size for f in files)
    size_mbs = size / IBYTES_TO_MBS
    total_downloads = len(files)
    limit = max_downloads_size_ibytes / IBYTES_TO_MBS
    return DownloadFolderMetrics(size, size_mbs, total_downloads, limit)


def download_folder_is_over_limit():
    metrics = download_folder_metrics()
    logger.debug(f"Downloads folder size: {metrics.size_mbs:.2f} MB")
    is_over_limit = metrics.size > max_downloads_size_ibytes
    if is_over_limit:
        logger.warning(
            f"Downloads folder size ({metrics.size_mbs:.2f} MB) is over the limit ({metrics.size_limit_mbs} MB)"
        )
    return is_over_limit


def check_downloads_folder_size():
    if not download_folder_is_over_limit():
        return
    sorted_by_oldest_access = sorted(
        download_folder.glob("*"), key=lambda f: f.stat().st_atime
    )
    for file in sorted_by_oldest_access:
        file.unlink()
        if not download_folder_is_over_limit():
            return


def info_to_song_metadata(
    info: dict[str, Any], is_search_info=False, is_mix_info=False
) -> SongMetadata:
    # Always represent an individual song with a canonical video URL. Search
    # and Mix results often include list/start_radio/tracking parameters, which
    # can accidentally turn a song click into a large playlist download.
    url = canonical_video_url(info["id"])

    thumbnail_url = (
        info["thumbnails"][0] if is_search_info else info["thumbnails"][0]["url"]
    )
    metadata: SongMetadata = {
        "title": info["title"],
        "url": url,
        "thumbnail_url": thumbnail_url,
        "id": info["id"],
    }
    if isinstance(info.get("duration"), (int, float)):
        metadata["duration"] = float(info["duration"])
    return metadata


def get_media_duration(file_path: Path) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        logger.exception("Could not determine duration for %s", file_path)
        return None


def get_song_metadata(url: str, download=False) -> SongMetadata:
    try:
        info = youtube_dl.extract_info(url, download=download)
        if not info:
            logger.error(f"Weird, info is {info} for {url}")
            raise ExtractVideoInfoException(url)
    except yt_dlp.utils.YoutubeDLError as e:
        logger.error(e)
        if msg := e.msg:
            match msg:
                case _ if "Incomplete YouTube ID" in msg:
                    raise InvalidURLException(msg)
                case _ if "Video unavailable" in msg:
                    raise UnavailableVideoException(msg)

        raise YoutubeException(f"Error downloading {url}: {e}")
    return info_to_song_metadata(info)


def clear_downloads():
    logger.debug("Clearing downloads")
    for file in download_folder.glob("*"):
        try:
            file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete {file}: {e}")


downloads = Downloads()

download_folder = cache_dir / "downloads"
download_folder.mkdir(exist_ok=True)

opts = {
    "format": "bestaudio/best",
    "outtmpl": f"{download_folder}/%(id)s.%(ext)s",
    "keepvideo": False,
}

# Current yt-dlp releases require a JavaScript runtime for YouTube challenge
# solving. Deno remains yt-dlp's default; enable Node automatically when it is
# installed so common development environments work without extra flags.
if shutil.which("node"):
    opts["js_runtimes"] = {"node": {"path": None}}

# Authentication is opt-in: cookie files must never be committed to the repo.
# A Netscape-format file is preferable for servers; browser extraction is
# convenient for local development.
if cookie_file := os.getenv("YTDLP_COOKIE_FILE"):
    opts["cookiefile"] = str(Path(cookie_file).expanduser())
elif cookie_browser := os.getenv("YTDLP_COOKIES_FROM_BROWSER"):
    opts["cookiesfrombrowser"] = (cookie_browser, None, None, None)

youtube_dl = yt_dlp.YoutubeDL(opts)
search_youtube_dl = yt_dlp.YoutubeDL(
    {
        **opts,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
)


def get_songs_in_playlist(
    url: str,
) -> Generator[SongMetadata, None, None]:
    try:
        # Mixes don't require processing
        info = youtube_dl.extract_info(url, download=False, process=False)
        if not info:
            logger.error(f"Weird, info is {info} for {url}")
        is_mix = True
    except yt_dlp.utils.YoutubeDLError as e:
        if msg := e.msg:
            match msg:
                case _ if "The playlist does not exist" in msg:
                    raise UnavailablePlaylistException(url)
        raise ExtractPlaylistInfoException(url)
    if not info or not info.get("entries"):
        is_mix = False
        info = youtube_dl.extract_info(url, download=False, process=True)
        if not info:
            raise ExtractPlaylistInfoException(url)
        if not info.get("entries"):
            raise UnavailablePlaylistException(url)

    logger.debug(f"{url} mix status: {is_mix}")
    entries = info["entries"]
    is_empty = True
    for entry in entries:
        is_empty = False
        metadata = info_to_song_metadata(entry, is_mix_info=is_mix)
        yield metadata
    if is_empty:
        raise EmptyPlaylistException(url)


def download_single(url: str, id: str) -> DownloadResponse:
    logger.debug(f"Parsed ID {id}")
    # This function is explicitly for one video. Discard any stale playlist or
    # radio parameters that may still exist in persisted metadata.
    url = canonical_video_url(id)
    while id in downloads.currently_downloading:
        logger.debug(f"Waiting for {id} to finish downloading")
        time.sleep(1)

    if metadata := downloads.get(id):
        file_path = downloads.download_file_path(id)
        if not file_path:
            raise YoutubeException(f"Invalid db state {id} not in {file_path}")
        logger.debug(f"Already downloaded {file_path}")
        return DownloadResponse(file_path, metadata)

    downloads.currently_downloading.add(id)
    try:
        check_downloads_folder_size()
        metadata = get_song_metadata(url, download=True)
    except Exception:
        downloads.currently_downloading.remove(id)
        raise
    downloads.currently_downloading.remove(id)
    file_path = downloads.download_file_path(id)
    if not file_path:
        raise YoutubeException(f"Failed to download {url}")
    downloads.add(metadata)
    return DownloadResponse(file_path, metadata)


def get_id(url: str) -> tuple[str | None, bool]:
    vid_id_match = re.search(VIDEO_ID_RX, url)
    is_playlist = PLAYLIST_MAGIC_STR in url
    id: str | None = None
    if vid_id_match:
        id = vid_id_match.group(1)
    elif is_playlist:
        id = url
    return id, is_playlist


def configure_random_songs():
    random_songs_config_path = Path("custom_random_songs_config.json")
    if not random_songs_config_path.exists():
        random_songs_config_path = Path("random_songs_config.json")
    with open(random_songs_config_path, "r") as f:
        songs = json.load(f)
        for song in songs:
            artist = song["artist"]
            url = song["playlist_url"]
            songs_metadata = list(get_songs_in_playlist(url))
            file_path = randoms_songs_dir / f"{artist}.json"
            with open(file_path, "w") as f:
                json.dump(songs_metadata, f, indent=4)


def main():
    if "--configure-random-songs" in sys.argv or "-crs" in sys.argv:
        configure_random_songs()
