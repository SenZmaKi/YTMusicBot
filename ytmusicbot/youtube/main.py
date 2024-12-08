import json
import os
import re
import time
from typing import Any, Generator, NamedTuple, TypedDict, cast
import yt_dlp
from youtube_search import YoutubeSearch
from pathlib import Path
from ytmusicbot.common.main import Cache, logger, cache_dir
from dotenv import load_dotenv
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
        self.message = message


YOUTUBE_HOME_URL = "https://www.youtube.com"
VIDEO_ID_RX = r"(?:^|\W)(?:youtube(?:-nocookie)?\.com/(?:.*[?&]v=|v/|e(?:mbed)?/|shorts/|[^/]+/.+/)|youtu\.be/)([\w-]+)"
PLAYLIST_MAGIC_STR = "list="


class SongMetadata(TypedDict):
    id: str
    title: str
    url: str
    thumbnail_url: str


def search(query: str, max_results=10) -> list[SongMetadata]:
    yts_results = cast(
        list[dict[str, Any]], YoutubeSearch(query, max_results=max_results).to_dict()
    )
    results = [info_to_song_metadata(r, is_search_info=True) for r in yts_results]
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
    if is_search_info:
        url = f"{YOUTUBE_HOME_URL}{info['url_suffix']}"
    elif is_mix_info:
        url = info["url"]
    else:
        url = info["original_url"]

    thumbnail_url = (
        info["thumbnails"][0] if is_search_info else info["thumbnails"][0]["url"]
    )
    return {
        "title": info["title"],
        "url": url,
        "thumbnail_url": thumbnail_url,
        "id": info["id"],
    }


def get_song_metadata(url: str, download=False) -> SongMetadata:
    try:
        info = youtube_dl.extract_info(url, download=download)
        if not info:
            raise YoutubeException(f"Could not extract info from {url}")
    except yt_dlp.utils.DownloadError as e:
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
youtube_dl = yt_dlp.YoutubeDL(opts)


def get_songs_in_playlist(
    url: str,
) -> Generator[SongMetadata, None, None]:
    try:
        # Mixes don't require processing
        info = youtube_dl.extract_info(url, download=False, process=False)
        is_mix = True
    except yt_dlp.utils.DownloadError as e:
        raise YoutubeException(f"Error getting playlist info from {url}: {e}")
    if not info or not info.get("entries"):
        is_mix = False
        info = youtube_dl.extract_info(url, download=False, process=True)
        if not info:
            raise YoutubeException(f"Could not extract playlist info from {url}")
        if not info.get("entries"):
            raise YoutubeException(
                f"No entries found in {url}, playlist could be private/empty/invalid"
            )

    logger.debug(f"{url} mix status: {is_mix}")
    entries = info["entries"]
    for entry in entries:
        metadata = info_to_song_metadata(entry, is_mix_info=is_mix)
        yield metadata


def download_single(url: str, id: str) -> DownloadResponse:
    logger.debug(f"Parsed ID {id}")
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


def test_search():
    query = "Sauti Sol"
    results = search(query, max_results=10)
    print(results)


def test_download_mix(only_extract_metadata=False):
    url = "https://www.youtube.com/watch?v=Or2sMfOcTtw&list=RDEMGKSEWOD6zbF-FHc_dLYrPg&start_radio=1"
    test_download_playlist(url, only_extract_metadata=only_extract_metadata)


def test_download_playlist(
    url="https://www.youtube.com/watch?v=jJPMnTXl63E&list=PL3yHf51-oxPi37LMBbuxJoEPA_SE5ymlU",
    only_extract_metadata=False,
):
    id, is_playlist = get_id(url)
    if not id:
        raise Exception("Invalid url")
    if is_playlist:
        urls: list[str] = []
        for metadata in get_songs_in_playlist(url):
            print(f"Metadata {metadata}")
            url = metadata["url"]
            urls.append(url)
        if not only_extract_metadata:
            for url in urls:
                test_download_single(url)
    else:
        raise Exception("Not a playlist")


def test_download_single(url="https://www.youtube.com/watch?v=F1kCWrem5RU"):
    id, is_playlist = get_id(url)
    if not id:
        raise Exception("Invalid url")
    if is_playlist:
        raise Exception("Not a single")
    else:
        result = download_single(url, id)
        print(f"Downloaded {result.file_path}")


def configure_random_songs():
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


def test_rx():
    real_id = "jJPMnTXl63E"
    vid_urls = [
        f"https://www.youtube.com/watch?v={real_id}",
        f"https://youtu.be/{real_id}",
        f"https://youtube.com/watch?v={real_id}",
        f"https://www.youtube.com/shorts/{real_id}",
    ]
    playlist_urls = [
        f"https://www.youtube.com/watch?v={real_id}&list=PL3yHf51-oxPi37LMBbuxJoEPA_SE5ymlU",
        f"https://www.youtube.com/watch?v={real_id}&list=PL3yHf51-oxPi37LMBbuxJoEPA_SE5ymlU&feature=youtu.be",
        f"https://www.youtube.com/watch?v={real_id}&list=PL3yHf51-oxPi37LMBbuxJoEPA_SE5ymlU&feature=youtu.be&start=1",
        "https://www.youtube.com/playlist?list=PL3yHf51-oxPhYl8D3Zkq9n82bvgSNpTw2",
    ]

    def tester(urls: list[str], are_playlists=False):
        print(f"Testing | Are Playlists: {are_playlists} | URLs: {urls}")
        for idx, url in enumerate(urls):
            id, is_playlist = get_id(url)
            print(f"{idx + 1} ID: {id}")
            if not are_playlists:
                assert id == real_id
            assert is_playlist == are_playlists

    tester(vid_urls)
    tester(playlist_urls, are_playlists=True)
    tester(playlist_urls, are_playlists=True)


def test():
    test_rx()
    test_search()
    test_download_single()
    test_download_playlist()
    test_download_mix(only_extract_metadata=True)


def main():
    if "--configure-random-songs" in sys.argv or "-crs" in sys.argv:
        configure_random_songs()
    else:
        test()
