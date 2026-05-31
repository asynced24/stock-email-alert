from pdf_builder import ReportPDF, FONT


def test_body_font_bold_and_consistent_after_page_break():
    pdf = ReportPDF("test-date")
    pdf.section_title("S")
    headers = ["A", "B"]
    widths  = [140, 140]
    rows = [[f"r{i}", "x"] for i in range(120)]   # enough rows to force >=1 page break
    pdf.table(headers, widths, rows)
    # Body text is intentionally bold; the reset-after-header keeps it consistent
    # across page breaks (the original bug left continuation pages in the wrong state).
    assert pdf.font_style == "B"       # "" = regular, "B" = bold
    assert pdf.font_family == FONT.lower()
