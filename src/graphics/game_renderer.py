"""
Renderer Abstraction - Decouples rendering from UI implementation
"""
from abc import ABC, abstractmethod


class GameRenderer(ABC):
    """Abstract base class for game rendering"""
    
    @abstractmethod
    def render_game(self, game_state):
        """
        Render the game state.
        game_state should contain all necessary information for rendering.
        """
        pass
    
    @abstractmethod
    def render_menu(self, menu_options, selected_index):
        """Render a menu"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up renderer resources"""
        pass
