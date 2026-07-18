from food.food import Food


def test_get_color_returns_constructor_color():
    food = Food((10, 20, 30))
    assert food.getColor() == (10, 20, 30)


def test_food_is_named_food_entity():
    food = Food((10, 20, 30))
    assert food.getName() == "Food"
