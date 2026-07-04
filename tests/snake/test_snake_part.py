from snake.snakePart import SnakePart


def test_set_color_updates_get_color():
    part = SnakePart((10, 20, 30))
    part.setColor((40, 50, 60))
    assert part.getColor() == (40, 50, 60)
