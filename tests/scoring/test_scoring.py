from scoring.scoring import (
    BASE_POINTS_PER_FOOD,
    applyScoreMultiplier,
    getGridFillPercentage,
    pointsForFood,
)


def test_grid_fill_percentage_is_a_whole_percent_of_the_grid():
    assert getGridFillPercentage(5, 100) == 5
    assert getGridFillPercentage(50, 100) == 50
    assert getGridFillPercentage(100, 100) == 100


def test_grid_fill_percentage_truncates_rather_than_rounding():
    assert getGridFillPercentage(1, 3) == 33


def test_grid_fill_percentage_is_zero_for_a_grid_with_no_locations():
    # guards the console stats readout against a divide-by-zero if it is
    # ever reached before an environment exists
    assert getGridFillPercentage(5, 0) == 0


def test_points_for_food_pay_the_base_plus_the_grid_fill_percentage():
    assert pointsForFood(25, 100) == BASE_POINTS_PER_FOOD + 25


def test_points_for_food_grow_as_the_board_fills():
    # a longer ophidian on a fuller board earns more per bite, which is the
    # shape the previous derived score had
    assert pointsForFood(10, 100) < pointsForFood(40, 100)


def test_points_for_food_are_never_zero_on_an_almost_empty_board():
    # a multiplier has to be visible even on the first bite of a run
    assert pointsForFood(1, 10000) == BASE_POINTS_PER_FOOD


def test_applying_a_multiplier_scales_an_award():
    assert applyScoreMultiplier(30, 2.0) == 60


def test_applying_a_multiplier_of_one_leaves_an_award_alone():
    assert applyScoreMultiplier(30, 1.0) == 30


def test_applying_a_multiplier_keeps_the_award_a_whole_number():
    # no renderer should ever have to format a fractional score
    assert applyScoreMultiplier(31, 1.5) == 46
    assert isinstance(applyScoreMultiplier(31, 1.5), int)
