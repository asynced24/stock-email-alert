from pdf_builder import ReportPDF, FONT


def test_body_font_regular_after_page_break():
    pdf = ReportPDF("test-date")
    pdf.section_title("S")
    headers = ["A", "B"]
    widths  = [140, 140]
    rows = [[f"r{i}", "x"] for i in range(120)]   # enough rows to force >=1 page break
    pdf.table(headers, widths, rows)
    # After rendering, the active font must be the regular body face, not bold.
    assert pdf.font_style == ""        # "" = regular, "B" = bold
    assert pdf.font_family == FONT.lower()
