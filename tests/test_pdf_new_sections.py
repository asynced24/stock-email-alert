from pdf_builder import _screen_rows


def test_screen_rows_maps_fields():
    data = [{"company": "Alpha", "symbol": "AAA", "price": "100.00",
             "5d": "+2.00%", "1mo": "-1.00%", "3mo": "+5.00%", "1yr": "+60.00%"}]
    rows = _screen_rows(data)
    assert rows[0][0] == "Alpha"
    assert rows[0][1] == "AAA"
    assert rows[0][2] == "100.00"
    assert rows[0][-1] == "+60.00%"


def test_screen_rows_handles_missing_keys():
    rows = _screen_rows([{"symbol": "BBB"}])
    assert rows[0][0] == "-"      # missing company -> placeholder
    assert rows[0][1] == "BBB"


def test_build_pdf_new_shapes_render(tmp_path):
    """build_pdf renders with the v2 Section-4 volume fields and split Section-9 args."""
    from pdf_builder import build_pdf
    screen = [{"company": "Alpha", "symbol": "AAA", "price": "100.00",
               "5d": "+2.00%", "1mo": "-1.00%", "3mo": "+5.00%", "1yr": "+60.00%"}]
    near = [{"company": "Beta", "symbol": "BBB", "price": "50.00", "ma": "49.50",
             "5d": "+1.0%", "1mo": "+2.0%", "3mo": "+3.0%", "1yr": "+10.0%"}]
    companies = {
        "five_day":  screen,
        "one_month": [{**screen[0], "6mo": "+12%", "1yr": "+30%"}],
        "volume":    [{"company": "Gam", "symbol": "CCC", "price": "9.0", "5d": "+1%",
                       "avg2wk_disp": "1.2M", "spike_disp": "3.4x",
                       "peakvol_disp": "4.1M", "peak_date": "2026-05-28"}],
    }
    out = tmp_path / "r.pdf"
    build_pdf([], [], [], companies, [], section6_data=screen, section7_data=screen,
              section8_data=screen, section9_50_data=near, section9_200_data=near,
              output_path=str(out))
    assert out.exists() and out.stat().st_size > 0
