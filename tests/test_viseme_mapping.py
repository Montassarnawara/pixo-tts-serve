from app.viseme_mapping import rhubarb_shape_to_viseme_id


def test_known_shapes_map_correctly():
    assert rhubarb_shape_to_viseme_id("X") == 0
    assert rhubarb_shape_to_viseme_id("A") == 21
    assert rhubarb_shape_to_viseme_id("D") == 2
    assert rhubarb_shape_to_viseme_id("G") == 18


def test_unknown_shape_falls_back_to_silence():
    assert rhubarb_shape_to_viseme_id("Z") == 0
    assert rhubarb_shape_to_viseme_id("") == 0
