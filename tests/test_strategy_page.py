from pdf_builder import ReportPDF, _cover_page
from config import MANTRA, MANTRA_DEFS, load_mistakes


def test_cover_page_renders_without_error():
    # The cover + strategy content is now combined on the first page.
    pdf = ReportPDF("test-date")
    _cover_page(pdf, "test-date", MANTRA, MANTRA_DEFS, load_mistakes())
    out = pdf.output()           # bytes; raises if rendering is broken
    assert out is not None and len(out) > 0
