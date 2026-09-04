from ytmusicbot.youtube.main import (
    get_id,
    info_to_song_metadata,
    search,
    download_single,
    get_songs_in_playlist,
)


def test_search_metadata_uses_canonical_url():
    video_id = "UIe6V10sslc"
    metadata = info_to_song_metadata(
        {
            "id": video_id,
            "title": "Example",
            "url_suffix": (
                f"/watch?v={video_id}&list=RD{video_id}"
                "&start_radio=1&pp=tracking-data"
            ),
            "thumbnails": ["https://example.com/thumbnail.jpg"],
        },
        is_search_info=True,
    )

    assert metadata["url"] == f"https://www.youtube.com/watch?v={video_id}"
    assert len(f"play-{metadata['url']}") <= 100
    assert len(f"queue-{metadata['url']}") <= 100


def test_mix_metadata_uses_single_video_url():
    video_id = "5OHo0NerdEY"
    metadata = info_to_song_metadata(
        {
            "id": video_id,
            "title": "If Only",
            "url": f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}",
            "thumbnails": [{"url": "https://example.com/thumbnail.jpg"}],
        },
        is_mix_info=True,
    )

    assert metadata["url"] == f"https://www.youtube.com/watch?v={video_id}"


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


def test_search():
    query = "Sauti Sol"
    results = search(query, max_results=10)
    print(results)


def test_mix(download=False):
    url = "https://www.youtube.com/watch?v=Or2sMfOcTtw&list=RDEMGKSEWOD6zbF-FHc_dLYrPg&start_radio=1"
    test_playlist(url, download=download)


def test_playlist(
    url="https://www.youtube.com/watch?v=jJPMnTXl63E&list=PL3yHf51-oxPi37LMBbuxJoEPA_SE5ymlU",
    download=False,
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
        if download:
            for url in urls:
                test_download_single(url)
    else:
        raise Exception("Not a playlist")


def test_download_single(url="https://www.youtube.com/watch?v=jJPMnTXl63E"):
    id, is_playlist = get_id(url)
    if not id:
        raise Exception("Invalid url")
    if is_playlist:
        raise Exception("Not a single")
    else:
        result = download_single(url, id)
        print(f"Downloaded {result.file_path}")


def main():
    test_rx()
    test_search()
    test_download_single()
    test_playlist()
    test_mix()


if __name__ == "__main__":
    main()
