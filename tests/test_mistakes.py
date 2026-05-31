from config import load_mistakes


def test_load_mistakes_reads_tickers(tmp_path):
    f = tmp_path / "m.txt"
    f.write_text("# comment\nCAR\nAGI lost on earnings\n\nUNH\n")
    out = load_mistakes(str(f))
    assert out == ["CAR", "AGI lost on earnings", "UNH"]


def test_load_mistakes_missing_file_returns_empty():
    assert load_mistakes("does_not_exist_12345.txt") == []


def test_default_mistakes_file_has_nine_tickers():
    out = load_mistakes()   # reads the committed mistakes.txt
    assert out == ["CAR", "UNH", "FVI", "TNZ", "BTE", "MDA", "AEO", "LULU", "GOOG"]
