"""
Unit tests for Input Handler abstraction
Tests to ensure input handling doesn't break game functionality
"""
import unittest
from unittest.mock import Mock, MagicMock
from src.input.input_handler import InputAction, DirectionMapper, InputHandler
from src.input.text_ui_input_handler import TextUIInputHandler


class TestInputAction(unittest.TestCase):
    """Test suite for InputAction constants"""
    
    def test_input_action_constants_exist(self):
        """Test that all required InputAction constants exist"""
        self.assertEqual(InputAction.MOVE_UP, "move_up")
        self.assertEqual(InputAction.MOVE_DOWN, "move_down")
        self.assertEqual(InputAction.MOVE_LEFT, "move_left")
        self.assertEqual(InputAction.MOVE_RIGHT, "move_right")
        self.assertEqual(InputAction.RESTART, "restart")
        self.assertEqual(InputAction.QUIT, "quit")
        self.assertEqual(InputAction.MENU, "menu")
        self.assertEqual(InputAction.SELECT, "select")
        self.assertEqual(InputAction.NONE, "none")


class TestDirectionMapper(unittest.TestCase):
    """Test suite for DirectionMapper"""
    
    def test_direction_constants_correct_values(self):
        """Test that direction constants have correct values matching game engine"""
        self.assertEqual(DirectionMapper.UP, 0)
        self.assertEqual(DirectionMapper.LEFT, 1)
        self.assertEqual(DirectionMapper.DOWN, 2)
        self.assertEqual(DirectionMapper.RIGHT, 3)
    
    def test_action_to_direction_maps_correctly(self):
        """Test that action_to_direction maps actions to correct directions"""
        self.assertEqual(DirectionMapper.action_to_direction(InputAction.MOVE_UP), 0)
        self.assertEqual(DirectionMapper.action_to_direction(InputAction.MOVE_LEFT), 1)
        self.assertEqual(DirectionMapper.action_to_direction(InputAction.MOVE_DOWN), 2)
        self.assertEqual(DirectionMapper.action_to_direction(InputAction.MOVE_RIGHT), 3)
    
    def test_action_to_direction_returns_none_for_non_movement(self):
        """Test that non-movement actions return None"""
        self.assertIsNone(DirectionMapper.action_to_direction(InputAction.QUIT))
        self.assertIsNone(DirectionMapper.action_to_direction(InputAction.RESTART))
        self.assertIsNone(DirectionMapper.action_to_direction(InputAction.MENU))
        self.assertIsNone(DirectionMapper.action_to_direction(InputAction.SELECT))
        self.assertIsNone(DirectionMapper.action_to_direction(InputAction.NONE))
    
    def test_direction_mapping_prevents_backwards_movement(self):
        """Test that direction constants match expected game behavior"""
        # This test ensures the critical mapping is maintained:
        # UP (0) <-> DOWN (2) are opposites
        # LEFT (1) <-> RIGHT (3) are opposites
        self.assertEqual((DirectionMapper.UP + 2) % 4, DirectionMapper.DOWN)
        self.assertEqual((DirectionMapper.LEFT + 2) % 4, DirectionMapper.RIGHT)


