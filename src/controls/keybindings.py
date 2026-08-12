"""Key bindings for both user interfaces.

The only thing that legitimately differs between the terminal and the
graphical window is how a key is *spelled* - a character (or an escape
sequence) for the terminal, a pygame key code for the window. The rules
those keys trigger are gameplay, not presentation, so they are kept out of
here entirely: this module is nothing but the spelling tables, and
Ophidian.handleKeyDownEvent() holds one copy of each rule they map onto
(see issue #126).

Keeping the tables as data also means a key can be added to one UI without
being silently forgotten in the other - the action it names has to exist
for both, and the pygame-only entries are visibly pygame-only.
"""

# Directions as stored on a SnakePart. The values are the order
# Ophidian.getLocationDirection() indexes with, so they must not be
# renumbered on their own.
DIRECTION_UP = 0
DIRECTION_LEFT = 1
DIRECTION_DOWN = 2
DIRECTION_RIGHT = 3

# A snake may not turn back through its own neck, so a direction key is
# ignored while the opposite direction is being travelled.
OPPOSITE_DIRECTIONS = {
    DIRECTION_UP: DIRECTION_DOWN,
    DIRECTION_DOWN: DIRECTION_UP,
    DIRECTION_LEFT: DIRECTION_RIGHT,
    DIRECTION_RIGHT: DIRECTION_LEFT,
}

# Non-directional actions. Named rather than bound to methods here so this
# module stays free of any dependency on Ophidian itself.
ACTION_QUIT = "quit"
ACTION_TOGGLE_TICK_SPEED_LIMIT = "toggleTickSpeedLimit"
ACTION_TOGGLE_FULLSCREEN = "toggleFullscreen"
ACTION_RESTART_RUN = "restartRun"
ACTION_CYCLE_COSMETIC = "cycleCosmetic"
ACTION_OPEN_SHOP = "openShop"

# Returned by handleKeyDownEvent() when the press replaced the board or
# held the game while the player was elsewhere, so the frame it happened in
# must not also advance the snake. Both run loops have to agree on this or
# they drift apart again (issue #117).
RESTART_SENTINEL = "restart"

# Terminal spellings. The escape sequences are what
# TextRenderer.getKeyPress() returns for the arrow keys, on Windows as well
# as on Unix.
TEXT_UI_DIRECTION_KEYS = {
    "w": DIRECTION_UP,
    "\x1b[A": DIRECTION_UP,
    "a": DIRECTION_LEFT,
    "\x1b[D": DIRECTION_LEFT,
    "s": DIRECTION_DOWN,
    "\x1b[B": DIRECTION_DOWN,
    "d": DIRECTION_RIGHT,
    "\x1b[C": DIRECTION_RIGHT,
}

TEXT_UI_ACTION_KEYS = {
    "q": ACTION_QUIT,
    "l": ACTION_TOGGLE_TICK_SPEED_LIMIT,
    "r": ACTION_RESTART_RUN,
    "c": ACTION_CYCLE_COSMETIC,
    "p": ACTION_OPEN_SHOP,
}


def buildPygameDirectionKeys(pygame):
    """The graphical spellings of the direction keys.

    Built from the supplied pygame module rather than declared at import
    time, because text mode never imports pygame at all.
    """
    return {
        pygame.K_w: DIRECTION_UP,
        pygame.K_UP: DIRECTION_UP,
        pygame.K_a: DIRECTION_LEFT,
        pygame.K_LEFT: DIRECTION_LEFT,
        pygame.K_s: DIRECTION_DOWN,
        pygame.K_DOWN: DIRECTION_DOWN,
        pygame.K_d: DIRECTION_RIGHT,
        pygame.K_RIGHT: DIRECTION_RIGHT,
    }


def buildPygameActionKeys(pygame):
    """The graphical spellings of the action keys.

    F11 has no terminal counterpart - there is no window to make
    fullscreen - so it appears here and not in TEXT_UI_ACTION_KEYS.
    """
    return {
        pygame.K_q: ACTION_QUIT,
        pygame.K_l: ACTION_TOGGLE_TICK_SPEED_LIMIT,
        pygame.K_F11: ACTION_TOGGLE_FULLSCREEN,
        pygame.K_r: ACTION_RESTART_RUN,
        pygame.K_c: ACTION_CYCLE_COSMETIC,
        pygame.K_p: ACTION_OPEN_SHOP,
    }
