"""Entry point of the browser build (pygbag), which packages src/ and runs
its main.py. The desktop game still starts from src/ophidian.py (run.sh);
both run the same async pygame loop, Ophidian.runPygameUI.

In a browser the game is WebOphidian: the same 2D game, which also draws
itself in the page's 3D view when the player turns that on (strata_view/
web.py). Its files are downloaded only then.
"""

import asyncio
import sys

# pygbag decides which runtime packages to install by scanning main.py's
# imports, and Ophidian imports pygame lazily (text mode never needs it), so
# without this the browser build gets no pygame at all.
import pygame  # noqa: F401

from ophidian import Ophidian


def chooseGame(platform=None):
    """The game class to run: WebOphidian in a browser, so the page's 3D
    toggle works; Ophidian anywhere else, or when graphik's 3D view isn't
    in the build (then the toggle is marked unavailable, with the reason)."""
    platform = sys.platform if platform is None else platform
    if platform != "emscripten":
        return Ophidian
    try:
        from strata_view.web import WebOphidian
    except ImportError as error:
        print("No 3D view in this build:", error)
        try:
            from preponderous.graphik.grid3d.web import set3D

            set3D(False, "this build has no 3D view")
        except ImportError:
            pass
        return Ophidian
    return WebOphidian


async def main():
    await chooseGame()().runPygameUI()


asyncio.run(main())
