from importlib import import_module
from unittest.mock import patch

youtube = import_module("ytmusicbot.youtube.main")


def test_search_uses_yt_dlp_and_canonicalizes_video_urls():
    search_data = {
        "entries": [
            {
                "id": "abc123def45",
                "title": "A result",
                "url": "https://www.youtube.com/watch?v=abc123def45&list=RDabc123def45",
                "thumbnail": "https://example.com/thumb.jpg",
                "duration": 123,
            }
        ]
    }

    with patch.object(
        youtube.search_youtube_dl, "extract_info", return_value=search_data
    ) as extract_info:
        results = youtube.search("a query", max_results=1)

    extract_info.assert_called_once_with("ytsearch1:a query", download=False)
    assert results == [
        {
            "id": "abc123def45",
            "title": "A result",
            "url": "https://www.youtube.com/watch?v=abc123def45",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "duration": 123.0,
        }
    ]


def test_search_can_keep_playlist_results():
    playlist_url = "https://www.youtube.com/playlist?list=PL123"
    search_data = {
        "entries": [
            {
                "id": "PL123",
                "title": "A playlist",
                "url": playlist_url,
                "thumbnails": [{"url": "https://example.com/playlist.jpg"}],
            }
        ]
    }

    with patch.object(
        youtube.search_youtube_dl, "extract_info", return_value=search_data
    ):
        results = youtube.search("a playlist", max_results=3, include_playlists=True)

    assert results[0]["url"] == playlist_url
