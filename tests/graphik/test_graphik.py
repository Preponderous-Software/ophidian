import pygame
import pytest

from preponderous.graphik import Graphik

BACKGROUND = (0, 0, 0)
RED = (200, 0, 0)
WHITE = (255, 255, 255)


@pytest.fixture
def surface():
    # a plain Surface is enough for every draw call graphik makes, so no
    # window (and no video driver) is needed
    pygame.font.init()
    surface = pygame.Surface((200, 100))
    surface.fill(BACKGROUND)
    yield surface
    pygame.font.quit()


def _drawnBounds(surface):
    """The smallest rect holding every pixel that is not the background."""
    width, height = surface.get_size()
    xs = []
    ys = []
    for x in range(width):
        for y in range(height):
            if tuple(surface.get_at((x, y)))[:3] != BACKGROUND:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _mouseAt(monkeypatch, position, pressed):
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: position)
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: pressed)


def test_get_game_display_returns_the_surface_it_was_built_with(surface):
    assert Graphik(surface).getGameDisplay() is surface


def test_colour_constants_are_on_the_class_and_the_instance(surface):
    # the old vendored copy defined __init__ twice, so its colour attributes
    # never existed; the installed graphik has them as class attributes
    assert Graphik.red == (200, 0, 0)
    assert Graphik(surface).white == WHITE


def test_get_version_returns_the_installed_version(surface):
    import preponderous.graphik as graphikPackage

    assert Graphik(surface).getVersion() == graphikPackage.__version__


def test_draw_rectangle_fills_exactly_the_given_area(surface):
    Graphik(surface).drawRectangle(10, 20, 30, 40, RED)
    assert _drawnBounds(surface) == (10, 20, 39, 59)
    assert tuple(surface.get_at((25, 40)))[:3] == RED


def test_draw_text_is_centred_on_the_given_point(surface):
    Graphik(surface).drawText("Snake", 100, 50, 20, WHITE)
    left, top, right, bottom = _drawnBounds(surface)
    # glyph outlines sit inside the font's line box, so allow a few pixels
    assert abs((left + right) / 2 - 100) <= 3
    assert abs((top + bottom) / 2 - 50) <= 3


def test_draw_button_draws_its_box_and_label(surface, monkeypatch):
    _mouseAt(monkeypatch, (0, 0), (0, 0, 0))
    Graphik(surface).drawButton(50, 20, 100, 60, RED, WHITE, 20, "Go", lambda: None)
    assert _drawnBounds(surface) == (50, 20, 149, 79)
    assert tuple(surface.get_at((52, 22)))[:3] == RED
    # the label is drawn over the middle of the box
    centre = surface.subsurface((80, 35, 40, 30))
    assert any(
        tuple(centre.get_at((x, y)))[:3] != RED for x in range(40) for y in range(30)
    )


def test_draw_button_calls_its_function_on_a_left_click_inside(surface, monkeypatch):
    calls = []
    _mouseAt(monkeypatch, (100, 50), (1, 0, 0))
    Graphik(surface).drawButton(
        50, 20, 100, 60, RED, WHITE, 20, "Go", lambda: calls.append("clicked")
    )
    assert calls == ["clicked"]


def test_draw_button_ignores_hovering_without_a_left_click(surface, monkeypatch):
    calls = []
    _mouseAt(monkeypatch, (100, 50), (0, 0, 1))
    Graphik(surface).drawButton(
        50, 20, 100, 60, RED, WHITE, 20, "Go", lambda: calls.append("clicked")
    )
    assert calls == []


@pytest.mark.parametrize(
    "position",
    [
        (49, 50),  # left of the box
        (150, 50),  # right of the box
        (100, 19),  # above the box
        (100, 80),  # below the box
    ],
)
def test_draw_button_ignores_a_click_outside(surface, monkeypatch, position):
    calls = []
    _mouseAt(monkeypatch, position, (1, 0, 0))
    Graphik(surface).drawButton(
        50, 20, 100, 60, RED, WHITE, 20, "Go", lambda: calls.append("clicked")
    )
    assert calls == []


@pytest.mark.parametrize("position", [(50, 50), (100, 20)])
def test_draw_button_counts_its_top_and_left_edges(surface, monkeypatch, position):
    # the clickable region is exactly the drawn box, so a click on its first
    # column or row counts (the old vendored copy missed these)
    calls = []
    _mouseAt(monkeypatch, position, (1, 0, 0))
    Graphik(surface).drawButton(
        50, 20, 100, 60, RED, WHITE, 20, "Go", lambda: calls.append("clicked")
    )
    assert calls == ["clicked"]
