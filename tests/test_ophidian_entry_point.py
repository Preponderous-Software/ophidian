"""How the game is started: run() picks the loop for the chosen UI, and the
script refuses --record before building a game it could not record.

Every other test drives runTextUI() or runPygameUI() directly, so the
dispatch between them, and the command-line guard in front of it, had no
test of their own.
"""

import os
import subprocess
import sys

import pytest

from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from recording.usd_recording import REQUIREMENTS_HINT, UsdRecording

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "src", "ophidian.py")


def _makeGame(monkeypatch, tmp_path, useTextUI=True):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    game = Ophidian(useTextUI=True)
    game.config.useTextUI = useTextUI
    return game


def _recordLoops(monkeypatch):
    loops = []

    def runTextUI(self):
        loops.append("text")

    async def runPygameUI(self):
        loops.append("pygame")

    monkeypatch.setattr(Ophidian, "runTextUI", runTextUI)
    monkeypatch.setattr(Ophidian, "runPygameUI", runPygameUI)
    return loops


def test_run_starts_the_text_loop_in_text_mode(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, useTextUI=True)
    loops = _recordLoops(monkeypatch)

    game.run()

    assert loops == ["text"]


def test_run_starts_the_async_pygame_loop_in_graphical_mode(tmp_path, monkeypatch):
    # runPygameUI is a coroutine; run() must drive it to completion rather
    # than just create it, or the window would never open
    game = _makeGame(monkeypatch, tmp_path, useTextUI=False)
    loops = _recordLoops(monkeypatch)

    game.run()

    assert loops == ["pygame"]


@pytest.mark.skipif(
    UsdRecording.isAvailable(),
    reason="usd-recorder is installed, so --record is accepted",
)
def test_record_without_usd_recorder_exits_with_the_install_hint(tmp_path):
    # run as a script, since the guard lives under `if __name__ ==
    # "__main__"`; it exits before an Ophidian is built, so no window opens
    # and no save is touched
    result = subprocess.run(
        [sys.executable, SCRIPT, "--record", str(tmp_path / "run.usda")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1
    assert result.stderr.strip() == (
        "--record needs the optional usd-recorder package: " + REQUIREMENTS_HINT
    )
    assert result.stdout == ""
    assert not (tmp_path / "run.usda").exists()
    assert not (tmp_path / "save.json").exists()
