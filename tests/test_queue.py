from pathlib import Path

from rlc.player.queue import TrackQueue


def test_queue_enqueue_and_next() -> None:
    q = TrackQueue()
    a = Path("a.mp3")
    b = Path("b.mp3")

    q.enqueue(a)
    q.enqueue(b)

    assert len(q) == 2
    assert q.next() == a
    assert q.next() == b
    assert q.next() is None
