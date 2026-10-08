from snake.snakePart import SnakePart


def chain(length):
    # parts[0] is the head; each part's previous is the one behind it,
    # linked the way Ophidian.spawnSnakePart grows the snake
    parts = [SnakePart((10, 20, 30)) for _ in range(length)]
    for ahead, behind in zip(parts, parts[1:]):
        ahead.setPrevious(behind)
        behind.setNext(ahead)
    return parts


def test_set_color_updates_get_color():
    part = SnakePart((10, 20, 30))
    part.setColor((40, 50, 60))
    assert part.getColor() == (40, 50, 60)


def test_snake_part_is_named_snake_part_entity():
    part = SnakePart((10, 20, 30))
    assert part.getName() == "Snake Part"


def test_new_part_faces_up_and_is_unlinked():
    part = SnakePart((10, 20, 30))
    assert part.getDirection() == 0
    assert not part.hasNext()
    assert not part.hasPrevious()
    assert part.lastPosition == -1


def test_set_direction_updates_get_direction():
    part = SnakePart((10, 20, 30))
    part.setDirection(3)
    assert part.getDirection() == 3


def test_set_last_position_records_position():
    part = SnakePart((10, 20, 30))
    part.setLastPosition("sentinel-location")
    assert part.lastPosition == "sentinel-location"


def test_linking_parts_sets_has_next_and_has_previous():
    head, tail = chain(2)
    assert head.hasPrevious()
    assert not head.hasNext()
    assert tail.hasNext()
    assert not tail.hasPrevious()


def test_get_tail_of_lone_part_is_itself():
    part = SnakePart((10, 20, 30))
    assert part.getTail() is part


def test_get_tail_of_two_part_snake_is_the_part_behind():
    head, tail = chain(2)
    assert head.getTail() is tail


def test_get_tail_walks_the_whole_chain():
    parts = chain(5)
    assert parts[0].getTail() is parts[-1]


def test_get_tail_from_a_middle_part_finds_the_same_tail():
    parts = chain(5)
    assert parts[2].getTail() is parts[-1]


def test_get_tail_of_the_tail_is_itself():
    parts = chain(5)
    assert parts[-1].getTail() is parts[-1]
