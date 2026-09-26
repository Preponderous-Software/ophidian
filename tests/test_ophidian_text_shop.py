"""The text UI's shop menu, openTextShop().

The pure purchase rules live in tests/progression/test_shop.py; these cover
what the text UI wraps around them - the listing the player reads, how a
typed choice is turned into an upgrade, that a purchase reaches the save
file, and that the terminal is handed back in raw mode however the menu is
left.
"""

import builtins
import json

import pytest

from textui.textrenderer import TextRenderer

from ophidian import Ophidian


def _makeGame(monkeypatch, tmp_path, currency=0, purchasedUpgrades=None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TextRenderer, "enableRawMode", lambda self: None)
    monkeypatch.setattr(TextRenderer, "disableRawMode", lambda self: None)
    game = Ophidian(useTextUI=True)
    game.saveManager.path = str(tmp_path / "shop-save.json")
    game.saveManager.data["currency"] = currency
    game.saveManager.data["purchasedUpgrades"] = list(purchasedUpgrades or [])
    return game


def _typeChoice(monkeypatch, choice):
    monkeypatch.setattr(builtins, "input", lambda prompt="": choice)


def _savedData(tmp_path):
    with open(tmp_path / "shop-save.json") as f:
        return json.load(f)


def test_the_listing_shows_the_balance_and_every_upgrade_in_order(
    tmp_path, monkeypatch, capsys
):
    game = _makeGame(monkeypatch, tmp_path, currency=12)
    _typeChoice(monkeypatch, "0")

    game.openTextShop()

    out = capsys.readouterr().out
    assert "Currency: 12" in out
    assert out.index("1. Head Start - cost 10") < out.index("2. Slow Starter - cost 15")
    assert out.index("2. Slow Starter - cost 15") < out.index(
        "3. Second Wind - cost 25"
    )
    assert "0. Exit shop" in out


def test_the_listing_tags_only_the_upgrades_already_owned(
    tmp_path, monkeypatch, capsys
):
    game = _makeGame(monkeypatch, tmp_path, purchasedUpgrades=["slow_starter"])
    _typeChoice(monkeypatch, "0")

    game.openTextShop()

    out = capsys.readouterr().out
    assert "2. Slow Starter - cost 15 (owned)" in out
    assert "1. Head Start - cost 10\n" in out
    assert "3. Second Wind - cost 25\n" in out


def test_a_numbered_choice_buys_that_upgrade_and_saves_it(
    tmp_path, monkeypatch, capsys
):
    game = _makeGame(monkeypatch, tmp_path, currency=30)
    _typeChoice(monkeypatch, "3")

    game.openTextShop()

    assert "Purchased Second Wind for 25 currency." in capsys.readouterr().out
    saved = _savedData(tmp_path)
    assert saved["currency"] == 5
    assert saved["purchasedUpgrades"] == ["second_wind"]


def test_a_choice_with_surrounding_whitespace_still_buys(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path, currency=10)
    _typeChoice(monkeypatch, "  1 \n")

    game.openTextShop()

    assert game.saveManager.data["purchasedUpgrades"] == ["head_start"]


def test_a_refused_purchase_reports_why_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    game = _makeGame(monkeypatch, tmp_path, currency=3)
    _typeChoice(monkeypatch, "1")

    game.openTextShop()

    assert (
        "Not enough currency for Head Start (costs 10, you have 3)."
        in capsys.readouterr().out
    )
    assert game.saveManager.data["currency"] == 3
    assert not (tmp_path / "shop-save.json").exists()


def test_rebuying_an_owned_upgrade_is_refused(tmp_path, monkeypatch, capsys):
    game = _makeGame(
        monkeypatch, tmp_path, currency=50, purchasedUpgrades=["head_start"]
    )
    _typeChoice(monkeypatch, "1")

    game.openTextShop()

    assert "Head Start is already owned." in capsys.readouterr().out
    assert game.saveManager.data["currency"] == 50
    assert game.saveManager.data["purchasedUpgrades"] == ["head_start"]


@pytest.mark.parametrize("choice", ["0", "", "   "])
def test_zero_or_a_blank_line_leaves_without_buying(
    tmp_path, monkeypatch, capsys, choice
):
    game = _makeGame(monkeypatch, tmp_path, currency=100)
    _typeChoice(monkeypatch, choice)

    game.openTextShop()

    out = capsys.readouterr().out
    assert "Invalid selection." not in out
    assert "Purchased" not in out
    assert game.saveManager.data["currency"] == 100
    assert not (tmp_path / "shop-save.json").exists()


@pytest.mark.parametrize("choice", ["4", "99", "two", "1.5"])
def test_a_choice_the_menu_does_not_list_is_invalid(
    tmp_path, monkeypatch, capsys, choice
):
    game = _makeGame(monkeypatch, tmp_path, currency=100)
    _typeChoice(monkeypatch, choice)

    game.openTextShop()

    assert "Invalid selection." in capsys.readouterr().out
    assert game.saveManager.data["currency"] == 100
    assert game.saveManager.data["purchasedUpgrades"] == []


@pytest.mark.xfail(
    strict=True,
    reason="issue #145: a negative choice indexes the upgrade list from the end",
)
@pytest.mark.parametrize("choice", ["-1", "-2"])
def test_a_negative_choice_is_invalid(tmp_path, monkeypatch, capsys, choice):
    game = _makeGame(monkeypatch, tmp_path, currency=100)
    _typeChoice(monkeypatch, choice)

    game.openTextShop()

    assert "Invalid selection." in capsys.readouterr().out
    assert game.saveManager.data["purchasedUpgrades"] == []


def _recordRawMode(monkeypatch):
    calls = []
    monkeypatch.setattr(
        TextRenderer, "disableRawMode", lambda self: calls.append("disable")
    )
    monkeypatch.setattr(
        TextRenderer, "enableRawMode", lambda self: calls.append("enable")
    )
    return calls


def test_raw_mode_is_off_while_the_menu_reads_a_line(tmp_path, monkeypatch):
    # input() needs a cooked terminal: in raw mode the player's Enter would
    # never end the line
    game = _makeGame(monkeypatch, tmp_path)
    calls = _recordRawMode(monkeypatch)

    def readChoice(prompt=""):
        calls.append("input")
        return "0"

    monkeypatch.setattr(builtins, "input", readChoice)

    game.openTextShop()

    assert calls == ["disable", "input", "enable"]


def test_raw_mode_is_restored_even_if_reading_the_choice_fails(tmp_path, monkeypatch):
    game = _makeGame(monkeypatch, tmp_path)
    calls = _recordRawMode(monkeypatch)

    def closedStdin(prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", closedStdin)

    with pytest.raises(EOFError):
        game.openTextShop()

    assert calls == ["disable", "enable"]
