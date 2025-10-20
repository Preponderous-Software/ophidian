import unittest
from unittest.mock import Mock, patch, MagicMock
from src.textui.text_renderer import TextRenderer
from src.config.config import Config


class TestTextRenderer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.text_renderer = TextRenderer(self.config)
    
    def test_text_renderer_initialization(self):
        """Test that TextRenderer initializes correctly"""
        self.assertIsNotNone(self.text_renderer)
        self.assertEqual(self.text_renderer.config, self.config)
        self.assertIsNone(self.text_renderer.old_settings)
    
    @patch('src.textui.text_renderer.sys.stdout')
    def test_clear_screen_unix(self, mock_stdout):
        """Test clear_screen on Unix-like systems (using ANSI codes)"""
        with patch('src.textui.text_renderer.os.name', 'posix'):
            self.text_renderer.clear_screen()
            # Check that ANSI escape codes were written
            mock_stdout.write.assert_called_once_with('\033[2J\033[H')
            mock_stdout.flush.assert_called_once()
    
    @patch('src.textui.text_renderer.os.system')
    def test_clear_screen_windows(self, mock_system):
        """Test clear_screen on Windows (using os.system fallback)"""
        with patch('src.textui.text_renderer.os.name', 'nt'):
            self.text_renderer.clear_screen()
            mock_system.assert_called_once_with('cls')
    
    def test_render_grid(self):
        """Test render_grid method"""
        # Create mock objects
        mock_env_repo = Mock()
        mock_snake_repo = Mock()
        
        # Set up mock environment repository
        mock_env_repo.get_rows.return_value = 5
        mock_env_repo.get_columns.return_value = 5
        mock_env_repo.get_locations.return_value = []
        
        # Set up mock snake repository with get_all method
        mock_snake_repo.get_all.return_value = []
        
        # Test that render_grid doesn't crash with empty grid
        with patch('builtins.print'):
            self.text_renderer.render_grid(mock_env_repo, mock_snake_repo, False)
    
    def test_render_stats(self):
        """Test render_stats method"""
        with patch('builtins.print'):
            self.text_renderer.render_stats(
                level=1,
                snake_length=5,
                current_score=100,
                cumulative_score=250,
                percentage=0.5
            )
    
    def test_render_controls(self):
        """Test render_controls method"""
        with patch('builtins.print'):
            self.text_renderer.render_controls()
    
    def test_render_menu(self):
        """Test render_menu method"""
        with patch('builtins.print'):
            with patch.object(self.text_renderer, 'clear_screen'):
                self.text_renderer.render_menu(
                    "Test Menu",
                    ["Option 1", "Option 2"],
                    0
                )
    
    @patch('src.textui.text_renderer.termios')
    @patch('src.textui.text_renderer.tty')
    def test_enable_raw_mode_unix(self, mock_tty, mock_termios):
        """Test enable_raw_mode on Unix-like systems"""
        with patch('src.textui.text_renderer.os.name', 'posix'):
            with patch('src.textui.text_renderer.sys.stdin') as mock_stdin:
                mock_stdin.fileno.return_value = 0
                mock_termios.tcgetattr.return_value = "test_settings"
                
                self.text_renderer.enable_raw_mode()
                
                mock_termios.tcgetattr.assert_called_once()
                mock_tty.setcbreak.assert_called_once()
                self.assertEqual(self.text_renderer.old_settings, "test_settings")
    
    @patch('src.textui.text_renderer.termios')
    def test_disable_raw_mode_unix(self, mock_termios):
        """Test disable_raw_mode on Unix-like systems"""
        with patch('src.textui.text_renderer.os.name', 'posix'):
            with patch('src.textui.text_renderer.sys.stdin') as mock_stdin:
                self.text_renderer.old_settings = "test_settings"
                
                self.text_renderer.disable_raw_mode()
                
                mock_termios.tcsetattr.assert_called_once()


if __name__ == '__main__':
    unittest.main()
