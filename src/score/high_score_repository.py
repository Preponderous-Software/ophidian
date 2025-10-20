import json
import logging
import os
from pathlib import Path
from .high_score_entry import HighScoreEntry

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)


class HighScoreRepository:
    """Repository for managing high scores with JSON persistence"""
    
    def __init__(self, file_path='high_scores.json', max_scores=10):
        """
        Initialize the high score repository
        
        Args:
            file_path: Path to the JSON file for storing high scores
            max_scores: Maximum number of high scores to keep (default: 10)
        """
        self.file_path = Path(file_path)
        self.max_scores = max_scores
    
    def save(self, high_scores):
        """
        Save high scores to JSON file
        
        Args:
            high_scores: List of HighScoreEntry objects
        """
        try:
            data = [entry.to_dict() for entry in high_scores]
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(high_scores)} high scores to {self.file_path}")
        except IOError as e:
            logger.error(f"Could not save high scores: {e}")
    
    def load(self):
        """
        Load high scores from JSON file
        
        Returns:
            List of HighScoreEntry objects, sorted by score (highest first)
        """
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    entries = [HighScoreEntry.from_dict(entry) for entry in data]
                    # Sort by score (highest first)
                    entries.sort(key=lambda x: x.score, reverse=True)
                    logger.debug(f"Loaded {len(entries)} high scores from {self.file_path}")
                    return entries
            logger.debug(f"No high scores file found at {self.file_path}")
            return []
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Could not load high scores: {e}")
            return []
    
    def add_score(self, score_entry):
        """
        Add a new high score entry and save
        
        Args:
            score_entry: HighScoreEntry object to add
            
        Returns:
            True if the score was added to the high scores list, False otherwise
        """
        high_scores = self.load()
        
        # Add the new score
        high_scores.append(score_entry)
        
        # Sort by score (highest first)
        high_scores.sort(key=lambda x: x.score, reverse=True)
        
        # Check if the new score made it into the top scores
        is_high_score = any(entry == score_entry for entry in high_scores[:self.max_scores])
        
        # Keep only the top scores
        high_scores = high_scores[:self.max_scores]
        
        # Save the updated list
        self.save(high_scores)
        
        logger.info(f"Added score {score_entry.score} - Is high score: {is_high_score}")
        return is_high_score
    
    def is_high_score(self, score):
        """
        Check if a score qualifies as a high score
        
        Args:
            score: The score to check
            
        Returns:
            True if the score would make it into the high scores list
        """
        high_scores = self.load()
        
        # If we have fewer than max_scores, any score qualifies
        if len(high_scores) < self.max_scores:
            return True
        
        # Check if score is higher than the lowest high score
        return score > high_scores[-1].score
    
    def clear(self):
        """Clear all high scores"""
        try:
            if self.file_path.exists():
                self.file_path.unlink()
                logger.info("Cleared all high scores")
        except IOError as e:
            logger.error(f"Could not clear high scores: {e}")
