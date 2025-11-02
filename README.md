# Ophidian
This game allows you to control an ever-increasingly growing ophidian in a virtual environment. 

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

## Controls
Key | Action
------------ | -------------
w / ↑ | move up
a / ← | move left
s / ↓ | move down
d / → | move right
f11 | fullscreen (graphical UI only)
l | toggle tick speed limit
+ / = | increase speed (faster snake)
- / _ | decrease speed (slower snake)
r | restart
q | quit

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
