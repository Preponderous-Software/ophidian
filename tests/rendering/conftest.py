import os

# Must happen before pygame's video subsystem is ever initialized (i.e.
# before the first pygame.init()/pygame.display.init() call anywhere in the
# process) - SDL reads these at init time, letting pygame run fully headless
# with no real display, which is what actually lets this whole directory
# exercise the drawing code paths instead of just import/compile-checking
# them.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from ophidian import Ophidian


@pytest.fixture
def pygameGame():
    """A real Ophidian instance in graphical (pygame) mode, running against
    the headless dummy video driver. Not chdir'd to a tmp_path like the
    text-UI test fixtures, because __init__ loads src/media/icon.PNG via a
    path relative to the working directory - so any save.json it writes
    lands in the repo root and is cleaned up here instead."""
    game = Ophidian(useTextUI=False)
    try:
        yield game
    finally:
        pygame.quit()
        savePath = os.path.join(os.getcwd(), "save.json")
        if os.path.exists(savePath):
            os.remove(savePath)


def regionHasNonBackgroundPixel(surface, rect, backgroundColor):
    """True if any sampled pixel in rect differs from backgroundColor.

    Used instead of asserting exact pixel colors/glyph shapes, since font
    anti-aliasing specifics aren't worth pinning down - what matters for
    these tests is that something was actually drawn where it should be.
    """
    x, y, w, h = rect
    background = tuple(backgroundColor)
    for sampleX in range(x, x + w, 2):
        for sampleY in range(y, y + h, 2):
            if tuple(surface.get_at((sampleX, sampleY)))[:3] != background:
                return True
    return False
