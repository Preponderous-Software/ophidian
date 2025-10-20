from datetime import datetime


class HighScoreEntry:
    """Represents a single high score entry"""
    
    def __init__(self, score, length, level, timestamp=None):
        """
        Initialize a high score entry
        
        Args:
            score: The cumulative score achieved
            length: The maximum snake length achieved
            level: The highest level reached
            timestamp: When the score was achieved (defaults to current time)
        """
        self.score = score
        self.length = length
        self.level = level
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def __eq__(self, other):
        """Compare two high score entries for equality"""
        if not isinstance(other, HighScoreEntry):
            return False
        return (self.score == other.score and 
                self.length == other.length and 
                self.level == other.level and 
                self.timestamp == other.timestamp)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'score': self.score,
            'length': self.length,
            'level': self.level,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary for JSON deserialization"""
        return cls(
            score=data.get('score', 0),
            length=data.get('length', 0),
            level=data.get('level', 1),
            timestamp=data.get('timestamp')
        )
