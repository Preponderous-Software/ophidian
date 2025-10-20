"""
Input Handler Abstraction - Decouples input handling from UI implementation
"""
from abc import ABC, abstractmethod


class InputAction:
    """Enum-like class for input actions"""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    RESTART = "restart"
    QUIT = "quit"
    MENU = "menu"
    SELECT = "select"  # For menu selection (Enter key)
    NONE = "none"


class InputHandler(ABC):
    """Abstract base class for input handling"""
    
    @abstractmethod
    def get_input(self, timeout=None):
        """
        Get input from the user.
        Returns an InputAction or None if no input.
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up input handler resources"""
        pass


class DirectionMapper:
    """Maps input actions to game direction values"""
    
    # Direction constants matching game engine
    UP = 0
    LEFT = 1
    DOWN = 2
    RIGHT = 3
    
    @staticmethod
    def action_to_direction(action):
        """Convert InputAction to direction integer"""
        mapping = {
            InputAction.MOVE_UP: DirectionMapper.UP,
            InputAction.MOVE_DOWN: DirectionMapper.DOWN,
            InputAction.MOVE_LEFT: DirectionMapper.LEFT,
            InputAction.MOVE_RIGHT: DirectionMapper.RIGHT,
        }
        return mapping.get(action)
