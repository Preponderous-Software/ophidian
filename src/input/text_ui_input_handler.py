"""
Text UI Input Handler - Handles keyboard input for text-based UI
"""
from src.input.input_handler import InputHandler, InputAction


class TextUIInputHandler(InputHandler):
    """Input handler for text-based UI"""
    
    def __init__(self, text_renderer):
        self.text_renderer = text_renderer
    
    def get_input(self, timeout=None):
        """Get input from text UI"""
        key = self.text_renderer.get_key_press(timeout=timeout or 0.01)
        
        if not key:
            return InputAction.NONE
        
        # Map keys to actions
        if key in ('w', 'W', '\x1b[A'):  # Up
            return InputAction.MOVE_UP
        elif key in ('a', 'A', '\x1b[D'):  # Left
            return InputAction.MOVE_LEFT
        elif key in ('s', 'S', '\x1b[B'):  # Down
            return InputAction.MOVE_DOWN
        elif key in ('d', 'D', '\x1b[C'):  # Right
            return InputAction.MOVE_RIGHT
        elif key in ('r', 'R'):  # Restart
            return InputAction.RESTART
        elif key in ('q', 'Q'):  # Quit
            return InputAction.QUIT
        elif key == '\x1b':  # ESC - Return to menu
            return InputAction.MENU
        elif key in ('\r', '\n'):  # Enter - Select
            return InputAction.SELECT
        
        return InputAction.NONE
    
    def cleanup(self):
        """Clean up text UI input resources"""
        self.text_renderer.disable_raw_mode()
