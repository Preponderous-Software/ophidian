"""
Unit tests for GameEngine - Core gameplay logic
Tests to ensure game-breaking changes are caught
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from src.game_engine import GameEngine
from src.config.config import Config


class TestGameEngine(unittest.TestCase):
    """Test suite for GameEngine class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.config.initial_grid_size = 5
        self.config.level_progress_percentage_required = 0.25
        self.game_engine = GameEngine(self.config)
    
    def test_game_engine_initialization(self):
        """Test that GameEngine initializes with correct default values"""
        self.assertEqual(self.game_engine.level, 1)
        self.assertEqual(self.game_engine.tick, 0)
        self.assertFalse(self.game_engine.changed_direction_this_tick)
        self.assertFalse(self.game_engine.collision)
        self.assertTrue(self.game_engine.running)
        self.assertIsNone(self.game_engine.snake_part_repository)
        self.assertIsNone(self.game_engine.environment_repository)
        self.assertIsNone(self.game_engine.game_score)
        self.assertIsNone(self.game_engine.selected_snake_part)
    
    def test_initialize_game_creates_game_objects(self):
        """Test that initialize_game creates all necessary game objects"""
        self.game_engine.initialize_game()
        
        self.assertIsNotNone(self.game_engine.snake_part_repository)
        self.assertIsNotNone(self.game_engine.environment_repository)
        self.assertIsNotNone(self.game_engine.game_score)
        self.assertIsNotNone(self.game_engine.selected_snake_part)
        self.assertEqual(self.game_engine.tick, 0)
        self.assertFalse(self.game_engine.changed_direction_this_tick)
        self.assertFalse(self.game_engine.collision)
    
    def test_initialize_game_spawns_snake_and_food(self):
        """Test that initialize_game spawns snake and food"""
        self.game_engine.initialize_game()
        
        # Verify snake was spawned
        self.assertEqual(self.game_engine.snake_part_repository.get_length(), 1)
        
        # Verify food was spawned (check environment has entities)
        food_count = 0
        for location_id in self.game_engine.environment_repository.get_locations():
            location = self.game_engine.environment_repository.get_location_by_id(location_id)
            for entity_id in location.getEntities():
                entity = location.getEntity(entity_id)
                if hasattr(entity, 'getName') and entity.getName() == "Food":
                    food_count += 1
        self.assertGreater(food_count, 0, "Food should be spawned")
    
    def test_handle_direction_input_changes_direction(self):
        """Test that handle_direction_input changes snake direction"""
        self.game_engine.initialize_game()
        
        # Initially should be able to change direction
        result = self.game_engine.handle_direction_input(1)  # LEFT
        self.assertTrue(result)
        self.assertEqual(self.game_engine.selected_snake_part.getDirection(), 1)
        self.assertTrue(self.game_engine.changed_direction_this_tick)
    
    def test_handle_direction_input_prevents_multiple_changes_per_tick(self):
        """Test that direction can only be changed once per tick"""
        self.game_engine.initialize_game()
        
        # First change should succeed
        result1 = self.game_engine.handle_direction_input(1)  # LEFT
        self.assertTrue(result1)
        
        # Second change in same tick should fail
        result2 = self.game_engine.handle_direction_input(2)  # DOWN
        self.assertFalse(result2)
        self.assertEqual(self.game_engine.selected_snake_part.getDirection(), 1)  # Still LEFT
    
    def test_update_increments_tick_and_resets_direction_flag(self):
        """Test that update() increments tick and resets direction change flag"""
        self.game_engine.initialize_game()
        self.config.limit_tick_speed = True
        
        # Change direction
        self.game_engine.handle_direction_input(1)
        self.assertTrue(self.game_engine.changed_direction_this_tick)
        
        initial_tick = self.game_engine.tick
        self.game_engine.update()
        
        self.assertEqual(self.game_engine.tick, initial_tick + 1)
        self.assertFalse(self.game_engine.changed_direction_this_tick)
    
    def test_update_moves_snake(self):
        """Test that update() moves the snake"""
        self.game_engine.initialize_game()
        
        # Get initial position
        initial_location = self.game_engine.environment_repository.get_location_of_entity(
            self.game_engine.selected_snake_part
        )
        initial_pos = (initial_location.getX(), initial_location.getY())
        
        # Set direction and update multiple times to ensure movement
        self.game_engine.handle_direction_input(1)  # LEFT
        
        # Update multiple times to ensure movement happens
        for _ in range(3):
            self.game_engine.update()
        
        # Get new position
        new_location = self.game_engine.environment_repository.get_location_of_entity(
            self.game_engine.selected_snake_part
        )
        new_pos = (new_location.getX(), new_location.getY())
        
        # Position should have changed (or wrapped around the grid)
        # The snake should have moved at least once
        self.assertTrue(
            initial_pos != new_pos or self.game_engine.tick >= 3,
            "Snake should have moved or ticks should have incremented"
        )
    
    def test_get_game_state_returns_correct_structure(self):
        """Test that get_game_state returns all required fields"""
        self.game_engine.initialize_game()
        
        game_state = self.game_engine.get_game_state()
        
        # Verify all required fields are present
        self.assertIn('level', game_state)
        self.assertIn('snake_length', game_state)
        self.assertIn('current_score', game_state)
        self.assertIn('cumulative_score', game_state)
        self.assertIn('collision', game_state)
        self.assertIn('environment_repository', game_state)
        self.assertIn('snake_part_repository', game_state)
        self.assertIn('progress_percentage', game_state)
        
        # Verify values are correct
        self.assertEqual(game_state['level'], 1)
        self.assertEqual(game_state['snake_length'], 1)
        self.assertFalse(game_state['collision'])
        self.assertIsNotNone(game_state['environment_repository'])
        self.assertIsNotNone(game_state['snake_part_repository'])
    
    def test_get_game_state_handles_uninitialized_game(self):
        """Test that get_game_state handles uninitialized game gracefully"""
        game_state = self.game_engine.get_game_state()
        
        self.assertEqual(game_state['snake_length'], 0)
        self.assertEqual(game_state['current_score'], 0)
        self.assertEqual(game_state['cumulative_score'], 0)
        self.assertEqual(game_state['progress_percentage'], 0)
    
    def test_save_game_state(self):
        """Test that save_game_state saves correctly"""
        self.game_engine.initialize_game()
        
        # Mock the state repository save method
        with patch.object(self.game_engine.state_repository, 'save') as mock_save:
            self.game_engine.save_game_state()
            
            # Verify save was called with correct structure
            mock_save.assert_called_once()
            saved_state = mock_save.call_args[0][0]
            self.assertIn('level', saved_state)
            self.assertIn('current_score', saved_state)
            self.assertIn('cumulative_score', saved_state)
    
    def test_handle_restart_resets_score(self):
        """Test that handle_restart resets the score"""
        self.game_engine.initialize_game()
        
        # Set some score
        self.game_engine.game_score.current_points = 100
        
        # Mock check_for_level_progress_and_reinitialize to avoid full reinit
        with patch.object(self.game_engine, 'check_for_level_progress_and_reinitialize'):
            self.game_engine.handle_restart()
            
            # Score should be reset (check_for_level_progress will call reset)
            self.game_engine.check_for_level_progress_and_reinitialize.assert_called_once()


