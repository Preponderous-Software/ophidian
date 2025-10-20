import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from src.score.high_score_entry import HighScoreEntry
from src.score.high_score_repository import HighScoreRepository


class TestHighScoreEntry(unittest.TestCase):
    """Test the HighScoreEntry class"""
    
    def test_initialization(self):
        """Test creating a high score entry"""
        entry = HighScoreEntry(score=1000, length=50, level=5)
        
        self.assertEqual(entry.score, 1000)
        self.assertEqual(entry.length, 50)
        self.assertEqual(entry.level, 5)
        self.assertIsNotNone(entry.timestamp)
    
    def test_initialization_with_timestamp(self):
        """Test creating a high score entry with custom timestamp"""
        timestamp = "2024-01-01T12:00:00"
        entry = HighScoreEntry(score=1000, length=50, level=5, timestamp=timestamp)
        
        self.assertEqual(entry.timestamp, timestamp)
    
    def test_to_dict(self):
        """Test converting to dictionary"""
        entry = HighScoreEntry(score=1000, length=50, level=5, timestamp="2024-01-01T12:00:00")
        data = entry.to_dict()
        
        self.assertEqual(data['score'], 1000)
        self.assertEqual(data['length'], 50)
        self.assertEqual(data['level'], 5)
        self.assertEqual(data['timestamp'], "2024-01-01T12:00:00")
    
    def test_from_dict(self):
        """Test creating from dictionary"""
        data = {
            'score': 1000,
            'length': 50,
            'level': 5,
            'timestamp': "2024-01-01T12:00:00"
        }
        entry = HighScoreEntry.from_dict(data)
        
        self.assertEqual(entry.score, 1000)
        self.assertEqual(entry.length, 50)
        self.assertEqual(entry.level, 5)
        self.assertEqual(entry.timestamp, "2024-01-01T12:00:00")


class TestHighScoreRepository(unittest.TestCase):
    """Test the HighScoreRepository class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.repository = HighScoreRepository(file_path=self.temp_file.name, max_scores=5)
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_save_and_load_empty_list(self):
        """Test saving and loading an empty list"""
        self.repository.save([])
        loaded = self.repository.load()
        self.assertEqual(loaded, [])
    
    def test_save_and_load_single_entry(self):
        """Test saving and loading a single entry"""
        entry = HighScoreEntry(score=1000, length=50, level=5)
        self.repository.save([entry])
        
        loaded = self.repository.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].score, 1000)
        self.assertEqual(loaded[0].length, 50)
        self.assertEqual(loaded[0].level, 5)
    
    def test_save_and_load_multiple_entries(self):
        """Test saving and loading multiple entries"""
        entries = [
            HighScoreEntry(score=1000, length=50, level=5),
            HighScoreEntry(score=800, length=40, level=4),
            HighScoreEntry(score=600, length=30, level=3)
        ]
        self.repository.save(entries)
        
        loaded = self.repository.load()
        self.assertEqual(len(loaded), 3)
        # Verify they're sorted by score (highest first)
        self.assertEqual(loaded[0].score, 1000)
        self.assertEqual(loaded[1].score, 800)
        self.assertEqual(loaded[2].score, 600)
    
    def test_load_sorts_by_score(self):
        """Test that loading sorts entries by score"""
        # Save entries in unsorted order
        entries = [
            HighScoreEntry(score=600, length=30, level=3),
            HighScoreEntry(score=1000, length=50, level=5),
            HighScoreEntry(score=800, length=40, level=4)
        ]
        self.repository.save(entries)
        
        loaded = self.repository.load()
        # Should be sorted by score (highest first)
        self.assertEqual(loaded[0].score, 1000)
        self.assertEqual(loaded[1].score, 800)
        self.assertEqual(loaded[2].score, 600)
    
    def test_load_nonexistent_file(self):
        """Test loading when file doesn't exist"""
        # Use a non-existent file path
        repo = HighScoreRepository(file_path='/tmp/nonexistent_high_scores.json')
        loaded = repo.load()
        self.assertEqual(loaded, [])
    
    def test_add_score_to_empty_list(self):
        """Test adding a score to an empty list"""
        entry = HighScoreEntry(score=1000, length=50, level=5)
        is_high_score = self.repository.add_score(entry)
        
        self.assertTrue(is_high_score)
        loaded = self.repository.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].score, 1000)
    
    def test_add_score_maintains_max_scores(self):
        """Test that only max_scores entries are kept"""
        # Add 6 scores (max is 5)
        for i in range(6):
            entry = HighScoreEntry(score=1000 - i * 100, length=50 - i * 5, level=5)
            self.repository.add_score(entry)
        
        loaded = self.repository.load()
        self.assertEqual(len(loaded), 5)
        # Lowest score should not be in the list
        self.assertNotEqual(loaded[-1].score, 500)
    
    def test_add_score_returns_correct_status(self):
        """Test that add_score returns correct high score status"""
        # Fill up with 5 scores (max is 5)
        for i in range(5):
            entry = HighScoreEntry(score=1000 - i * 100, length=50, level=5)
            self.repository.add_score(entry)
        
        # Add a score that makes it into the list
        high_entry = HighScoreEntry(score=900, length=50, level=5)
        is_high_score = self.repository.add_score(high_entry)
        self.assertTrue(is_high_score)
        
        # Add a score that doesn't make it into the list
        low_entry = HighScoreEntry(score=100, length=10, level=1)
        is_high_score = self.repository.add_score(low_entry)
        self.assertFalse(is_high_score)
    
    def test_is_high_score_with_empty_list(self):
        """Test is_high_score with empty list"""
        self.assertTrue(self.repository.is_high_score(100))
    
    def test_is_high_score_with_partial_list(self):
        """Test is_high_score when list is not full"""
        # Add 3 scores (max is 5)
        for i in range(3):
            entry = HighScoreEntry(score=1000 - i * 100, length=50, level=5)
            self.repository.add_score(entry)
        
        # Any score should qualify
        self.assertTrue(self.repository.is_high_score(100))
    
    def test_is_high_score_with_full_list(self):
        """Test is_high_score when list is full"""
        # Fill up with 5 scores (max is 5)
        for i in range(5):
            entry = HighScoreEntry(score=1000 - i * 100, length=50, level=5)
            self.repository.add_score(entry)
        
        # Score higher than lowest should qualify
        self.assertTrue(self.repository.is_high_score(700))
        
        # Score lower than lowest should not qualify
        self.assertFalse(self.repository.is_high_score(500))
    
    def test_clear(self):
        """Test clearing all high scores"""
        # Add some scores
        for i in range(3):
            entry = HighScoreEntry(score=1000 - i * 100, length=50, level=5)
            self.repository.add_score(entry)
        
        # Clear
        self.repository.clear()
        
        # Should be empty now
        loaded = self.repository.load()
        self.assertEqual(loaded, [])


if __name__ == '__main__':
    unittest.main()