class TestTextUIInputHandler(unittest.TestCase):
    """Test suite for TextUIInputHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_renderer = Mock()
        self.input_handler = TextUIInputHandler(self.mock_renderer)
    
    def test_initialization(self):
        """Test TextUIInputHandler initializes correctly"""
        self.assertIsNotNone(self.input_handler.text_renderer)
        self.assertEqual(self.input_handler.text_renderer, self.mock_renderer)
    
    def test_get_input_returns_move_up_for_w_key(self):
        """Test that 'w' key maps to MOVE_UP"""
        self.mock_renderer.get_key_press.return_value = 'w'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_UP)
    
    def test_get_input_returns_move_up_for_arrow_up(self):
        """Test that up arrow maps to MOVE_UP"""
        self.mock_renderer.get_key_press.return_value = '\x1b[A'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_UP)
    
    def test_get_input_returns_move_left_for_a_key(self):
        """Test that 'a' key maps to MOVE_LEFT"""
        self.mock_renderer.get_key_press.return_value = 'a'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_LEFT)
    
    def test_get_input_returns_move_left_for_arrow_left(self):
        """Test that left arrow maps to MOVE_LEFT"""
        self.mock_renderer.get_key_press.return_value = '\x1b[D'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_LEFT)
    
    def test_get_input_returns_move_down_for_s_key(self):
        """Test that 's' key maps to MOVE_DOWN"""
        self.mock_renderer.get_key_press.return_value = 's'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_DOWN)
    
    def test_get_input_returns_move_down_for_arrow_down(self):
        """Test that down arrow maps to MOVE_DOWN"""
        self.mock_renderer.get_key_press.return_value = '\x1b[B'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_DOWN)
    
    def test_get_input_returns_move_right_for_d_key(self):
        """Test that 'd' key maps to MOVE_RIGHT"""
        self.mock_renderer.get_key_press.return_value = 'd'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_RIGHT)
    
    def test_get_input_returns_move_right_for_arrow_right(self):
        """Test that right arrow maps to MOVE_RIGHT"""
        self.mock_renderer.get_key_press.return_value = '\x1b[C'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MOVE_RIGHT)
    
    def test_get_input_returns_restart_for_r_key(self):
        """Test that 'r' key maps to RESTART"""
        self.mock_renderer.get_key_press.return_value = 'r'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.RESTART)
    
    def test_get_input_returns_quit_for_q_key(self):
        """Test that 'q' key maps to QUIT"""
        self.mock_renderer.get_key_press.return_value = 'q'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.QUIT)
    
    def test_get_input_returns_menu_for_escape(self):
        """Test that ESC key maps to MENU"""
        self.mock_renderer.get_key_press.return_value = '\x1b'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.MENU)
    
    def test_get_input_returns_select_for_enter(self):
        """Test that Enter key maps to SELECT"""
        self.mock_renderer.get_key_press.return_value = '\r'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.SELECT)
    
    def test_get_input_returns_select_for_newline(self):
        """Test that newline maps to SELECT"""
        self.mock_renderer.get_key_press.return_value = '\n'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.SELECT)
    
    def test_get_input_returns_none_for_no_key(self):
        """Test that no key press returns NONE"""
        self.mock_renderer.get_key_press.return_value = None
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.NONE)
    
    def test_get_input_returns_none_for_unknown_key(self):
        """Test that unknown key returns NONE"""
        self.mock_renderer.get_key_press.return_value = 'x'
        action = self.input_handler.get_input()
        self.assertEqual(action, InputAction.NONE)
    
    def test_get_input_handles_uppercase_keys(self):
        """Test that uppercase keys work correctly"""
        test_cases = [
            ('W', InputAction.MOVE_UP),
            ('A', InputAction.MOVE_LEFT),
            ('S', InputAction.MOVE_DOWN),
            ('D', InputAction.MOVE_RIGHT),
            ('R', InputAction.RESTART),
            ('Q', InputAction.QUIT),
        ]
        
        for key, expected_action in test_cases:
            self.mock_renderer.get_key_press.return_value = key
            action = self.input_handler.get_input()
            self.assertEqual(action, expected_action, f"Key {key} should map to {expected_action}")
    
    def test_cleanup_calls_disable_raw_mode(self):
        """Test that cleanup disables raw mode"""
        self.input_handler.cleanup()
        self.mock_renderer.disable_raw_mode.assert_called_once()


class TestInputHandlerIntegration(unittest.TestCase):
    """Integration tests for input handling with DirectionMapper"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_renderer = Mock()
        self.input_handler = TextUIInputHandler(self.mock_renderer)
    
    def test_complete_input_to_direction_flow(self):
        """Test complete flow from key press to direction value"""
        # Test each movement key produces correct direction
        test_cases = [
            ('w', 0),  # UP
            ('a', 1),  # LEFT
            ('s', 2),  # DOWN
            ('d', 3),  # RIGHT
        ]
        
        for key, expected_direction in test_cases:
            self.mock_renderer.get_key_press.return_value = key
            action = self.input_handler.get_input()
            direction = DirectionMapper.action_to_direction(action)
            self.assertEqual(direction, expected_direction, 
                           f"Key {key} should produce direction {expected_direction}")
    
    def test_arrow_keys_produce_same_directions_as_wasd(self):
        """Test that arrow keys produce same directions as WASD"""
        wasd_arrow_pairs = [
            ('w', '\x1b[A'),  # UP
            ('a', '\x1b[D'),  # LEFT
            ('s', '\x1b[B'),  # DOWN
            ('d', '\x1b[C'),  # RIGHT
        ]
        
        for wasd_key, arrow_key in wasd_arrow_pairs:
            # Get direction from WASD
            self.mock_renderer.get_key_press.return_value = wasd_key
            wasd_action = self.input_handler.get_input()
            wasd_direction = DirectionMapper.action_to_direction(wasd_action)
            
            # Get direction from arrow
            self.mock_renderer.get_key_press.return_value = arrow_key
            arrow_action = self.input_handler.get_input()
            arrow_direction = DirectionMapper.action_to_direction(arrow_action)
            
            # Should be the same
            self.assertEqual(wasd_direction, arrow_direction,
                           f"{wasd_key} and {arrow_key} should produce same direction")


if __name__ == '__main__':
    unittest.main()
