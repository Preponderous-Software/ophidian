import os
import sys
import termios
import tty
import select

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
        self.last_render = None  # Cache last render to avoid unnecessary redraws

    def clear_screen(self):
        """Clear terminal screen efficiently"""
        # Use ANSI escape codes instead of os.system for better performance
        if os.name != 'nt':
            # Unix/Linux/Mac - use ANSI codes
            sys.stdout.write('\033[2J\033[H')
            sys.stdout.flush()
        else:
            # Windows - use os.system as fallback
            os.system('cls')

    def render_grid(self, environment_repository, snake_part_repository, collision):
        """Render the game grid as text with performance optimizations"""
        # Build the entire frame in memory first, then print once
        output_lines = []
        
        rows = environment_repository.get_rows()
        cols = environment_repository.get_columns()
        
        # Create a display grid
        display = []
        for _ in range(cols):
            display.append(['.'] * rows)
        
        # Mark snake parts
        snake_parts = snake_part_repository.get_all()
        for snake_part in snake_parts:
            location = environment_repository.get_location_of_entity(snake_part)
            if location is not None:
                x = location.getX()
                y = location.getY()
                display[y][x] = 'S'
        
        # Mark head of snake (first snake part)
        if len(snake_parts) > 0:
            head_location = environment_repository.get_location_of_entity(snake_parts[0])
            if head_location is not None:
                hx = head_location.getX()
                hy = head_location.getY()
                display[hy][hx] = 'H'
        
        # Mark food
        for location_id in environment_repository.get_locations():
            location = environment_repository.get_location_by_id(location_id)
            for entity_id in location.getEntities():
                entity = location.getEntity(entity_id)
                if hasattr(entity, 'getName') and entity.getName() == "Food":
                    x = location.getX()
                    y = location.getY()
                    display[y][x] = 'F'
        
        # Build output in memory
        output_lines.append('┌' + '─' * (rows * 2 + 1) + '┐')
        
        for row in display:
            output_lines.append('│ ' + ' '.join(row) + ' │')
        
        output_lines.append('└' + '─' * (rows * 2 + 1) + '┘')
        
        if collision:
            output_lines.append("\n[!] COLLISION! The ophidian collides with itself!")
        
        output_lines.append("\nLegend: H=Head, S=Snake, F=Food, .=Empty")
        
        # Clear and print all at once
        self.clear_screen()
        print('\n'.join(output_lines))

    def render_stats(self, level, snake_length, current_score, cumulative_score, percentage):
        """Render game statistics"""
        print(f"\nLevel: {level}")
        print(f"Length: {snake_length}")
        print(f"Score: {current_score} | {cumulative_score}")
        print(f"Progress: {int(percentage * 100)}%")
        
        # Draw progress bar
        bar_length = 30
        filled = int(bar_length * percentage)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"[{bar}]")

    def render_controls(self):
        """Render control instructions"""
        print("\nControls: w/↑=Up, a/←=Left, s/↓=Down, d/→=Right, r=Restart, q=Quit, ESC=Menu")

    def render_menu(self, title, options, selected_index):
        """Render a text-based menu"""
        self.clear_screen()
        print(f"\n{title}")
        print("=" * len(title))
        print()
        
        for i, option in enumerate(options):
            if i == selected_index:
                print(f"> {option}")
            else:
                print(f"  {option}")
        
        print("\nControls: w/↑=Up, s/↓=Down, ENTER=Select, q=Quit")

    def enable_raw_mode(self):
        """Enable raw mode for non-blocking keyboard input"""
        if os.name != 'nt':
            try:
                self.old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (termios.error, OSError):
                # No TTY available (e.g., in CI environment)
                # Skip raw mode - test mode will handle input differently
                self.old_settings = None

    def disable_raw_mode(self):
        """Disable raw mode and restore terminal settings"""
        if os.name != 'nt' and self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key_press(self, timeout=0):
        """
        Get a key press without blocking (non-blocking input)
        Returns the key pressed or None if no key was pressed
        Handles arrow keys by reading full escape sequences
        """
        if os.name != 'nt':
            # Unix/Linux/Mac
            if select.select([sys.stdin], [], [], timeout)[0]:
                ch = sys.stdin.read(1)
                # Check if this is the start of an escape sequence
                if ch == '\x1b':
                    # Try to read the rest of the arrow key sequence
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            if select.select([sys.stdin], [], [], 0.01)[0]:
                                ch3 = sys.stdin.read(1)
                                # Return full escape sequence
                                return '\x1b[' + ch3
                    return ch
                return ch
        else:
            # Windows
            if msvcrt and msvcrt.kbhit():
                ch = msvcrt.getch()
                # Handle arrow keys on Windows
                if ch in (b'\xe0', b'\x00'):
                    ch2 = msvcrt.getch()
                    # Map Windows arrow keys to escape sequences
                    arrow_map = {
                        b'H': '\x1b[A',  # Up
                        b'P': '\x1b[B',  # Down
                        b'M': '\x1b[C',  # Right
                        b'K': '\x1b[D',  # Left
                    }
                    return arrow_map.get(ch2, ch2.decode('utf-8', errors='ignore'))
                return ch.decode('utf-8', errors='ignore')
        return None