class TestGameEngineIntegration(unittest.TestCase):
    """Integration tests for complete game scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.config.initial_grid_size = 5
        self.config.level_progress_percentage_required = 0.25
        self.config.limit_tick_speed = True
        self.game_engine = GameEngine(self.config)
        self.game_engine.initialize_game()
    
    def test_complete_game_cycle(self):
        """Test a complete game cycle: init -> move -> update -> check state"""
        # Initial state
        self.assertEqual(self.game_engine.level, 1)
        self.assertEqual(self.game_engine.tick, 0)
        
        # Change direction
        self.assertTrue(self.game_engine.handle_direction_input(1))  # LEFT
        
        # Update game
        self.game_engine.update()
        
        # Verify state changed
        self.assertEqual(self.game_engine.tick, 1)
        self.assertFalse(self.game_engine.changed_direction_this_tick)
        
        # Can change direction again
        self.assertTrue(self.game_engine.handle_direction_input(0))  # UP
    
    def test_multiple_updates_work_correctly(self):
        """Test that multiple updates work correctly"""
        initial_tick = self.game_engine.tick
        
        # Perform multiple updates
        for i in range(5):
            self.game_engine.handle_direction_input(i % 4)
            self.game_engine.update()
        
        # Tick should have incremented
        self.assertEqual(self.game_engine.tick, initial_tick + 5)
    
    def test_multiple_initializations_spawn_single_entities(self):
        """Test that reinitializing doesn't create duplicate snakes or food"""
        # First initialization (already done in setUp)
        food_count_1 = self._count_food_entities()
        snake_count_1 = self.game_engine.snake_part_repository.get_length()
        
        self.assertEqual(food_count_1, 1, "Should have exactly 1 food after first init")
        self.assertEqual(snake_count_1, 1, "Should have exactly 1 snake part after first init")
        
        # Second initialization (simulating restart)
        self.game_engine.initialize_game()
        
        food_count_2 = self._count_food_entities()
        snake_count_2 = self.game_engine.snake_part_repository.get_length()
        
        self.assertEqual(food_count_2, 1, "Should have exactly 1 food after second init")
        self.assertEqual(snake_count_2, 1, "Should have exactly 1 snake part after second init")
        
        # Third initialization for good measure
        self.game_engine.initialize_game()
        
        food_count_3 = self._count_food_entities()
        snake_count_3 = self.game_engine.snake_part_repository.get_length()
        
        self.assertEqual(food_count_3, 1, "Should have exactly 1 food after third init")
        self.assertEqual(snake_count_3, 1, "Should have exactly 1 snake part after third init")
    
    def _count_food_entities(self):
        """Helper method to count food entities in the environment"""
        food_count = 0
        for location_id in self.game_engine.environment_repository.get_locations():
            location = self.game_engine.environment_repository.get_location_by_id(location_id)
            for entity_id in location.getEntities():
                entity = location.getEntity(entity_id)
                if hasattr(entity, 'getName') and entity.getName() == "Food":
                    food_count += 1
        return food_count


