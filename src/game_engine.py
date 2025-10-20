"""
Game Engine - Core gameplay logic decoupled from UI
This module contains the pure game logic without any UI dependencies.
"""
import logging
from src.snake.snakePart import SnakePart
from src.snake.snakePartRepository import SnakePartRepository
from src.snake.snakeColorGenerator import SnakeColorGenerator
from src.environment.pyEnvLibEnvironmentRepositoryImpl import PyEnvLibEnvironmentRepositoryImpl
from src.score.game_score import GameScore
from src.score.high_score_entry import HighScoreEntry
from src.score.high_score_repository import HighScoreRepository
from src.state.game_state_repository import GameStateRepository

logger = logging.getLogger(__name__)


class GameEngine:
    """
    Pure game logic engine that is UI-agnostic.
    Handles game state, snake movement, collision detection, scoring, etc.
    """
    
    def __init__(self, config):
        self.config = config
        self.state_repository = GameStateRepository()
        self.high_score_repository = HighScoreRepository()
        
        # Game state
        self.level = 1
        self.tick = 0
        self.changed_direction_this_tick = False
        self.collision = False
        self.running = True
        
        # Game objects
        self.snake_part_repository = None
        self.environment_repository = None
        self.game_score = None
        self.selected_snake_part = None
        
        # Track maximum snake length for high score entry
        self.max_snake_length = 0
    
    def initialize_game(self):
        """Initialize or reset the game state"""
        # Load saved state or use defaults
        saved_state = self.state_repository.load()
        if saved_state:
            self.level = saved_state.level
        else:
            self.level = 1

        self.tick = 0
        self.changed_direction_this_tick = False
        self.collision = False

        self.snake_part_repository = SnakePartRepository()
        self.environment_repository = PyEnvLibEnvironmentRepositoryImpl(
            self.level,
            self.config,
            self.snake_part_repository
        )
        self.game_score = GameScore(self.snake_part_repository, self.environment_repository)
        
        # Load saved state or use defaults
        if saved_state:
            self.game_score.current_points = saved_state.current_score
            self.game_score.cumulative_points = saved_state.cumulative_score
        else:
            self.game_score.current_points = 0
            self.game_score.cumulative_points = 0
        
        self._initialize_level()
    
    def _initialize_level(self):
        """Initialize a new level"""
        self.collision = False
        self.tick = 0
        self.selected_snake_part = SnakePart(
            SnakeColorGenerator.generate_green_shade()
        )
        self.environment_repository.add_entity_to_random_location(self.selected_snake_part)
        self.snake_part_repository.append(self.selected_snake_part)
        logger.info("The ophidian enters the world.")
        self.environment_repository.spawn_food()
    
    def save_game_state(self):
        """Save current game state"""
        if self.game_score is not None:
            state = {
                'level': self.level,
                'current_score': self.game_score.current_points,
                'cumulative_score': self.game_score.cumulative_points
            }
            self.state_repository.save(state)
    
    def handle_direction_input(self, direction: int) -> bool:
        """
        Handle direction change input.
        Returns True if direction was changed, False otherwise.
        """
        if not self.changed_direction_this_tick and self.selected_snake_part:
            self.selected_snake_part.setDirection(direction)
            self.changed_direction_this_tick = True
            return True
        return False
    
    def handle_restart(self):
        """Handle game restart"""
        logger.info("Restarting the game...")
        self._save_high_score_if_eligible()
        self.game_score.reset()
        self.check_for_level_progress_and_reinitialize()
    
    def update(self):
        """
        Update game state for one tick.
        This is the core game loop logic without any UI.
        """
        if not self.snake_part_repository or not self.environment_repository:
            return
        
        # Move the snake based on its current direction
        direction = self.selected_snake_part.getDirection()
        check_for_level_progress = self.environment_repository.move_entity(
            self.selected_snake_part, direction
        )
        
        if check_for_level_progress:
            self.check_for_level_progress_and_reinitialize()
        
        # Update score
        self.game_score.calculate()
        
        # Track maximum snake length
        current_length = self.snake_part_repository.get_length()
        if current_length > self.max_snake_length:
            self.max_snake_length = current_length
        
        # Handle tick timing
        if self.config.limit_tick_speed:
            self.tick += 1
            self.changed_direction_this_tick = False
    
    def check_for_level_progress_and_reinitialize(self):
        """Check if level is complete and reinitialize if needed"""
        logger.info("Checking for level progress...")
        if (
            self.snake_part_repository.get_length()
            > self.environment_repository.get_num_locations()
            * self.config.level_progress_percentage_required
        ):
            logger.info("The ophidian has progressed to the next level.")
            self.game_score.level_complete()
            self.level += 1
        else:
            # Game ended (player died), save high score
            self._save_high_score_if_eligible()
            self.game_score.reset()

        self.save_game_state()

        logger.info("Reinitializing the environment...")
        self.environment_repository.reinitialize(self.level)
        logger.info("Clearing the environment repository")
        self.environment_repository.clear()
        logger.info("Re-initializing the game")
        self._initialize_level()
    
    def _save_high_score_if_eligible(self):
        """Save high score if the current score qualifies"""
        if self.game_score and self.game_score.cumulative_points > 0:
            entry = HighScoreEntry(
                score=self.game_score.cumulative_points,
                length=self.max_snake_length,
                level=self.level
            )
            is_high_score = self.high_score_repository.add_score(entry)
            if is_high_score:
                logger.info(f"New high score! Score: {entry.score}, Length: {entry.length}, Level: {entry.level}")
            # Reset max length for next game
            self.max_snake_length = 0
    
    def get_game_state(self):
        """Get current game state for rendering"""
        return {
            'level': self.level,
            'snake_length': self.snake_part_repository.get_length() if self.snake_part_repository else 0,
            'current_score': self.game_score.current_points if self.game_score else 0,
            'cumulative_score': self.game_score.cumulative_points if self.game_score else 0,
            'collision': self.collision,
            'environment_repository': self.environment_repository,
            'snake_part_repository': self.snake_part_repository,
            'progress_percentage': (
                self.snake_part_repository.get_length() / self.environment_repository.get_num_locations()
                if self.snake_part_repository and self.environment_repository
                else 0
            )
        }
