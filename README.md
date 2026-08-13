# Ophidian
This game allows you to control an ever-increasingly growing ophidian in a virtual environment. 

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
python src/ophidian.py
```

### Text-Based UI
Run the game with a text-based terminal interface:
```bash
python src/ophidian.py --text-ui
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

Letter keys are matched regardless of case, so the controls keep working in both UIs
with Caps Lock on.

While paused, the ophidian stops where it stands, the tick count stops rising, and any
power-up you are carrying keeps the time it had left rather than draining away. Both
UIs say on screen that the run is held. Restarting a paused run starts the new one
unpaused.

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