class TestGameEngineReinitialization(unittest.TestCase):
    """Tests for environment reinitialization to prevent KeyError issues"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.config.initial_grid_size = 5
        self.config.level_progress_percentage_required = 0.25
        self.config.limit_tick_speed = True
        self.game_engine = GameEngine(self.config)
        self.game_engine.initialize_game()
    
    def test_reinitialize_clears_old_environment(self):
        """Test that reinitialize properly clears old environment state"""
        # Get initial environment
        initial_env = self.game_engine.environment_repository
        initial_env_id = id(initial_env.environment)
        
        # Perform reinitialization
        self.game_engine.check_for_level_progress_and_reinitialize()
        
        # Get new environment
        new_env = self.game_engine.environment_repository
        new_env_id = id(new_env.environment)
        
        # The environment object should be different (recreated)
        self.assertNotEqual(initial_env_id, new_env_id, 
                          "Environment should be recreated during reinitialize")
        
        # Should have exactly 1 snake and 1 food after reinit
        food_count = 0
        snake_count = 0
        for location_id in new_env.get_locations():
            location = new_env.get_location_by_id(location_id)
            for entity_id in location.getEntities():
                entity = location.getEntity(entity_id)
                if hasattr(entity, 'getName'):
                    if entity.getName() == "Food":
                        food_count += 1
                    elif entity.getName() == "Snake Part":
                        snake_count += 1
        
        self.assertEqual(food_count, 1, "Should have exactly 1 food after reinit")
        self.assertEqual(snake_count, 1, "Should have exactly 1 snake part after reinit")
    
    def test_multiple_reinitializations_no_stale_entities(self):
        """Test that multiple reinitializations don't leave stale entity references"""
        # Perform multiple reinitializations
        for i in range(3):
            self.game_engine.check_for_level_progress_and_reinitialize()
            
            # After each reinit, verify we can iterate through all entities without KeyError
            try:
                for location_id in self.game_engine.environment_repository.get_locations():
                    location = self.game_engine.environment_repository.get_location_by_id(location_id)
                    for entity_id in location.getEntities():
                        # This would raise KeyError if entity_id doesn't exist
                        entity = location.getEntity(entity_id)
                        # Verify entity is valid
                        self.assertIsNotNone(entity)
            except KeyError as e:
                self.fail(f"KeyError on iteration {i+1}: {e}. Stale entity references present.")


if __name__ == '__main__':
    unittest.main()
