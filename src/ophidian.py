import os
import random
import time
import logging

import pygame

from src.config.config import Config
from src.graphics.renderer import Renderer
from src.graphics.main_menu import MainMenu
from src.graphics.options_menu import OptionsMenu
from src.graphics.high_scores_menu import HighScoresMenu
from src.input.keyDownEventHandler import KeyDownEventHandler
from src.snake.snakePart import SnakePart
from src.snake.snakePartRepository import SnakePartRepository
from src.snake.snakeColorGenerator import SnakeColorGenerator
from src.environment.pyEnvLibEnvironmentRepositoryImpl import PyEnvLibEnvironmentRepositoryImpl
from src.score.game_score import GameScore
from src.state.game_state_repository import GameStateRepository
from src.state.menu_state import MenuState
from src.audio.audio_manager import AudioManager

# New abstractions for UI/Game decoupling
from src.game_engine import GameEngine
from src.input.input_handler import InputAction, DirectionMapper
from src.input.text_ui_input_handler import TextUIInputHandler
from src.input.gui_input_handler import GUIInputHandler
from src.textui.text_ui_renderer import TextUIRenderer

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

class Ophidian:
    def __init__(self, use_text_ui=False):
        # Set UI mode first
        self.use_text_ui = use_text_ui
        
        # Initialize pygame conditionally
        if not self.use_text_ui:
            pygame.init()
        
        self.running = True
        self.current_state = MenuState.MAIN_MENU
        self.config = Config()
        self.config.use_text_ui = use_text_ui
        
        # Initialize game engine (UI-agnostic)
        self.game_engine = GameEngine(self.config)
        
        # Track current window size for persistence
        self.current_window_size = (self.config.display_width, self.config.display_height)
        
        # Initialize UI-specific components
        if not self.use_text_ui:
            self._initialize_gui()
        else:
            self._initialize_text_ui()
        
        # Deprecated attributes for backward compatibility
        # These delegate to game_engine
        self.state_repository = self.game_engine.state_repository
    
    def _initialize_gui(self):
        """Initialize GUI-specific components"""
        self.game_display = self.initialize_game_display()
        
        # Set icon after display is initialized
        try:
            pygame.display.set_icon(pygame.image.load("src/media/icon.PNG"))
        except (pygame.error, FileNotFoundError):
            pass  # Icon loading is optional
        
        pygame.display.set_caption("Ophidian")
        
        # Initialize menu systems with current window size
        self.main_menu = MainMenu(self.config, self.game_display)
        self.options_menu = OptionsMenu(self.config, self.game_display)
        self.high_scores_menu = HighScoresMenu(self.config, self.game_display)
        
        # Initialize audio manager
        self.audio_manager = AudioManager(self.config)
        
        # Set up audio update callback for options menu
        self.options_menu.set_audio_update_callback(self.update_audio_settings)
        self.options_menu.set_resolution_change_callback(self.handle_resolution_change)
        
        # GUI renderer (existing Renderer class)
        self.renderer = None
        
        # GUI input handler
        self.gui_input_handler = None
    
    def _initialize_text_ui(self):
        """Initialize text UI-specific components"""
        from src.textui.text_renderer import TextRenderer
        text_renderer = TextRenderer(self.config)
        text_renderer.enable_raw_mode()
        
        # Text UI renderer adapter
        self.text_ui_renderer = TextUIRenderer(text_renderer)
        
        # Text UI input handler
        self.text_input_handler = TextUIInputHandler(text_renderer)
        
        # Text menu state
        self.text_menu_selected = 0
        self.text_menu_options = ["Play Game", "Exit"]
    
    # Properties for backward compatibility - delegate to game_engine
    @property
    def level(self):
        return self.game_engine.level
    
    @level.setter
    def level(self, value):
        self.game_engine.level = value
    
    @property
    def tick(self):
        return self.game_engine.tick
    
    @tick.setter
    def tick(self, value):
        self.game_engine.tick = value
    
    @property
    def changed_direction_this_tick(self):
        return self.game_engine.changed_direction_this_tick
    
    @changed_direction_this_tick.setter
    def changed_direction_this_tick(self, value):
        self.game_engine.changed_direction_this_tick = value
    
    @property
    def collision(self):
        return self.game_engine.collision
    
    @collision.setter
    def collision(self, value):
        self.game_engine.collision = value
    
    @property
    def snake_part_repository(self):
        return self.game_engine.snake_part_repository
    
    @snake_part_repository.setter
    def snake_part_repository(self, value):
        self.game_engine.snake_part_repository = value
    
    @property
    def environment_repository(self):
        return self.game_engine.environment_repository
    
    @environment_repository.setter
    def environment_repository(self, value):
        self.game_engine.environment_repository = value
    
    @property
    def game_score(self):
        return self.game_engine.game_score
    
    @game_score.setter
    def game_score(self, value):
        self.game_engine.game_score = value
    
    @property
    def selected_snake_part(self):
        return self.game_engine.selected_snake_part
    
    @selected_snake_part.setter
    def selected_snake_part(self, value):
        self.game_engine.selected_snake_part = value

    def initialize_game_display(self):
        """Initialize the game display using current window size"""
        if self.use_text_ui:
            return None  # No display needed for text UI
        
        if self.config.fullscreen:
            return pygame.display.set_mode(
                self.current_window_size, pygame.FULLSCREEN
            )
        else:
            return pygame.display.set_mode(
                self.current_window_size, pygame.RESIZABLE
            )

    def initialize_game(self):
        """Initialize the game state when starting to play"""
        # Delegate to game engine
        self.game_engine.initialize_game()
        
        # Only initialize renderer for GUI mode
        if not self.use_text_ui:
            self.renderer = Renderer(
                self.collision,
                self.config,
                self.environment_repository,
                self.snake_part_repository,
                self.game_score,
                self.game_display  # Pass the existing game display
            )
            # Initialize GUI input handler with current snake part
            self.gui_input_handler = GUIInputHandler(self.config, self.selected_snake_part)
        
        self.initialize()

    def save_game_state(self):
        """Save current game state"""
        self.game_engine.save_game_state()

    def check_for_level_progress_and_reinitialize(self):
        logging.info("Checking for level progress...")
        
        # Check if level is complete for sound effects
        is_level_complete = (
            self.snake_part_repository.get_length()
            > self.environment_repository.get_num_locations()
            * self.config.level_progress_percentage_required
        )
        
        if is_level_complete:
            logging.info("The ophidian has progressed to the next level.")
            # Play level complete sound
            if not self.use_text_ui and hasattr(self, 'audio_manager'):
                self.audio_manager.play_sound_effect("level_complete")
        else:
            # Play collision/death sound
            if not self.use_text_ui and hasattr(self, 'audio_manager'):
                self.audio_manager.play_sound_effect("collision")
        
        # Delegate to game engine for core logic
        self.game_engine.check_for_level_progress_and_reinitialize()
        
        # Recreate renderer with new environment references (GUI mode only)
        if not self.use_text_ui:
            self.renderer = Renderer(
                self.collision,
                self.config,
                self.environment_repository,
                self.snake_part_repository,
                self.game_score,
                self.game_display
            )
            # Update GUI input handler with new snake part
            self.gui_input_handler = GUIInputHandler(self.config, self.selected_snake_part)
            # Initialize renderer settings
            self.initialize()

    def quit_application(self):
        self.save_game_state()
        if self.game_score is not None:
            self.game_score.display_stats()
        
        # Clean up audio (GUI mode only)
        if not self.use_text_ui and hasattr(self, 'audio_manager'):
            self.audio_manager.cleanup()
        
        # Clean up input handlers
        if self.use_text_ui:
            self.text_input_handler.cleanup()
        elif hasattr(self, 'gui_input_handler') and self.gui_input_handler:
            self.gui_input_handler.cleanup()
            
        if not self.use_text_ui:
            pygame.quit()
        quit()
    
    def update_audio_settings(self):
        """Update audio manager when settings change"""
        if hasattr(self, 'audio_manager'):
            self.audio_manager.update_volumes()
    
    def handle_resolution_change(self):
        """Handle resolution changes from options menu"""
        if self.use_text_ui:
            return  # No display to resize in text mode
        
        # Update current window size
        self.current_window_size = (self.config.display_width, self.config.display_height)
        
        # Reinitialize the game display with new resolution
        self.game_display = self.initialize_game_display()
        
        # Update menu references to new display
        self.main_menu.game_display = self.game_display
        self.options_menu.game_display = self.game_display
        self.high_scores_menu.game_display = self.game_display
        
        # Update renderer if in game
        if self.renderer:
            self.renderer.graphik.gameDisplay = self.game_display
            self.renderer.initialize_location_width_and_height()

    def initialize(self):
        self.collision = False
        self.tick = 0
        if not self.use_text_ui:
            self.renderer.initialize_location_width_and_height()
            pygame.display.set_caption("Ophidian - Level " + str(self.level))

    def run(self):
        if self.use_text_ui:
            self.run_text_ui()
        else:
            self.run_gui()

    def run_gui(self):
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_application()
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down_event_based_on_state(event.key)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion_based_on_state(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click_based_on_state(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_release_based_on_state()
                elif event.type == pygame.WINDOWRESIZED:
                    # Update current window size for all states
                    self.current_window_size = self.game_display.get_size()
                    
                    if self.current_state == MenuState.GAME and self.renderer:
                        self.renderer.initialize_location_width_and_height()
                    # Menus will automatically adapt to new size in their draw methods

            # Handle different states
            if self.current_state == MenuState.MAIN_MENU:
                self.main_menu.draw()
            elif self.current_state == MenuState.OPTIONS:
                self.options_menu.draw()
            elif self.current_state == MenuState.HIGH_SCORES:
                self.high_scores_menu.draw()
            elif self.current_state == MenuState.GAME:
                self.run_game_loop()
            elif self.current_state == MenuState.EXIT:
                self.quit_application()

            pygame.display.update()
            clock.tick(60)  # 60 FPS for menu, game has its own timing

        self.quit_application()
    
    def run_text_ui(self):
        """Run the game with text-based UI"""
        while self.running:
            if self.current_state == MenuState.MAIN_MENU:
                self.run_text_menu()
            elif self.current_state == MenuState.GAME:
                self.run_text_game_loop()
            elif self.current_state == MenuState.EXIT:
                self.quit_application()
        
        self.quit_application()
    
    def run_text_menu(self):
        """Run text-based menu"""
        self.text_ui_renderer.render_menu(self.text_menu_options, self.text_menu_selected)
        
        # Get key press with timeout
        action = self.text_input_handler.get_input(timeout=0.1)
        
        if action != InputAction.NONE:
            if action == InputAction.MOVE_UP:  # Up arrow
                self.text_menu_selected = (self.text_menu_selected - 1) % len(self.text_menu_options)
            elif action == InputAction.MOVE_DOWN:  # Down arrow
                self.text_menu_selected = (self.text_menu_selected + 1) % len(self.text_menu_options)
            elif action == InputAction.SELECT:  # Enter key
                if self.text_menu_options[self.text_menu_selected] == "Play Game":
                    self.current_state = MenuState.GAME
                    self.initialize_game()
                elif self.text_menu_options[self.text_menu_selected] == "Exit":
                    self.current_state = MenuState.EXIT
            elif action == InputAction.QUIT:
                self.current_state = MenuState.EXIT
    
    def run_text_game_loop(self):
        """Run one iteration of the text-based game loop"""
        if not self.snake_part_repository or not self.environment_repository:
            return
        
        # Render using abstraction
        game_state = self.game_engine.get_game_state()
        self.text_ui_renderer.render_game(game_state)
        
        # Get input using abstraction
        action = self.text_input_handler.get_input(
            timeout=self.config.tick_speed if self.config.limit_tick_speed else 0.01
        )
        
        # Handle input actions
        if action != InputAction.NONE:
            if action in (InputAction.MOVE_UP, InputAction.MOVE_DOWN, 
                         InputAction.MOVE_LEFT, InputAction.MOVE_RIGHT):
                direction = DirectionMapper.action_to_direction(action)
                self.game_engine.handle_direction_input(direction)
            elif action == InputAction.RESTART:
                self.game_engine.handle_restart()
            elif action == InputAction.QUIT:
                logging.info("Quiting the application...")
                self.quit_application()
            elif action == InputAction.MENU:
                self.current_state = MenuState.MAIN_MENU
                self.save_game_state()
                return
        
        # Update game state using engine
        self.game_engine.update()

    def handle_key_down_event_based_on_state(self, key):
        """Handle key down events based on current state"""
        if self.current_state == MenuState.MAIN_MENU:
            new_state = self.main_menu.handle_key_down(key)
            if new_state:
                self.change_state(new_state)
        elif self.current_state == MenuState.OPTIONS:
            new_state = self.options_menu.handle_key_down(key)
            if new_state:
                self.change_state(new_state)
        elif self.current_state == MenuState.HIGH_SCORES:
            new_state = self.high_scores_menu.handle_key_down(key)
            if new_state:
                self.change_state(new_state)
        elif self.current_state == MenuState.GAME:
            self.handle_game_key_down_event(key)

    def handle_mouse_motion_based_on_state(self, pos):
        """Handle mouse motion based on current state"""
        if self.current_state == MenuState.MAIN_MENU:
            self.main_menu.handle_mouse_motion(pos)
        elif self.current_state == MenuState.OPTIONS:
            self.options_menu.handle_mouse_motion(pos)

    def handle_mouse_click_based_on_state(self, pos):
        """Handle mouse clicks based on current state"""
        if self.current_state == MenuState.MAIN_MENU:
            new_state = self.main_menu.handle_mouse_click(pos)
            if new_state:
                self.change_state(new_state)
        elif self.current_state == MenuState.OPTIONS:
            new_state = self.options_menu.handle_mouse_click(pos)
            if new_state:
                self.change_state(new_state)
        elif self.current_state == MenuState.HIGH_SCORES:
            new_state = self.high_scores_menu.handle_mouse_click(pos)
            if new_state:
                self.change_state(new_state)

    def handle_mouse_release_based_on_state(self):
        """Handle mouse release based on current state"""
        if self.current_state == MenuState.OPTIONS:
            self.options_menu.handle_mouse_release()

    def change_state(self, new_state):
        """Change the current state and handle transitions"""
        # Play menu navigation sound
        if hasattr(self, 'audio_manager'):
            self.audio_manager.play_sound_effect("menu_select")
            
        if new_state == MenuState.GAME and self.current_state != MenuState.GAME:
            # Initialize game when transitioning to game state
            self.initialize_game()
        elif new_state == MenuState.MAIN_MENU and self.current_state == MenuState.GAME:
            # Save game state when returning to menu
            self.save_game_state()
        
        self.current_state = new_state

    def handle_game_key_down_event(self, key):
        """Handle key down events during gameplay"""
        if key == pygame.K_ESCAPE:
            # Return to main menu
            self.change_state(MenuState.MAIN_MENU)
            return
            
        key_down_event_handler = KeyDownEventHandler(
            self.config, self.renderer.graphik.gameDisplay, self.selected_snake_part
        )
        result = key_down_event_handler.handle_key_down_event(key)
        if result == "quit":
            logging.info("Quiting the application...")
            self.quit_application()
        elif result == "restart":
            logging.info("Restarting the game...")
            # Reset score when manually restarting
            self.game_score.reset()
            self.check_for_level_progress_and_reinitialize()
        elif result == "initialize game display":
            logging.info("Re-initializing the game display...")
            self.renderer.initialize_location_width_and_height()

    def run_game_loop(self):
        """Run one iteration of the game loop"""
        if not self.snake_part_repository or not self.environment_repository:
            return

        check_for_level_progress_and_reinitialize = False
        if self.selected_snake_part.getDirection() == 0:
            check_for_level_progress_and_reinitialize = self.environment_repository.move_entity(self.selected_snake_part, 0)
        elif self.selected_snake_part.getDirection() == 1:
            check_for_level_progress_and_reinitialize = self.environment_repository.move_entity(self.selected_snake_part, 1)
        elif self.selected_snake_part.getDirection() == 2:
            check_for_level_progress_and_reinitialize = self.environment_repository.move_entity(self.selected_snake_part, 2)
        elif self.selected_snake_part.getDirection() == 3:
            check_for_level_progress_and_reinitialize = self.environment_repository.move_entity(self.selected_snake_part, 3)

        if check_for_level_progress_and_reinitialize:
            self.check_for_level_progress_and_reinitialize()

        self.game_score.calculate()
        self.renderer.draw()

        if self.config.limit_tick_speed:
            # Apply difficulty-based speed modification
            base_tick_speed = self.config.tick_speed
            if self.config.difficulty == "Easy":
                # Slower speed = easier
                tick_speed = base_tick_speed * 1.5
            elif self.config.difficulty == "Hard":
                # Faster speed = harder
                tick_speed = base_tick_speed * 0.6
            else:  # Normal
                tick_speed = base_tick_speed
                
            time.sleep(tick_speed)
            self.tick += 1
            self.changed_direction_this_tick = False


if __name__ == "__main__":
    ophidian = Ophidian()
    ophidian.run()
