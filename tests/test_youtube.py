from rlc.library.youtube import (
    _canonical_youtube_watch_url,
    is_supported_youtube_url,
)


def test_is_supported_youtube_url_with_watch_list_and_radio_params() -> None:
    url = "https://www.youtube.com/watch?v=uetE5C2Tmfg&list=RDuetE5C2Tmfg&start_radio=1"
    assert is_supported_youtube_url(url)


def test_canonical_youtube_watch_url_drops_playlist_related_params() -> None:
    url = "https://www.youtube.com/watch?v=uetE5C2Tmfg&list=RDuetE5C2Tmfg&start_radio=1"
    got = _canonical_youtube_watch_url(url)
    assert got == "https://www.youtube.com/watch?v=uetE5C2Tmfg"


def test_is_supported_youtube_url_rejects_non_video_url() -> None:
    assert not is_supported_youtube_url("https://www.youtube.com/playlist?list=PL123")
