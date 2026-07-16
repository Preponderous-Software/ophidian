from ui.banner import UiBanner


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def advance(self, seconds):
        self.now += seconds

    def __call__(self):
        return self.now


def _bannerWithFakeClock(monkeypatch, durationSeconds=2.0):
    banner = UiBanner(durationSeconds=durationSeconds)
    clock = FakeClock()
    monkeypatch.setattr("ui.banner.time.time", clock)
    return banner, clock


def test_current_returns_none_when_queue_is_empty():
    banner = UiBanner()
    assert banner.current() is None


def test_current_returns_pushed_message(monkeypatch):
    banner, clock = _bannerWithFakeClock(monkeypatch)
    banner.push("hello")
    assert banner.current() == "hello"


def test_messages_are_shown_in_order_not_clobbered(monkeypatch):
    # regression case: two notify()-style push() calls firing back-to-back
    # before any frame is drawn must each get a turn, not just the last one
    banner, clock = _bannerWithFakeClock(monkeypatch)
    banner.push("first")
    banner.push("second")

    seenInOrder = []
    for _ in range(6):
        message = banner.current()
        if message is not None and (not seenInOrder or seenInOrder[-1] != message):
            seenInOrder.append(message)
        clock.advance(2.1)

    assert seenInOrder == ["first", "second"]


def test_message_expires_after_duration(monkeypatch):
    banner, clock = _bannerWithFakeClock(monkeypatch, durationSeconds=1.0)
    banner.push("hello")
    assert banner.current() == "hello"
    clock.advance(0.5)
    assert banner.current() == "hello"
    clock.advance(0.6)
    assert banner.current() is None


def test_draw_calls_graphik_with_current_message(monkeypatch):
    banner, clock = _bannerWithFakeClock(monkeypatch)
    banner.push("hello")

    calls = []

    class FakeGraphik:
        def drawRectangle(self, *args):
            calls.append(("rect", args))

        def drawText(self, *args):
            calls.append(("text", args))

    banner.draw(FakeGraphik(), width=500, backgroundColor=(0, 0, 0), textColor=(255, 255, 255))

    assert ("rect", (0, 0, 500, 30, (0, 0, 0))) in calls
    assert ("text", ("hello", 250, 15, 16, (255, 255, 255))) in calls


def test_draw_does_nothing_when_queue_empty():
    banner = UiBanner()
    calls = []

    class FakeGraphik:
        def drawRectangle(self, *args):
            calls.append("rect")

        def drawText(self, *args):
            calls.append("text")

    banner.draw(FakeGraphik(), width=500, backgroundColor=(0, 0, 0), textColor=(255, 255, 255))
    assert calls == []
