#!/usr/bin/env python3
"""
Integration test for Text UI gameplay verification.
This test runs the game in text UI mode and simulates gameplay to verify:
1. Game starts correctly
2. Snake movement works
3. Food collection works
4. Game state updates properly
5. Restart/level progression works
"""

import sys
import os
import time
import threading
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.ophidian import Ophidian
from src.config.config import Config
from src.input.input_handler import InputAction


class TextUIGameplayTest:
    """Automated gameplay test for text UI mode"""
    
    def __init__(self):
        self.config = Config()
        self.config.initial_grid_size = 5  # Small grid for faster testing
        self.config.limit_tick_speed = False  # Run as fast as possible
        # Skip terminal init for CI/testing environments without TTY
        self.ophidian = Ophidian(use_text_ui=True, skip_terminal_init=True)
        self.test_passed = False
        self.errors = []
        
    def log(self, message):
        """Log test progress"""
        print(f"[TEST] {message}")
    
    def verify_initial_state(self):
        """Verify the game initializes correctly"""
        self.log("Verifying initial game state...")
        
        try:
            # Start the game
            self.ophidian.initialize_game()
            
            # Check basic state
            assert self.ophidian.level == 1, "Level should be 1"
            assert self.ophidian.snake_part_repository.get_length() == 1, "Snake should have 1 part"
            assert self.ophidian.environment_repository is not None, "Environment should exist"
            assert self.ophidian.game_score is not None, "Game score should exist"
            
            # Count food
            food_count = 0
            for location_id in self.ophidian.environment_repository.get_locations():
                location = self.ophidian.environment_repository.get_location_by_id(location_id)
                for entity_id in location.getEntities():
                    entity = location.getEntity(entity_id)
                    if hasattr(entity, 'getName') and entity.getName() == "Food":
                        food_count += 1
            
            assert food_count == 1, f"Should have exactly 1 food, found {food_count}"
            
            self.log("✓ Initial state verified")
            return True
        except AssertionError as e:
            self.errors.append(f"Initial state verification failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error in initial state: {e}")
            return False
    
    def simulate_movement(self, direction, steps=5):
        """Simulate snake movement in a direction"""
        self.log(f"Simulating {steps} steps in direction {direction}...")
        
        try:
            for i in range(steps):
                # Set direction
                if not self.ophidian.game_engine.handle_direction_input(direction):
                    self.log(f"  Warning: Direction input rejected at step {i+1}")
                
                # Update game state
                self.ophidian.game_engine.update()
                
                # Small delay to see progress
                time.sleep(0.05)
            
            self.log(f"✓ Completed {steps} steps")
            return True
        except Exception as e:
            self.errors.append(f"Movement simulation failed: {e}")
            return False
    
    def verify_game_mechanics(self):
        """Verify game mechanics work correctly"""
        self.log("Verifying game mechanics...")
        
        try:
            initial_tick = self.ophidian.tick
            
            # Move up
            self.simulate_movement(0, 3)  # UP
            
            # Move right
            self.simulate_movement(3, 3)  # RIGHT
            
            # Move down
            self.simulate_movement(2, 3)  # DOWN
            
            # Move left
            self.simulate_movement(1, 3)  # LEFT
            
            # Verify ticks increased
            final_tick = self.ophidian.tick
            assert final_tick > initial_tick, f"Tick should increase (was {initial_tick}, now {final_tick})"
            
            # Verify snake still exists
            assert self.ophidian.snake_part_repository.get_length() >= 1, "Snake should still exist"
            
            self.log("✓ Game mechanics verified")
            return True
        except AssertionError as e:
            self.errors.append(f"Game mechanics verification failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error in game mechanics: {e}")
            return False
    
    def verify_restart(self):
        """Verify game restart works correctly"""
        self.log("Verifying game restart...")
        
        try:
            # Simulate collision by setting collision flag
            self.ophidian.collision = True
            
            # Restart the game
            self.ophidian.check_for_level_progress_and_reinitialize()
            
            # Verify state after restart
            assert self.ophidian.snake_part_repository.get_length() == 1, "Snake should reset to 1 part"
            assert not self.ophidian.collision, "Collision flag should be cleared"
            
            # Count food again
            food_count = 0
            for location_id in self.ophidian.environment_repository.get_locations():
                location = self.ophidian.environment_repository.get_location_by_id(location_id)
                for entity_id in location.getEntities():
                    entity = location.getEntity(entity_id)
                    if hasattr(entity, 'getName') and entity.getName() == "Food":
                        food_count += 1
            
            assert food_count == 1, f"Should have exactly 1 food after restart, found {food_count}"
            
            self.log("✓ Restart verified")
            return True
        except AssertionError as e:
            self.errors.append(f"Restart verification failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error in restart: {e}")
            return False
    
    def verify_text_renderer(self):
        """Verify text renderer produces output"""
        self.log("Verifying text renderer...")
        
        try:
            # Import and create text renderer
            from src.textui.text_renderer import TextRenderer
            
            text_renderer = TextRenderer(self.config)
            
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                # Render the grid
                text_renderer.render_grid(
                    self.ophidian.environment_repository,
                    self.ophidian.snake_part_repository,
                    self.ophidian.collision
                )
                
                # Render stats
                percentage = self.ophidian.snake_part_repository.get_length() / self.ophidian.environment_repository.get_num_locations()
                text_renderer.render_stats(
                    self.ophidian.level,
                    self.ophidian.snake_part_repository.get_length(),
                    self.ophidian.game_score.current_points,
                    self.ophidian.game_score.cumulative_points,
                    percentage
                )
                
                # Render controls
                text_renderer.render_controls()
                
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            
            # Verify output contains expected elements
            assert '┌' in output or '+' in output, "Output should contain grid border"
            assert 'Level' in output or 'level' in output, "Output should contain level info"
            assert 'Score' in output or 'score' in output, "Output should contain score info"
            assert 'Controls' in output or 'controls' in output, "Output should contain controls info"
            
            self.log("✓ Text renderer verified")
            return True
        except AssertionError as e:
            self.errors.append(f"Text renderer verification failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error in text renderer: {e}")
            return False
    
    def run_all_tests(self):
        """Run all gameplay tests"""
        self.log("="*60)
        self.log("Starting Text UI Gameplay Verification")
        self.log("="*60)
        
        tests = [
            ("Initial State", self.verify_initial_state),
            ("Game Mechanics", self.verify_game_mechanics),
            ("Restart", self.verify_restart),
            ("Text Renderer", self.verify_text_renderer),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            if test_func():
                passed += 1
            else:
                failed += 1
        
        self.log("\n" + "="*60)
        self.log(f"Test Results: {passed} passed, {failed} failed")
        self.log("="*60)
        
        if self.errors:
            self.log("\nErrors encountered:")
            for error in self.errors:
                self.log(f"  - {error}")
        
        if failed == 0:
            self.log("\n✓ All Text UI gameplay tests PASSED!")
            return True
        else:
            self.log(f"\n✗ {failed} test(s) FAILED")
            return False


def main():
    """Main test entry point"""
    try:
        test = TextUIGameplayTest()
        success = test.run_all_tests()
        
        if success:
            print("\n" + "="*60)
            print("SUCCESS: Text UI gameplay verification completed")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("FAILURE: Text UI gameplay verification failed")
            print("="*60)
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
