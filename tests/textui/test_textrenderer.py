import pytest

from config.config import Config
from level.level import Level
from food.food import Food
from snake.snakePart import SnakePart
from textui.textrenderer import TextRenderer


def locationAt(environment, x, y):
    grid = environment.getGrid()
    for locationId in grid.getLocations():
        location = grid.getLocation(locationId)
        if location.getX() == x and location.getY() == y:
            return location
    raise ValueError("no location at ({}, {})".format(x, y))


@pytest.fixture
def renderer():
    return TextRenderer(Config())


def test_render_grid_marks_head_body_and_food(renderer, capsys):
    level = Level("Level 1", 3)
    environment = level.environment

    head = SnakePart((0, 255, 0))
    body = SnakePart((0, 200, 0))
    environment.addEntityToLocation(head, locationAt(environment, 0, 0))
    environment.addEntityToLocation(body, locationAt(environment, 1, 0))

    food = Food((255, 0, 0))
    environment.addEntityToLocation(food, locationAt(environment, 2, 2))

    renderer.renderGrid(environment, [head, body], collision=False)

    out = capsys.readouterr().out
    lines = out.splitlines()
    gridLines = lines[1:4]
    assert gridLines[0].strip("│ ") == "H S ."
    assert gridLines[2].strip("│ ") == ". . F"
    assert "COLLISION" not in out
    assert "Legend: H=Head, S=Snake, F=Food, .=Empty" in out


def test_render_grid_reports_collision(renderer, capsys):
    level = Level("Level 1", 2)
    environment = level.environment
    head = SnakePart((0, 255, 0))
    environment.addEntityToLocation(head, locationAt(environment, 0, 0))

    renderer.renderGrid(environment, [head], collision=True)

    out = capsys.readouterr().out
    assert "[!] COLLISION! The ophidian collides with itself!" in out


def test_render_stats_shows_level_length_score_and_progress(renderer, capsys):
    renderer.renderStats(level=3, snakeLength=5, score=120, percentage=0.5)

    out = capsys.readouterr().out
    assert "Level: 3" in out
    assert "Length: 5" in out
    assert "Score: 120" in out
    assert "Progress: 50%" in out
    assert "█" * 15 + "░" * 15 in out


def test_render_hud_shows_currency_and_active_upgrades(renderer, capsys):
    renderer.renderHud(currency=42, activeUpgradeLabels=["Head Start", "Extra Life"])

    out = capsys.readouterr().out
    assert "Currency: 42" in out
    assert "Active upgrades: Head Start, Extra Life" in out


def test_render_hud_omits_upgrades_line_when_none_active(renderer, capsys):
    renderer.renderHud(currency=0, activeUpgradeLabels=[])

    out = capsys.readouterr().out
    assert "Currency: 0" in out
    assert "Active upgrades" not in out


def test_render_controls_lists_key_bindings(renderer, capsys):
    renderer.renderControls()

    out = capsys.readouterr().out
    assert "w/↑=Up" in out
    assert "q=Quit" in out


def test_enable_and_disable_raw_mode_use_termios(renderer, monkeypatch):
    calls = []
    monkeypatch.setattr("os.name", "posix")

    class FakeStdin:
        def fileno(self):
            return 0

    monkeypatch.setattr("sys.stdin", FakeStdin())
    monkeypatch.setattr("termios.tcgetattr", lambda fd: "saved-settings", raising=False)
    monkeypatch.setattr(
        "tty.setcbreak", lambda fd: calls.append("setcbreak"), raising=False
    )
    monkeypatch.setattr(
        "termios.tcsetattr",
        lambda fd, when, settings: calls.append(("tcsetattr", when, settings)),
        raising=False,
    )

    renderer.enableRawMode()
    assert renderer.old_settings == "saved-settings"
    assert calls == ["setcbreak"]

    renderer.disableRawMode()
    assert calls[-1] == ("tcsetattr", 1, "saved-settings")


def test_disable_raw_mode_is_a_noop_without_prior_enable(renderer):
    renderer.old_settings = None
    renderer.disableRawMode()  # should not raise


def test_get_key_press_returns_none_when_nothing_ready(renderer, monkeypatch):
    monkeypatch.setattr("os.name", "posix")
    monkeypatch.setattr(
        "select.select", lambda rlist, wlist, xlist, timeout: ([], [], [])
    )

    assert renderer.getKeyPress() is None


def test_get_key_press_returns_plain_character(renderer, monkeypatch):
    monkeypatch.setattr("os.name", "posix")

    class FakeStdin:
        def read(self, n):
            return "w"

    monkeypatch.setattr("sys.stdin", FakeStdin())
    monkeypatch.setattr(
        "select.select", lambda rlist, wlist, xlist, timeout: ([True], [], [])
    )

    assert renderer.getKeyPress() == "w"


def test_get_key_press_assembles_arrow_escape_sequence(renderer, monkeypatch):
    monkeypatch.setattr("os.name", "posix")

    chars = iter(["\x1b", "[", "A"])

    class FakeStdin:
        def read(self, n):
            return next(chars)

    monkeypatch.setattr("sys.stdin", FakeStdin())
    monkeypatch.setattr(
        "select.select", lambda rlist, wlist, xlist, timeout: ([True], [], [])
    )

    assert renderer.getKeyPress() == "\x1b[A"
