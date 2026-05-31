from pdf_builder import pct_fill_color


def test_zero_change_is_white():
    assert pct_fill_color(0.0) == (255, 255, 255)


def test_strong_positive_is_darker_green_than_weak():
    weak = pct_fill_color(2.0)
    strong = pct_fill_color(25.0)
    assert strong[0] < weak[0]
    assert strong[2] < weak[2]


def test_strong_negative_is_darker_red_than_weak():
    weak = pct_fill_color(-2.0)
    strong = pct_fill_color(-25.0)
    assert strong[1] < weak[1]
    assert strong[2] < weak[2]


def test_clamps_beyond_range():
    assert pct_fill_color(999) == pct_fill_color(20)
    assert pct_fill_color(-999) == pct_fill_color(-20)
