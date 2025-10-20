import pygame
from src.lib.graphik.src.graphik import Graphik
from src.state.menu_state import MenuState
from src.score.high_score_repository import HighScoreRepository


class HighScoresMenu:
    def __init__(self, config, game_display):
        self.config = config
        self.game_display = game_display
        self.graphik = Graphik(game_display)
        self.high_score_repository = HighScoreRepository()
        self.scroll_offset = 0
        self.max_visible_scores = 8  # Number of scores visible on screen at once
        self._cached_high_scores = None  # Cache for high scores
    
    def refresh_scores(self):
        """Reload high scores from repository"""
        self._cached_high_scores = self.high_score_repository.load()
    
    def _get_high_scores(self):
        """Get high scores, loading them if not cached"""
        if self._cached_high_scores is None:
            self.refresh_scores()
        return self._cached_high_scores

    def handle_key_down(self, key):
        """Handle keyboard input - return to main menu on escape or enter, scroll with arrow keys"""
        high_scores = self._get_high_scores()
        max_scroll = max(0, len(high_scores) - self.max_visible_scores)
        
        if key == pygame.K_ESCAPE or key == pygame.K_RETURN:
            return MenuState.MAIN_MENU
        elif key == pygame.K_UP or key == pygame.K_w:
            # Scroll up
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == pygame.K_DOWN or key == pygame.K_s:
            # Scroll down
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
        
        return None

    def handle_mouse_click(self, pos):
        """Handle mouse clicks - return to main menu"""
        return MenuState.MAIN_MENU

    def draw(self):
        """Draw the high scores menu"""
        # Get current window size for dynamic rendering
        try:
            current_width, current_height = self.game_display.get_size()
        except (AttributeError, ValueError):
            # Fallback to config values for testing
            current_width, current_height = self.config.display_width, self.config.display_height
        
        # Clear screen with black background
        self.game_display.fill(self.config.black)
        
        # Draw title
        title_y = 50
        self.graphik.drawText(
            "HIGH SCORES",
            current_width // 2,
            title_y,
            self.config.text_size,
            self.config.green
        )
        
        # Load high scores
        high_scores = self._get_high_scores()
        
        if not high_scores:
            # No scores yet
            self.graphik.drawText(
                "No high scores yet!",
                current_width // 2,
                current_height // 2,
                self.config.text_size // 2,
                self.config.white
            )
            self.graphik.drawText(
                "Play the game to set a high score",
                current_width // 2,
                current_height // 2 + 50,
                self.config.text_size // 3,
                self.config.white
            )
        else:
            # Draw table header
            header_y = title_y + 80
            col_rank_x = current_width // 2 - 250
            col_score_x = current_width // 2 - 50
            col_length_x = current_width // 2 + 100
            col_level_x = current_width // 2 + 200
            
            header_size = self.config.text_size // 3
            self.graphik.drawText("RANK", col_rank_x, header_y, header_size, self.config.yellow)
            self.graphik.drawText("SCORE", col_score_x, header_y, header_size, self.config.yellow)
            self.graphik.drawText("LENGTH", col_length_x, header_y, header_size, self.config.yellow)
            self.graphik.drawText("LEVEL", col_level_x, header_y, header_size, self.config.yellow)
            
            # Draw scores
            score_start_y = header_y + 60
            score_spacing = 45
            text_size = self.config.text_size // 3
            
            # Bronze color for 3rd place
            bronze_color = (205, 127, 50)
            
            # Calculate which scores to display based on scroll offset
            start_idx = self.scroll_offset
            end_idx = min(start_idx + self.max_visible_scores, len(high_scores))
            
            for i in range(start_idx, end_idx):
                score_entry = high_scores[i]
                y_pos = score_start_y + (i - start_idx) * score_spacing
                
                # Highlight top 3 scores with different colors
                if i == 0:
                    color = self.config.green  # Gold for 1st
                elif i == 1:
                    color = self.config.white  # Silver for 2nd
                elif i == 2:
                    color = bronze_color  # Bronze for 3rd
                else:
                    color = self.config.white
                
                # Draw rank (1-indexed)
                self.graphik.drawText(f"#{i + 1}", col_rank_x, y_pos, text_size, color)
                
                # Draw score
                self.graphik.drawText(str(score_entry.score), col_score_x, y_pos, text_size, color)
                
                # Draw length
                self.graphik.drawText(str(score_entry.length), col_length_x, y_pos, text_size, color)
                
                # Draw level
                self.graphik.drawText(str(score_entry.level), col_level_x, y_pos, text_size, color)
            
            # Draw scroll indicators if needed
            if self.scroll_offset > 0:
                # Can scroll up
                self.graphik.drawText(
                    "▲ More above",
                    current_width // 2,
                    score_start_y - 30,
                    self.config.text_size // 4,
                    self.config.yellow
                )
            
            if end_idx < len(high_scores):
                # Can scroll down
                last_visible_y = score_start_y + (end_idx - start_idx - 1) * score_spacing
                self.graphik.drawText(
                    "▼ More below",
                    current_width // 2,
                    last_visible_y + 60,
                    self.config.text_size // 4,
                    self.config.yellow
                )
        
        # Draw instructions
        instructions_y = current_height - 60
        self.graphik.drawText(
            "Press ESC or ENTER to return to main menu",
            current_width // 2,
            instructions_y,
            self.config.text_size // 3,
            self.config.yellow
        )
        
        # Draw scroll instructions if there are enough scores
        if len(high_scores) > self.max_visible_scores:
            self.graphik.drawText(
                "Use UP/DOWN arrows to scroll",
                current_width // 2,
                instructions_y + 30,
                self.config.text_size // 4,
                self.config.yellow
            )