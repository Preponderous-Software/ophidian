# @author Daniel McCoy Stephenson
# @since August 6th, 2022

import json
import os
import pygame

# @author Daniel McCoy Stephenson
# @since August 6th, 2022
class Config:
    def __init__(self):
        # UI mode
        self.use_text_ui = False
        
        # display
        self.display_width = 500
        self.display_height = 500
        self.fullscreen = False
        self.black = (0, 0, 0)
        self.white = (255, 255, 255)
        self.green = (0, 255, 0)
        self.red = (255, 0, 0)
        self.yellow = (255, 255, 0)
        self.blue = (0, 0, 255)
        self.gray = (128, 128, 128)
        self.text_size = 50

        # audio settings
        self.master_volume = 0.7
        self.music_volume = 0.5
        self.sfx_volume = 0.8

        # grid size
        self.initial_grid_size = 5

        # tick speed
        self.limit_tick_speed = True
        self.tick_speed = 0.1
        
        # text UI performance settings
        self.text_ui_target_fps = 30  # Target framerate for text UI (30 FPS is smooth enough for terminal)

        # difficulty settings
        self.difficulty = "Normal"  # Easy, Normal, Hard
        
        # key bindings
        self.key_bindings = {
            'move_up': pygame.K_w,
            'move_down': pygame.K_s,
            'move_left': pygame.K_a,
            'move_right': pygame.K_d,
            'fullscreen': pygame.K_F11,
            'restart': pygame.K_r,
            'quit': pygame.K_q
        }

        # misc
        self.debug = False
        self.restart_upon_collision = True
        self.level_progress_percentage_required = 0.25
        
        # Load saved settings
        self.load_settings()

    def get_available_resolutions(self):
        """Get available display resolutions"""
        return [
            (500, 500),
            (800, 600),
            (1024, 768),
            (1280, 720),
            (1920, 1080)
        ]
    
    def get_difficulty_levels(self):
        """Get available difficulty levels"""
        return ["Easy", "Normal", "Hard"]
    
    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'use_text_ui': self.use_text_ui,
            'display_width': self.display_width,
            'display_height': self.display_height,
            'fullscreen': self.fullscreen,
            'master_volume': self.master_volume,
            'music_volume': self.music_volume,
            'sfx_volume': self.sfx_volume,
            'limit_tick_speed': self.limit_tick_speed,
            'tick_speed': self.tick_speed,
            'text_ui_target_fps': self.text_ui_target_fps,
            'difficulty': self.difficulty,
            'initial_grid_size': self.initial_grid_size,
            'level_progress_percentage_required': self.level_progress_percentage_required,
            'key_bindings': self.key_bindings
        }
        
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save settings: {e}")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            with open('config/settings.json', 'r') as f:
                settings = json.load(f)
                
            self.use_text_ui = settings.get('use_text_ui', self.use_text_ui)
            self.display_width = settings.get('display_width', self.display_width)
            self.display_height = settings.get('display_height', self.display_height)
            self.fullscreen = settings.get('fullscreen', self.fullscreen)
            self.master_volume = settings.get('master_volume', self.master_volume)
            self.music_volume = settings.get('music_volume', self.music_volume)
            self.sfx_volume = settings.get('sfx_volume', self.sfx_volume)
            self.limit_tick_speed = settings.get('limit_tick_speed', self.limit_tick_speed)
            self.tick_speed = settings.get('tick_speed', self.tick_speed)
            self.text_ui_target_fps = settings.get('text_ui_target_fps', self.text_ui_target_fps)
            self.difficulty = settings.get('difficulty', self.difficulty)
            self.initial_grid_size = settings.get('initial_grid_size', self.initial_grid_size)
            self.level_progress_percentage_required = settings.get('level_progress_percentage_required', self.level_progress_percentage_required)
            
            # Load key bindings, ensuring they are valid pygame key constants
            saved_bindings = settings.get('key_bindings', {})
            for key, value in saved_bindings.items():
                if key in self.key_bindings and isinstance(value, int):
                    self.key_bindings[key] = value
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is invalid, use defaults
            pass
