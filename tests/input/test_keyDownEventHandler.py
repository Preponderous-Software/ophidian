import unittest
from unittest.mock import MagicMock

import pygame
from src.input.keyDownEventHandler import KeyDownEventHandler


class TestKeyDownEventHandler(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.key_bindings = {
            'quit': pygame.K_q,
            'move_up': pygame.K_w,
            'move_left': pygame.K_a,
            'move_down': pygame.K_s,
            'move_right': pygame.K_d,
            'fullscreen': pygame.K_F11,
            'restart': pygame.K_r
        }
        self.config.fullscreen = False
        self.config.limit_tick_speed = True
        self.game_display = MagicMock()
        self.selected_snake_part = MagicMock()
        self.handler = KeyDownEventHandler(self.config, self.game_display, self.selected_snake_part)

    def test_handle_key_down_event_quit(self):
        # Act
        result = self.handler.handle_key_down_event(pygame.K_q)

        # Assert
        self.assertEqual(result, "quit")

    def test_handle_key_down_event_up(self):
        # Arrange
        self.selected_snake_part.getDirection.return_value = 1
        self.handler.changed_direction_this_tick = False

        # Act
        result = self.handler.handle_key_down_event(pygame.K_w)

        # Assert
        self.selected_snake_part.setDirection.assert_called_once_with(0)
        self.assertIsNone(result)

    def test_handle_key_down_event_left(self):
        # Arrange
        self.selected_snake_part.getDirection.return_value = 0
        self.handler.changed_direction_this_tick = False

        # Act
        result = self.handler.handle_key_down_event(pygame.K_a)

        # Assert
        self.selected_snake_part.setDirection.assert_called_once_with(1)
        self.assertIsNone(result)

    def test_handle_key_down_event_down(self):
        # Arrange
        self.selected_snake_part.getDirection.return_value = 3
        self.handler.changed_direction_this_tick = False

        # Act
        result = self.handler.handle_key_down_event(pygame.K_s)

        # Assert
        self.selected_snake_part.setDirection.assert_called_once_with(2)
        self.assertIsNone(result)

    def test_handle_key_down_event_right(self):
        # Arrange
        self.selected_snake_part.getDirection.return_value = 2
        self.handler.changed_direction_this_tick = False

        # Act
        result = self.handler.handle_key_down_event(pygame.K_d)

        # Assert
        self.selected_snake_part.setDirection.assert_called_once_with(3)
        self.assertIsNone(result)

    def test_handle_key_down_event_fullscreen_toggle(self):
        # Arrange
        self.config.fullscreen = True

        # Act
        result = self.handler.handle_key_down_event(pygame.K_F11)

        # Assert
        self.assertFalse(self.config.fullscreen)
        self.assertEqual(result, "initialize game display")

    def test_handle_key_down_event_limit_tick_speed_toggle(self):
        # Arrange
        self.config.limit_tick_speed = False

        # Act
        result = self.handler.handle_key_down_event(pygame.K_l)

        # Assert
        self.assertTrue(self.config.limit_tick_speed)
        self.assertIsNone(result)

    def test_handle_key_down_event_restart(self):
        # Act
        result = self.handler.handle_key_down_event(pygame.K_r)

        # Assert
        self.assertEqual(result, "restart")

    def test_handle_key_down_event_unknown(self):
        # Act
        result = self.handler.handle_key_down_event(pygame.K_x)

        # Assert
        self.assertEqual(result, "unknown")


if __name__ == '__main__':
    unittest.main()
