# tests\test_pyEnvLibEnvironmentRepositoryImpl.py
import unittest
from unittest.mock import MagicMock

from src.config.config import Config
from src.environment.pyEnvLibEnvironmentRepositoryImpl import PyEnvLibEnvironmentRepositoryImpl
from src.lib.pyenvlib.entity import Entity
from src.lib.pyenvlib.location import Location
from src.snake.snakePart import SnakePart
from src.snake.snakePartRepository import SnakePartRepository


class TestPyEnvLibEnvironmentRepositoryImpl(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.tick_speed = 0.1
        self.mock_config.restart_upon_collision = True
        self.mock_config.initial_grid_size = 5
        self.mock_config.difficulty = "Normal"  # Add difficulty attribute
        self.mock_snake_part_repository = MagicMock(spec=SnakePartRepository)
        self.repository = PyEnvLibEnvironmentRepositoryImpl(1, self.mock_config, self.mock_snake_part_repository)

    def test_get_rows(self):
        # Arrange
        self.repository.environment.getGrid = MagicMock()
        self.repository.environment.getGrid().getRows.return_value = 10

        # Act
        rows = self.repository.get_rows()

        # Assert
        self.assertEqual(rows, 10)

    def test_get_columns(self):
        # Arrange
        self.repository.environment.getGrid = MagicMock()
        self.repository.environment.getGrid().getColumns.return_value = 15

        # Act
        columns = self.repository.get_columns()

        # Assert
        self.assertEqual(columns, 15)

    def test_get_location(self):
        # Arrange
        self.repository.environment.getGrid = MagicMock()
        mock_location = MagicMock(spec=Location)
        self.repository.environment.getGrid().getLocation.return_value = mock_location

        # Act
        location = self.repository.get_location(1, 2)

        # Assert
        self.assertEqual(location, mock_location)
        self.repository.environment.getGrid().getLocation.assert_called_once_with(1, 2)

    def test_get_num_locations(self):
        # Arrange
        self.repository.environment.getGrid = MagicMock()
        mock_locations = [MagicMock(spec=Location) for _ in range(20)]
        self.repository.environment.getGrid().getLocations.return_value = mock_locations

        # Act
        num_locations = self.repository.get_num_locations()

        # Assert
        self.assertEqual(num_locations, 20)

    def test_get_location_of_entity(self):
        # Arrange
        entity = MagicMock(spec=Entity)
        entity.getLocationID.return_value = "location_id"
        mock_location = MagicMock(spec=Location)
        self.repository.environment.getGrid = MagicMock()
        self.repository.environment.getGrid().getLocation.return_value = mock_location

        # Act
        location = self.repository.get_location_of_entity(entity)

        # Assert
        self.assertEqual(location, mock_location)
        self.repository.environment.getGrid().getLocation.assert_called_once_with("location_id")

    def test_add_entity_to_random_location(self):
        # Arrange
        mock_snake_part = MagicMock(spec=SnakePart)
        random_location = MagicMock(spec=Location)
        self.repository.get_random_location = MagicMock(return_value=random_location)
        self.repository.add_entity_to_location = MagicMock()

        # Act
        self.repository.add_entity_to_random_location(mock_snake_part)

        # Assert
        self.repository.add_entity_to_location.assert_called_once_with(mock_snake_part, random_location)

    def test_add_entity_to_location(self):
        # Arrange
        entity = MagicMock(spec=Entity)
        location = MagicMock(spec=Location)
        self.repository.environment.addEntityToLocation = MagicMock()

        # Act
        self.repository.add_entity_to_location(entity, location)

        # Assert
        self.repository.environment.addEntityToLocation.assert_called_once_with(entity, location)

    def test_remove_entity_from_location(self):
        # Arrange
        entity = MagicMock(spec=Entity)
        self.repository.environment.removeEntity = MagicMock()

        # Act
        self.repository.remove_entity_from_location(entity)

        # Assert
        self.repository.environment.removeEntity.assert_called_once_with(entity)

    # def test_spawn_snake_part_new_snake_generated(self):
    #     # TODO: implement this test

    def test_spawn_food(self):
        # Arrange
        random_location = MagicMock(spec=Location)
        random_location.getNumEntities.return_value = 0
        food_mock = MagicMock()
        self.repository.get_random_location = MagicMock(return_value=random_location)
        self.repository.add_entity_to_location = MagicMock()

        # Act
        self.repository.spawn_food()

        # Assert
        self.repository.add_entity_to_location.assert_called_once()

    def test_clear(self):
        # Arrange
        mock_location = MagicMock(spec=Location)
        self.repository.environment.getGrid = MagicMock()
        self.repository.environment.getGrid().getLocations.return_value = ["loc1"]
        self.repository.environment.getGrid().getLocation.return_value = mock_location
        mock_location.getEntities.return_value.values.return_value = []
        self.repository.environment.removeEntity = MagicMock()
        self.repository.snake_part_repository.clear = MagicMock()

        # Act
        self.repository.clear()

        # Assert
        self.repository.environment.removeEntity.assert_not_called()
