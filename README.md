# Ophidian
This game allows you to control an ever-increasingly growing ophidian in a virtual environment. 

## Running the Game
To run the game with the graphical UI (default):
```
python run.py
```

To run the game with the text-based UI:
```
python run.py --text-ui
``` 

## Running Tests
To run the test suite:
```
python -m pytest tests
``` 

## Controls
### Graphical UI
| Key | Action                  |
|-----|-------------------------|
| w   | move up                 |
| a   | move left               |
| s   | move down               |
| d   | move right              |
| f11 | fullscreen              |
| l   | toggle tick speed limit |
| r   | restart                 |
| q   | quit                    |

### Text-based UI
| Key       | Action       |
|-----------|--------------|
| w or ↑    | move up      |
| a or ←    | move left    |
| s or ↓    | move down    |
| d or →    | move right   |
| r         | restart      |
| q         | quit         |
| ESC       | return to menu |

## Support
You can find the support discord server [here](https://discord.gg/49J4RHQxhy).

## Authors and acknowledgement
### Developers
| Name              | Main Contributions |
|-------------------|--------------------|
| Daniel Stephenson | Creator            |

## Libraries
This project makes use of [graphik](https://github.com/Preponderous-Software/graphik) and [py_env_lib](https://github.com/Preponderous-Software/py_env_lib).