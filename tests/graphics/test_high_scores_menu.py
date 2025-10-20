import unittest
from unittest.mock import MagicMock, patch
import os
import pygame
from src.graphics.high_scores_menu import HighScoresMenu
from src.state.menu_state import MenuState
from src.score.high_score_entry import HighScoreEntry


class TestHighScoresMenu(unittest.TestCase):
    """Test the HighScoresMenu class"""

    def setUp(self):
        """Set up test fixtures"""
        # Disable audio to avoid ALSA warnings in tests
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        pygame.init()
        
        # Mock config and display
        self.mock_config = MagicMock()
        self.mock_config.display_width = 500
        self.mock_config.display_height = 500
        self.mock_config.black = (0, 0, 0)
        self.mock_config.white = (255, 255, 255)
        self.mock_config.green = (0, 255, 0)
        self.mock_config.yellow = (255, 255, 0)
        self.mock_config.text_size = 50
        
        self.mock_display = MagicMock()

    def tearDown(self):
        """Clean up after tests"""
        pygame.quit()

    def test_high_scores_menu_initialization(self):
        """Test HighScoresMenu initialization"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        self.assertIsNotNone(menu.config)
        self.assertIsNotNone(menu.game_display)
        self.assertIsNotNone(menu.graphik)
        self.assertIsNotNone(menu.high_score_repository)
        self.assertEqual(menu.scroll_offset, 0)

    def test_handle_key_down_escape(self):
        """Test that escape key returns to main menu"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        result = menu.handle_key_down(pygame.K_ESCAPE)
        self.assertEqual(result, MenuState.MAIN_MENU)

    def test_handle_key_down_enter(self):
        """Test that enter key returns to main menu"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        result = menu.handle_key_down(pygame.K_RETURN)
        self.assertEqual(result, MenuState.MAIN_MENU)

    def test_handle_key_down_other_keys(self):
        """Test that other keys return None"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        result = menu.handle_key_down(pygame.K_a)
        self.assertIsNone(result)
        
        result = menu.handle_key_down(pygame.K_SPACE)
        self.assertIsNone(result)

    def test_handle_key_down_scroll_up(self):
        """Test scrolling up with arrow keys"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        menu.scroll_offset = 3
        
        result = menu.handle_key_down(pygame.K_UP)
        self.assertIsNone(result)
        self.assertEqual(menu.scroll_offset, 2)

    def test_handle_key_down_scroll_down(self):
        """Test scrolling down with arrow keys"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        # Mock high scores to allow scrolling
        with patch.object(menu.high_score_repository, 'load') as mock_load:
            mock_load.return_value = [
                HighScoreEntry(1000 - i * 100, 50 - i, 5) for i in range(15)
            ]
            
            result = menu.handle_key_down(pygame.K_DOWN)
            self.assertIsNone(result)
            self.assertEqual(menu.scroll_offset, 1)

    def test_handle_key_down_scroll_bounds(self):
        """Test that scrolling respects bounds"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        # Test cannot scroll up past 0
        menu.scroll_offset = 0
        menu.handle_key_down(pygame.K_UP)
        self.assertEqual(menu.scroll_offset, 0)

    def test_handle_mouse_click(self):
        """Test mouse click returns to main menu"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        result = menu.handle_mouse_click((100, 100))
        self.assertEqual(result, MenuState.MAIN_MENU)

    def test_draw_method_no_scores(self):
        """Test drawing when there are no high scores"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        # Mock the graphik methods
        menu.graphik.drawText = MagicMock()
        
        # Mock high score repository to return empty list
        with patch.object(menu.high_score_repository, 'load') as mock_load:
            mock_load.return_value = []
            
            menu.draw()
            
            # Should call fill on display
            menu.game_display.fill.assert_called_with(self.mock_config.black)
            
            # Should draw text
            self.assertTrue(menu.graphik.drawText.called)
            
            # Check that "HIGH SCORES" title is drawn
            title_calls = [call for call in menu.graphik.drawText.call_args_list 
                          if len(call[0]) > 0 and call[0][0] == "HIGH SCORES"]
            self.assertTrue(len(title_calls) > 0)
            
            # Check that "No high scores yet!" message is drawn
            no_scores_calls = [call for call in menu.graphik.drawText.call_args_list 
                              if len(call[0]) > 0 and "No high scores yet" in call[0][0]]
            self.assertTrue(len(no_scores_calls) > 0)

    def test_draw_method_with_scores(self):
        """Test drawing when there are high scores"""
        menu = HighScoresMenu(self.mock_config, self.mock_display)
        
        # Mock the graphik methods
        menu.graphik.drawText = MagicMock()
        
        # Mock high score repository to return some scores
        test_scores = [
            HighScoreEntry(1000, 50, 5),
            HighScoreEntry(800, 40, 4),
            HighScoreEntry(600, 30, 3)
        ]
        
        with patch.object(menu.high_score_repository, 'load') as mock_load:
            mock_load.return_value = test_scores
            
            menu.draw()
            
            # Should draw text multiple times
            self.assertTrue(menu.graphik.drawText.called)
            
            # Verify scores are being drawn (check for the score values)
            all_args = [str(call[0][0]) for call in menu.graphik.drawText.call_args_list]
            self.assertIn("1000", all_args)
            self.assertIn("800", all_args)
            self.assertIn("600", all_args)


if __name__ == '__main__':
    unittest.main()