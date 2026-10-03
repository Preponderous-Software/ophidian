# Ophidian

[![Play in your browser](https://img.shields.io/badge/Play-in%20your%20browser-2ea44f)](https://danielstephenson.dev/play/ophidian)

This game allows you to control an ever-increasingly growing ophidian in a virtual environment. 

## Play in your browser
Ophidian also runs in a web browser, phones included, with nothing to install:

- https://ophidian.play.danielstephenson.dev
- https://danielstephenson.dev/play (every browser game in one place)

Click or tap the page once to start it. On a phone, swipe to steer, or tap a
spot on the board to turn towards it. The browser build is the graphical UI
built with [pygbag](https://github.com/pygame-web/pygbag) from `src/`, whose
`main.py` is its entry point (`python -m pygbag --build src` builds it into
`src/build/web`); `.github/workflows/browser.yml` builds it on every pull request
and deploys it. Two things differ there: progress (`save.json`) lasts only as
long as the tab, and no usage reporting is sent at all. There is no quit key, as
closing the tab ends the game.

## Requirements
- Python 3.8 or newer (developed and tested on 3.10)
- [pygame](https://www.pygame.org/) — only for the graphical UI; `--text-ui` runs without it

## Installation
```bash
git clone https://github.com/Preponderous-Software/ophidian.git
cd ophidian
pip install -r requirements.txt
```

To run the tests or the formatter, install the development dependencies
(`pytest`, `pytest-cov`, `black`, `autoflake`) instead:
```bash
pip install -r requirements-dev.txt
```

## Usage

### Graphical UI (Default)
Run the game with the standard pygame graphical interface:
```bash
python3 src/ophidian.py
```

### Text-Based UI
Run the game with a text-based terminal interface:
```bash
python3 src/ophidian.py --text-ui
```

`./run.sh` starts the graphical UI too, after pulling the latest code and running
the tests. It and `./test.sh` pick the interpreter themselves — `python3` first,
then `python`, taking whichever reports 3.8 or newer — so set `PYTHON` to
override that choice:
```bash
PYTHON=.venv/bin/python ./test.sh
```

The text-based UI is perfect for:
- Environments where graphical display is not available
- Running the game over SSH
- Low-resource systems
- Terminal enthusiasts

## Pickups
Most of what spawns on the board is food, which grows the ophidian by one segment.
The rest are power-ups, which grant a temporary effect instead of growing you:

Power-up | Effect | Duration | Chance per pickup
------------ | ------------- | ------------- | -------------
Speed Boost | the ophidian moves twice as fast | 5s | 15%
Invincibility | collisions with your own body no longer end the run | 3s | 5%
Score Multiplier | food is worth double points | 10s | 15%

Whatever is currently running gets its own indicator on the HUD, in both UIs: the
symbol the power-up is drawn with on the grid, its name, the whole seconds left, and
a meter that drains as its timer does. The graphical UI fills that meter with the
power-up's own color; the text UI draws it as `[██████░░░░]`. In the text UI,
power-ups appear on the grid as their own symbol and are listed in the legend
beneath it.

## Scoring
Points are banked as they are earned, one award per piece of food eaten. An award is
worth a flat 10 points plus one point per percent of the grid the ophidian already
fills, so bites get more valuable as the board fills up. While the Score Multiplier
runs, each award is doubled — points earned before it are left alone, and points
earned after it expires go back to normal. Both UIs mark the score with `(x2)` for
as long as the multiplier lasts.

Note that the score resets at the start of each level, alongside the board.

When a run ends, the score it finished on is reported in the obituary that both UIs
show, alongside the all-time best in the chronicle printed beneath it.

## Controls
Key | Action
------------ | -------------
w / ↑ | move up
a / ← | move left
s / ↓ | move down
d / → | move right
space | pause / resume
f11 | fullscreen (graphical UI only)
l | toggle tick speed limit
c | cycle selected cosmetic skin
p | open the upgrade shop
r | restart
q | quit
swipe / tap | steer: a swipe turns the way it travelled, a tap turns towards where it landed (graphical UI, mouse or touch)

Letter keys are matched regardless of case in either UI, so the controls keep working
with Caps Lock on.

While paused, the ophidian stops where it stands, the tick count stops rising, and any
power-up you are carrying keeps the time it had left rather than draining away. Both
UIs say on screen that the run is held. Restarting a paused run starts the new one
unpaused.

Opening the shop holds a power-up's timer the same way, so browsing upgrades never costs
you the boost you are carrying.

When a run ends in a collision, both UIs hold the board it ended on for a few seconds
before the next one starts: the graphical UI turns it red and then shows the obituary,
and the text UI prints a collision notice under the board, followed by the obituary.

## Usage reporting
Usage reporting is on by default: Ophidian sends its name (`ophidian`), the version in
`version.txt` and two kinds of event to [trace](https://github.com/Stephenson-Software/trace)
at `https://trace.danielstephenson.dev`, so that its maintainers can see the game is still
played:

Event | When | What it carries
------------ | ------------- | -------------
`startup` | the game starts | the program name (`ophidian`) and the version in `version.txt`
`run-ended` | a run ends | how it ended: `collision`, `restart` or `quit`, and the version in `version.txt`

No usernames, hostnames, IP addresses, paths, save contents or scores are ever sent. Reporting
happens on a background thread, never delays a frame, and never stops the game if the
server is unreachable.

The first time the game starts it says so once on the console and writes a `usageReporting`
block to `save.json` (created next to where the game is run):
```json
"usageReporting": {
  "enabled": true,
  "endpoint": "https://trace.danielstephenson.dev",
  "key": "..."
}
```
To turn it off, any one of these is enough:

- set `"enabled": false` in that block of `save.json`
- set the environment variable `TRACE_USAGE_REPORTING=off` (also `false`, `0`, `no`), which
  turns off every program that reports to trace
- set the environment variable `DO_NOT_TRACK=1` (see [consoledonottrack.com](https://consoledonottrack.com))

The environment variables win over `save.json`. `endpoint` is where events are posted and
`key` identifies the game to the server; neither normally needs changing. The client itself
is a vendored copy of [trace-client-python](https://github.com/Stephenson-Software/trace-client-python)
at `src/lib/trace_client.py`, and the test suite never contacts the real server.

Details: https://github.com/Stephenson-Software/trace#usage-reporting

## Support
You can find the support discord server [here](https://discord.gg/49J4RHQxhy).

## Authors and acknowledgement
### Developers
Name | Main Contributions
------------ | -------------
Daniel Stephenson | Creator

## Libraries
This project makes use of [graphik](https://github.com/Preponderous-Software/graphik) and [py_env_lib](https://github.com/Preponderous-Software/py_env_lib).

## 📄 License

This project is licensed under the **Preponderous Non-Commercial License (Preponderous-NC)**.  
It is free to use, modify, and self-host for **non-commercial** purposes, but **commercial use requires a separate license**.

> **Disclaimer:** *Preponderous Software is not a legal entity.*  
> All rights to works published under this license are reserved by the copyright holder, **Daniel McCoy Stephenson**.

Full license text:  
[https://github.com/Preponderous-Software/preponderous-nc-license/blob/main/LICENSE.md](https://github.com/Preponderous-Software/preponderous-nc-license/blob/main/LICENSE.md)
