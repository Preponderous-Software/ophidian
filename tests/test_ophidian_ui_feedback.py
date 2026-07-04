from textui.textrenderer import TextRenderer

from ophidian import Ophidian
from progression.cosmetics import SKINS_BY_ID


def _makeGame(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    return Ophidian(useTextUI=True)


def test_cycle_selected_cosmetic_updates_live_snake_part_color(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["unlockedCosmetics"] = ["default", "ember"]
    game.saveManager.data["selectedCosmetic"] = "default"

    game.cycleSelectedCosmetic()

    assert game.saveManager.data["selectedCosmetic"] == "ember"
    assert game.selectedSnakePart.getColor() == SKINS_BY_ID["ember"]["color"]


def test_cycle_selected_cosmetic_wraps_and_updates_color_each_time(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    game.saveManager.data["unlockedCosmetics"] = ["default", "ember", "frost"]
    game.saveManager.data["selectedCosmetic"] = "frost"

    game.cycleSelectedCosmetic()

    assert game.saveManager.data["selectedCosmetic"] == "default"
    # default has no fixed color, but it must differ from frost's fixed color
    assert game.selectedSnakePart.getColor() != SKINS_BY_ID["frost"]["color"]


def test_notify_is_console_only_in_text_ui_mode(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)

    game.notify("hello")

    # text UI has no pygame banner queue to populate
    assert game.uiMessageQueue == []


def test_notify_queues_messages_instead_of_clobbering(tmp_path, monkeypatch):
    # regression test: checkForLevelProgressAndReinitialize's ascension
    # notify() is immediately followed by initialize()'s biome-arrival
    # notify() in the same synchronous call chain, before any frame is ever
    # drawn - a single-slot uiMessage would silently lose the first message
    game = _makeGame(monkeypatch, tmp_path)
    game.config.useTextUI = False  # pretend pygame mode without a real display

    game.notify("The ophidian ascends! (Ascension 1)")
    game.notify("Medusa enters The Sunken Grove.")

    assert list(game.uiMessageQueue) == [
        "The ophidian ascends! (Ascension 1)",
        "Medusa enters The Sunken Grove.",
    ]
