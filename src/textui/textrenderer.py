import math
import os
import sys
import termios
import tty
import select

from scoring.scoring import formatScoreLabel

# Windows-specific import
try:
    import msvcrt
except ImportError:
    msvcrt = None


# @author Daniel McCoy Stephenson
# @since October 15th, 2025
class TextRenderer:
    def __init__(self, config):
        self.config = config
        self.old_settings = None

    def clearScreen(self):
        os.system("clear" if os.name != "nt" else "cls")

    def renderGrid(self, environment, snakeParts, collision):
        """Render the game grid as text"""
        self.clearScreen()

        grid = environment.getGrid()
        rows = grid.getRows()
        cols = grid.getColumns()

        # Create a display grid
        display = []
        for _ in range(cols):
            display.append(["."] * rows)

        # Mark snake parts
        for snakePart in snakeParts:
            locationID = snakePart.getLocationID()
            if locationID is not None:
                location = grid.getLocation(locationID)
                x = location.getX()
                y = location.getY()
                display[y][x] = "S"

        # Mark head of snake
        if len(snakeParts) > 0:
            headLocationID = snakeParts[0].getLocationID()
            if headLocationID is not None:
                headLocation = grid.getLocation(headLocationID)
                hx = headLocation.getX()
                hy = headLocation.getY()
                display[hy][hx] = "H"

        # Mark food and power-ups. A power-up supplies its own symbol and
        # display name (the way Food already supplies its color), so this
        # renderer stays independent of the power-up registry and needs no
        # change when a new power-up type is added.
        powerUpLegend = {}
        for locationId in grid.getLocations():
            location = grid.getLocation(locationId)
            for eid in location.getEntities():
                entity = location.getEntity(eid)
                x = location.getX()
                y = location.getY()
                if entity.getName() == "Food":
                    display[y][x] = "F"
                elif entity.getName() == "PowerUp":
                    symbol = entity.getTextSymbol()
                    display[y][x] = symbol
                    powerUpLegend[symbol] = entity.getDisplayName()

        # Print border
        print("┌" + "─" * (rows * 2 + 1) + "┐")

        # Print grid
        for row in display:
            print("│ " + " ".join(row) + " │")

        # Print border
        print("└" + "─" * (rows * 2 + 1) + "┘")

        if collision:
            print("\n[!] COLLISION! The ophidian collides with itself!")

        # power-up entries are built from what is actually on the board, so
        # the legend can never advertise a symbol the player can't see
        legendEntries = ["H=Head", "S=Snake", "F=Food"]
        legendEntries += [
            f"{symbol}={name}" for symbol, name in sorted(powerUpLegend.items())
        ]
        legendEntries.append(".=Empty")
        print("\nLegend: " + ", ".join(legendEntries))

    def renderMessage(self, message):
        """Render the current player-facing notification, if any.

        The text-mode counterpart of the pygame UiBanner: it receives an
        already-resolved string, so this renderer stays independent of the
        graphical UI package.
        """
        if not message:
            return
        print(f"\n>>> {message}")

    def renderStats(self, level, snakeLength, score, percentage, scoreMultiplier=1.0):
        """Render game statistics

        scoreMultiplier arrives as a plain number, so the player can tell a
        doubled bite from a normal one at the moment it is banked rather than
        only from the power-up's countdown. How it is annotated comes from
        scoring.formatScoreLabel, which the graphical HUD reads too, so the
        two UIs cannot disagree about it. Defaults to 1.0 (no annotation) so
        a caller that doesn't care about multipliers is unaffected.
        """
        print(f"\nLevel: {level}")
        print(f"Length: {snakeLength}")
        print(f"Score: {formatScoreLabel(score, scoreMultiplier)}")
        print(f"Progress: {int(percentage * 100)}%")

        # Draw progress bar
        bar_length = 30
        filled = int(bar_length * percentage)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}]")

    def renderHud(self, currency, activeUpgradeLabels, powerUpStatuses=None):
        """Currency, active-upgrades and active-power-up readout, always
        visible (not just inside the shop) so the player isn't stuck checking
        their balance or what they own by reopening the shop mid-run.

        powerUpStatuses is a list of (label, secondsRemaining) pairs whose
        seconds arrive as plain numbers and are formatted here, mirroring
        renderMessage's already-resolved string so this renderer stays
        independent of both the graphical UI package and the power-up
        registry. Gameplay omits power-ups with no time left, so every pair
        handed over is worth a line.
        """
        print(f"Currency: {currency}")
        if activeUpgradeLabels:
            print("Active upgrades: " + ", ".join(activeUpgradeLabels))
        for label, secondsRemaining in powerUpStatuses or []:
            print(f"{label}: {math.ceil(secondsRemaining)}s")

    def renderControls(self):
        """Render control instructions"""
        print(
            "\nControls: w/↑=Up, a/←=Left, s/↓=Down, d/→=Right, "
            "c=Cycle skin, p=Shop, l=Toggle tick speed limit, r=Restart, q=Quit"
        )

    def enableRawMode(self):
        """Enable raw mode for non-blocking keyboard input"""
        if os.name != "nt":
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

    def disableRawMode(self):
        """Disable raw mode and restore terminal settings"""
        if os.name != "nt" and self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def getKeyPress(self, timeout=0):
        """
        Get a key press without blocking (non-blocking input)
        Returns the key pressed or None if no key was pressed
        Handles arrow keys by reading full escape sequences
        """
        if os.name != "nt":
            # Unix/Linux/Mac
            if select.select([sys.stdin], [], [], timeout)[0]:
                ch = sys.stdin.read(1)
                # Check if this is the start of an escape sequence
                if ch == "\x1b":
                    # Try to read the rest of the arrow key sequence
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        ch2 = sys.stdin.read(1)
                        if ch2 == "[":
                            if select.select([sys.stdin], [], [], 0.01)[0]:
                                ch3 = sys.stdin.read(1)
                                # Return full escape sequence
                                return "\x1b[" + ch3
                    return ch
                return ch
        else:
            # Windows
            if msvcrt and msvcrt.kbhit():
                ch = msvcrt.getch()
                # Handle arrow keys on Windows
                if ch in (b"\xe0", b"\x00"):
                    ch2 = msvcrt.getch()
                    # Map Windows arrow keys to escape sequences
                    arrow_map = {
                        b"H": "\x1b[A",  # Up
                        b"P": "\x1b[B",  # Down
                        b"M": "\x1b[C",  # Right
                        b"K": "\x1b[D",  # Left
                    }
                    return arrow_map.get(ch2, ch2.decode("utf-8", errors="ignore"))
                return ch.decode("utf-8", errors="ignore")
        return None
