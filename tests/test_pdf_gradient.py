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


def test_spike_fill_color_scales_amber():
    from pdf_builder import spike_fill_color
    low  = spike_fill_color("2.0x")    # at threshold -> light amber
    high = spike_fill_color("6.0x")    # big spike -> deep amber
    # deeper spike => darker (every channel lower or equal, and clearly darker overall)
    assert sum(high) < sum(low)
    # light end is near amber-100, dark end near amber-700
    assert low[0] > 240 and high[0] < 200
    # unparseable -> white
    assert spike_fill_color("-") == (255, 255, 255)


def test_spike_fill_color_clamps():
    from pdf_builder import spike_fill_color
    assert spike_fill_color("99x") == spike_fill_color("6.0x")   # saturates at hi
    assert spike_fill_color("1.0x") == spike_fill_color("2.0x")  # floors at lo
