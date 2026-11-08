"""src/main.py, the entry point pygbag runs for the browser build.

It has no function to call: importing it starts the game, so each test
loads a fresh copy of the file with the game swapped for a recording
stand-in, and never opens a window.
"""

import importlib.util
import os

import pygame

from ophidian import Ophidian

MAIN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "main.py"
)


def _runMain(monkeypatch):
    events = []

    def recordingInit(self, *args, **kwargs):
        events.append(("init", self, args, kwargs))

    async def recordingRunPygameUI(self):
        # only reached when the coroutine is awaited, not merely created
        events.append(("runPygameUI", self))

    monkeypatch.setattr(Ophidian, "__init__", recordingInit)
    monkeypatch.setattr(Ophidian, "runPygameUI", recordingRunPygameUI)

    # loaded under its own name and kept out of sys.modules, so every test
    # runs the file's top level again
    spec = importlib.util.spec_from_file_location("browser_main", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, events


def test_importing_main_builds_one_game_in_graphical_mode(monkeypatch):
    _, events = _runMain(monkeypatch)

    inits = [event for event in events if event[0] == "init"]
    assert len(inits) == 1
    # no arguments means useTextUI=False and no --record path: the browser
    # build has neither a terminal nor a command line
    assert inits[0][2:] == ((), {})


def test_importing_main_runs_the_pygame_loop_of_that_game_to_completion(
    monkeypatch,
):
    _, events = _runMain(monkeypatch)

    assert [event[0] for event in events] == ["init", "runPygameUI"]
    assert events[1][1] is events[0][1]


def test_main_imports_pygame_itself_for_pygbag(monkeypatch):
    # pygbag installs only the packages main.py imports, and Ophidian imports
    # pygame lazily, so this import is what gets pygame into the browser build
    module, _ = _runMain(monkeypatch)

    assert module.pygame is pygame
