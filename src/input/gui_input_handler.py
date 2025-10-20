"""
GUI Input Handler - Handles keyboard input for pygame-based UI
"""
import pygame
from src.input.input_handler import InputHandler, InputAction


class GUIInputHandler(InputHandler):
    """Input handler for pygame-based GUI"""
    
    def __init__(self, config, selected_snake_part):
        self.config = config
        self.selected_snake_part = selected_snake_part
    
    def get_input(self, timeout=None):
        """
        Get input from pygame events.
        Note: This doesn't use timeout as pygame events are polled differently.
        """
        # This is a simplified version - actual pygame event handling
        # happens in the main game loop
        return InputAction.NONE
    
    def handle_key_event(self, key):
        """Handle a pygame key event and return the corresponding action"""
        if key == self.config.key_bindings.get('quit', pygame.K_q):
            return InputAction.QUIT
        elif key == self.config.key_bindings.get('move_up', pygame.K_w) or key == pygame.K_UP:
            if self.selected_snake_part.getDirection() != 2:  # Not opposite direction
                return InputAction.MOVE_UP
        elif key == self.config.key_bindings.get('move_left', pygame.K_a) or key == pygame.K_LEFT:
            if self.selected_snake_part.getDirection() != 3:  # Not opposite direction
                return InputAction.MOVE_LEFT
        elif key == self.config.key_bindings.get('move_down', pygame.K_s) or key == pygame.K_DOWN:
            if self.selected_snake_part.getDirection() != 0:  # Not opposite direction
                return InputAction.MOVE_DOWN
        elif key == self.config.key_bindings.get('move_right', pygame.K_d) or key == pygame.K_RIGHT:
            if self.selected_snake_part.getDirection() != 1:  # Not opposite direction
                return InputAction.MOVE_RIGHT
        elif key == self.config.key_bindings.get('restart', pygame.K_r):
            return InputAction.RESTART
        elif key == pygame.K_ESCAPE:
            return InputAction.MENU
        
        return InputAction.NONE
    
    def cleanup(self):
        """Clean up GUI input resources"""
        pass  # pygame cleanup handled elsewhere
