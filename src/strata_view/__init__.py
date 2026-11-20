"""Ophidian's 3D view, drawn with Strata (desktop Linux and Windows).

scene.py maps game state to plain shapes and needs no GPU; renderer.py draws
them with Strata's Python binding; game.py runs the game in a Strata window.
On Linux and Windows `python3 src/ophidian.py` opens it by default and falls
back to the 2D window when Strata can't start (`--2d` skips it).
tools/strata_snapshot.py renders real game states headless to PNGs.
"""


class StrataUnavailable(Exception):
    """The 3D window can't start here: the strata-engine package is missing,
    the Strata library couldn't be loaded, or no window could be opened.
    The message says which, in words a player can act on."""
