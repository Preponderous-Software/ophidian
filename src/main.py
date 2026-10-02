"""Entry point of the browser build (pygbag), which packages src/ and runs
its main.py. The desktop game still starts from src/ophidian.py (run.sh);
both run the same async pygame loop, Ophidian.runPygameUI.
"""

import asyncio

# pygbag decides which runtime packages to install by scanning main.py's
# imports, and Ophidian imports pygame lazily (text mode never needs it), so
# without this the browser build gets no pygame at all.
import pygame  # noqa: F401

from ophidian import Ophidian


async def main():
    await Ophidian().runPygameUI()


asyncio.run(main())
