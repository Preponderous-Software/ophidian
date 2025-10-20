"""
Text UI Renderer Adapter - Adapts TextRenderer to GameRenderer interface
"""
from src.graphics.game_renderer import GameRenderer


class TextUIRenderer(GameRenderer):
    """Renderer adapter for text-based UI"""
    
    def __init__(self, text_renderer):
        self.text_renderer = text_renderer
    
    def render_game(self, game_state):
        """Render game state using text UI"""
        self.text_renderer.render_grid(
            game_state['environment_repository'],
            game_state['snake_part_repository'],
            game_state['collision']
        )
        
        self.text_renderer.render_stats(
            game_state['level'],
            game_state['snake_length'],
            game_state['current_score'],
            game_state['cumulative_score'],
            game_state['progress_percentage']
        )
        
        self.text_renderer.render_controls()
    
    def render_menu(self, menu_options, selected_index):
        """Render menu using text UI"""
        self.text_renderer.render_menu(
            "Ophidian - Main Menu",
            menu_options,
            selected_index
        )
    
    def cleanup(self):
        """Clean up text renderer"""
        self.text_renderer.disable_raw_mode()
