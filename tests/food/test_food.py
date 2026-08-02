from food.food import Food, FOOD_TYPE_GROWTH


def test_get_color_returns_constructor_color():
    food = Food((10, 20, 30))
    assert food.getColor() == (10, 20, 30)


def test_food_is_named_food_entity():
    food = Food((10, 20, 30))
    assert food.getName() == "Food"


def test_food_defaults_to_growth_type():
    food = Food((10, 20, 30))
    assert food.getFoodType() == FOOD_TYPE_GROWTH


def test_food_type_can_be_set_explicitly():
    food = Food((10, 20, 30), FOOD_TYPE_GROWTH)
    assert food.getFoodType() == FOOD_TYPE_GROWTH
