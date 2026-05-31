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
