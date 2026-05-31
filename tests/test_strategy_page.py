from pdf_builder import ReportPDF, _strategy_page
from config import MANTRA, MANTRA_DEFS, load_mistakes


def test_strategy_page_renders_without_error():
    pdf = ReportPDF("test-date")
    _strategy_page(pdf, MANTRA, MANTRA_DEFS, load_mistakes())
    out = pdf.output()           # bytes; raises if rendering is broken
    assert out is not None and len(out) > 0
