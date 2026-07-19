from food.food import Food, FOOD_TYPE_GROWTH, FOOD_TYPE_SPEED


def test_get_color_returns_constructor_color():
    food = Food((10, 20, 30))
    assert food.getColor() == (10, 20, 30)


def test_food_is_named_food_entity():
    food = Food((10, 20, 30))
    assert food.getName() == "Food"


def test_food_defaults_to_growth_type():
    food = Food((10, 20, 30))
    assert food.getFoodType() == FOOD_TYPE_GROWTH


def test_food_can_be_constructed_as_speed_type():
    food = Food((10, 20, 30), FOOD_TYPE_SPEED)
    assert food.getFoodType() == FOOD_TYPE_SPEED
