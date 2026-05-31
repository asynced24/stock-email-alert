"""
PDF Builder: assembles all 5 sections into a single PDF report.
Uses fpdf2 in landscape A4 orientation.
Color-codes percentage change cells (green = positive, red = negative).
"""
from datetime import datetime

from fpdf import FPDF


def _safe(text):
    """
    Sanitize a string so it only contains Latin-1 encodable characters.
    Replaces common Unicode punctuation with ASCII equivalents, then
    falls back to dropping anything that still won't encode.
    """
    if text is None:
        return "NA"
    text = str(text)
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2019": "'",   # right single quote
        "\u2018": "'",   # left single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "*",   # bullet
        "\u2026": "...", # ellipsis
        "\u00e2": "a",   # a with circumflex (often from encoding issues)
        "\u20ac": "EUR", # euro sign
        "\ufffd": "?",   # replacement character
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Final safety net: drop anything still outside Latin-1
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("ascii", errors="replace").decode("ascii")


# ── Color Palette ────────────────────────────────────────────
COLOR_HEADER_BG   = (30,  30,  60)    # dark navy
COLOR_HEADER_FG   = (255, 255, 255)
COLOR_SEC_TITLE   = (10,  80, 160)    # section banner blue
COLOR_POS         = (0,  120,  0)     # green text
COLOR_NEG         = (180,  0,   0)    # red text
COLOR_NEUTRAL     = (50,  50,  50)
COLOR_ROW_ALT     = (245, 245, 250)   # alternating row shading
COLOR_ROW_NORMAL  = (255, 255, 255)
COLOR_BORDER      = (180, 180, 200)


def pct_fill_color(pct, saturate=20.0):
    """
    Map a percentage change to a cell background color.
    0% -> white; positive -> green (darker as magnitude grows);
    negative -> red (darker as magnitude grows). Saturates at +-`saturate`%.
    """
    try:
        v = float(pct)
    except (TypeError, ValueError):
        return (255, 255, 255)
    frac = max(-1.0, min(1.0, v / saturate))
    intensity = abs(frac)
    if frac > 0:   # green: keep G high, drop R and B
        r = int(255 - 175 * intensity)
        g = int(255 - 35 * intensity)
        b = int(255 - 175 * intensity)
    elif frac < 0:  # red: keep R high, drop G and B
        r = int(255 - 35 * intensity)
        g = int(255 - 175 * intensity)
        b = int(255 - 175 * intensity)
    else:
        return (255, 255, 255)
    return (r, g, b)


# ── Page Geometry (A4 landscape) ─────────────────────────────
PAGE_W  = 297
PAGE_H  = 210
MARGIN  = 8
USABLE  = PAGE_W - 2 * MARGIN   # ~281 mm

# ── Fonts ────────────────────────────────────────────────────
FONT   = "Helvetica"
FONT_B = "Helvetica"


class ReportPDF(FPDF):
    def __init__(self, report_date):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.report_date = report_date
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(MARGIN, MARGIN, MARGIN)

    def header(self):
        self.set_font(FONT_B, "B", 7)
        self.set_text_color(*COLOR_NEUTRAL)
        self.cell(0, 4, _safe(f"Daily Stock Market Report - {self.report_date}"), align="L")
        self.ln(5)

    def footer(self):
        self.set_y(-10)
        self.set_font(FONT, "", 6)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4, f"Page {self.page_no()} | Data sourced from FRED, Yahoo Finance, StockAnalysis.com, Finviz", align="C")

    # ── Section Banner ────────────────────────────────────────
    def section_title(self, title):
        self.add_page()
        self.set_fill_color(*COLOR_SEC_TITLE)
        self.set_text_color(*COLOR_HEADER_FG)
        self.set_font(FONT_B, "B", 13)
        self.cell(USABLE, 9, _safe(title), align="C", fill=True)
        self.ln(11)

    # ── Table ─────────────────────────────────────────────────
    def table(self, headers, col_widths, rows, pct_cols=None, gradient_cols=None):
        """
        Render a table.
        headers:       list of column header strings
        col_widths:    list of mm widths (must sum to ~USABLE)
        rows:          list of lists (each inner list is a row of cell values)
        pct_cols:      set of column indices whose values are pct strings (text color-coded)
        gradient_cols: set of column indices whose cell BACKGROUND is shaded by magnitude
        """
        if pct_cols is None:
            pct_cols = set()
        if gradient_cols is None:
            gradient_cols = set()

        row_h = 5.2   # mm per row
        hdr_h = 6.0   # header row height

        def draw_header():
            self.set_fill_color(*COLOR_HEADER_BG)
            self.set_text_color(*COLOR_HEADER_FG)
            self.set_font(FONT_B, "B", 6.5)
            for i, (h, w) in enumerate(zip(headers, col_widths)):
                self.cell(w, hdr_h, _safe(h), border=1, align="C", fill=True)
            self.ln()

        BODY_SIZE = 6.5   # was 6 — small bump for readability
        BODY_STYLE = "B"  # Aryan wants all table body text bold

        draw_header()
        self.set_font(FONT, BODY_STYLE, BODY_SIZE)

        for row_idx, row in enumerate(rows):
            # Auto page break with repeated header
            if self.get_y() + row_h > PAGE_H - 14:
                self.add_page()
                draw_header()
                self.set_font(FONT, BODY_STYLE, BODY_SIZE)   # reset body font after header

            fill_color = COLOR_ROW_ALT if row_idx % 2 == 0 else COLOR_ROW_NORMAL

            for col_idx, (val, w) in enumerate(zip(row, col_widths)):
                val = _safe(val)

                # Choose fill: gradient overrides alternating shading
                if col_idx in gradient_cols and val not in ("NA", "-", ""):
                    self.set_fill_color(*pct_fill_color(
                        val.replace("%", "").replace("+", "").strip()))
                else:
                    self.set_fill_color(*fill_color)

                # Color-code percentage cells (text color).
                # Skip when the cell has a gradient background — colored text on a
                # colored fill is low-contrast; neutral bold text reads better there.
                if col_idx in pct_cols and col_idx not in gradient_cols and val != "NA" and val != "-":
                    val_clean = val.replace("%", "").replace("+", "").strip()
                    try:
                        num = float(val_clean)
                        if num > 0:
                            self.set_text_color(*COLOR_POS)
                        elif num < 0:
                            self.set_text_color(*COLOR_NEG)
                        else:
                            self.set_text_color(*COLOR_NEUTRAL)
                    except ValueError:
                        self.set_text_color(*COLOR_NEUTRAL)
                else:
                    self.set_text_color(*COLOR_NEUTRAL)

                # First column left-aligned, rest centered
                align = "L" if col_idx == 0 else "C"
                self.cell(w, row_h, val, border=1, align=align, fill=True)

            self.ln()

        self.ln(4)

    def no_data_notice(self):
        self.set_font(FONT, "I", 9)
        self.set_text_color(160, 100, 0)
        self.cell(USABLE, 8, "No data available for this section.", align="C")
        self.ln(10)


# ── Table Layout Helpers ──────────────────────────────────────

PCT_COLS_STD = {2, 3, 4, 5, 6, 7}   # the six percentage columns in 8-col std tables

def _std_pct_cols():
    return PCT_COLS_STD


# ── Section 1: FRED Macro ─────────────────────────────────────

S1_HEADERS = ["Metric [Units]", "Current", "5 Day %", "1 Month %", "3 Month %",
              "6 Month %", "1 Year %", "5 Year %"]
S1_WIDTHS  = [90, 26, 21, 21, 21, 21, 21, 21]
_diff = USABLE - sum(S1_WIDTHS)
S1_WIDTHS[0] += _diff


def _s1_rows(data):
    return [[r["metric"], r["current"], r["5d"], r["1mo"], r["3mo"],
             r["6mo"], r["1yr"], r["5yr"]] for r in data]


# ── Section 2: Commodities ────────────────────────────────────

S2_HEADERS = ["Commodity [Units]", "Current Price", "5 Day %", "1 Month %", "3 Month %",
              "6 Month %", "1 Year %", "5 Year %"]
S2_WIDTHS  = S1_WIDTHS[:]


def _s2_rows(data):
    return [[r["commodity"], r["current"], r["5d"], r["1mo"], r["3mo"],
             r["6mo"], r["1yr"], r["5yr"]] for r in data]


# ── Section 3: Industries ─────────────────────────────────────

S3_HEADERS = ["Industry", "Market Cap", "5 Day %", "1 Month %", "6 Month %", "1 Year %", "5 Year %"]
S3_WIDTHS  = [98, 32, 25, 25, 25, 25, 25]
_diff3 = USABLE - sum(S3_WIDTHS)
S3_WIDTHS[0] += _diff3


def _s3_rows(data):
    return [
        [r.get("industry","—"), r.get("market_cap","—"), r.get("5d","—"),
         r.get("1mo","—"), r.get("6mo","—"), r.get("1yr","—"), r.get("5yr","—")]
        for r in data
    ]


# ── Section 4: Companies of Interest ─────────────────────────

S4_HEADERS = ["Company", "Ticker", "Market Cap", "Price", "P/E Ratio", "Options", "5 Day %", "1 Month %"]
S4_WIDTHS  = [70, 20, 30, 22, 22, 18, 28, 28]
_diff4 = USABLE - sum(S4_WIDTHS)
S4_WIDTHS[0] += _diff4
S4_PCT_COLS = {6, 7}


def _s4_rows(data):
    return [
        [r.get("company","—"), r.get("ticker","—"), r.get("market_cap","—"),
         r.get("price","—"), r.get("pe","—"), r.get("has_options","—"),
         r.get("5d","—"), r.get("1mo","—")]
        for r in data
    ]


# ── Section 5: Earnings Calendar ─────────────────────────────

S5_HEADERS = ["Date", "Ticker", "Company", "Time", "EPS Est.", "EPS Actual", "Rev. Est.", "Rev. Actual", "Mkt Cap"]
S5_WIDTHS  = [22, 16, 68, 14, 20, 20, 24, 24, 25]
_diff5 = USABLE - sum(S5_WIDTHS)
S5_WIDTHS[2] += _diff5


def _s5_rows(data):
    return [
        [r.get("date","—"), r.get("symbol","—"), r.get("company","—"),
         r.get("time","—"), r.get("eps_est","—"), r.get("eps_actual","—"),
         r.get("revenue_est","—"), r.get("revenue_act","—"), r.get("market_cap","—")]
        for r in data
    ]


# ── Cover Page ────────────────────────────────────────────────

def _cover_page(pdf, report_date):
    pdf.add_page()
    pdf.set_y(60)
    pdf.set_font(FONT_B, "B", 26)
    pdf.set_text_color(*COLOR_SEC_TITLE)
    pdf.cell(USABLE, 14, "Daily Stock Market Report", align="C")
    pdf.ln(16)
    pdf.set_font(FONT, "", 14)
    pdf.set_text_color(*COLOR_NEUTRAL)
    pdf.cell(USABLE, 8, _safe(f"Generated: {report_date}"), align="C")
    pdf.ln(10)
    pdf.set_font(FONT, "I", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(USABLE, 6, "Recipient: 22mdrw@queensu.ca", align="C")
    pdf.ln(20)

    # Table of contents
    pdf.set_font(FONT_B, "B", 11)
    pdf.set_text_color(*COLOR_NEUTRAL)
    toc = [
        "Section 1 - Macro Data (FRED API)",
        "Section 2 - Base Materials & Commodities (Yahoo Finance)",
        "Section 3 - Industries (Finviz)",
        "Section 4 - Companies of Interest (Filtered by Price/Volume)",
        "Section 5 - Earnings Calendar (StockAnalysis / Finviz)",
    ]
    for entry in toc:
        pdf.cell(USABLE, 7, _safe(f"   {entry}"), align="L")
        pdf.ln(7)


# ── Strategy / Discipline Page ───────────────────────────────

def _strategy_page(pdf, mantra, mantra_defs, mistakes):
    pdf.add_page()
    pdf.set_font(FONT_B, "B", 18)
    pdf.set_text_color(*COLOR_SEC_TITLE)
    pdf.cell(USABLE, 12, "Trading Discipline", align="C")
    pdf.ln(16)

    # Mantra
    pdf.set_font(FONT_B, "B", 13)
    pdf.set_text_color(*COLOR_NEUTRAL)
    pdf.cell(USABLE, 8, "Mantra", align="L")
    pdf.ln(9)
    pdf.set_font(FONT_B, "B", 12)
    pdf.cell(USABLE, 8, _safe("  ->  ".join(mantra)), align="L")
    pdf.ln(12)

    # Definitions (bold label, wrapped description)
    for step, desc in mantra_defs:
        pdf.set_font(FONT_B, "B", 10)
        pdf.cell(28, 6, _safe(f"  {step}:"), align="L")
        pdf.set_font(FONT, "", 10)
        pdf.multi_cell(USABLE - 28, 6, _safe(desc), align="L")
    pdf.ln(8)

    # Past mistakes
    pdf.set_font(FONT_B, "B", 13)
    pdf.set_text_color(*COLOR_NEUTRAL)
    pdf.cell(USABLE, 8, "Past Mistakes", align="L")
    pdf.ln(9)
    pdf.set_font(FONT, "", 11)
    if mistakes:
        for m in mistakes:
            pdf.cell(USABLE, 7, _safe(f"  - {m}"), align="L")
            pdf.ln(7)
    else:
        pdf.cell(USABLE, 7, "  (none recorded)", align="L")
        pdf.ln(7)


# ── Main Build Function ───────────────────────────────────────

def build_pdf(
    macro_data,
    materials_data,
    industries_data,
    companies_data,
    earnings_data,
    output_path="stock_report.pdf",
):
    """
    Assemble all 5 sections into a single PDF and save to output_path.

    Args:
        macro_data:      list of dicts from section1_macro.fetch_macro_data()
        materials_data:  list of dicts from section2_materials.fetch_materials_data()
        industries_data: list of dicts from section3_industries.fetch_industries_data()
        companies_data:  list of dicts from section4_companies.fetch_companies_data()
        earnings_data:   list of dicts from section5_earnings.fetch_earnings_data()
        output_path:     file path for the output PDF

    Returns:
        output_path
    """
    report_date = datetime.now().strftime("%B %d, %Y — %I:%M %p ET")
    print(f"[PDF] Building report: {report_date}")

    pdf = ReportPDF(report_date)

    # ── Cover ─────────────────────────────────────────────────
    _cover_page(pdf, report_date)

    # ── Strategy / Discipline Page ────────────────────────────
    from config import MANTRA, MANTRA_DEFS, load_mistakes
    _strategy_page(pdf, MANTRA, MANTRA_DEFS, load_mistakes())

    # ── Section 1: FRED Macro ─────────────────────────────────
    pdf.section_title("Section 1 - Macro Data  (Source: FRED API)")
    if macro_data:
        pdf.table(S1_HEADERS, S1_WIDTHS, _s1_rows(macro_data), pct_cols=_std_pct_cols())
    else:
        pdf.no_data_notice()

    # ── Section 2: Base Materials ─────────────────────────────
    pdf.section_title("Section 2 - Base Materials & Commodities  (Source: Yahoo Finance)")
    if materials_data:
        pdf.table(S2_HEADERS, S2_WIDTHS, _s2_rows(materials_data), pct_cols=_std_pct_cols())
    else:
        pdf.no_data_notice()

    # ── Section 3: Industries ─────────────────────────────────
    pdf.section_title("Section 3 - Industries  (Source: Finviz)")
    if industries_data:
        pdf.table(S3_HEADERS, S3_WIDTHS, _s3_rows(industries_data), pct_cols=_std_pct_cols())
    else:
        pdf.no_data_notice()

    # ── Section 4: Companies of Interest ─────────────────────
    pdf.section_title("Section 4 - Companies of Interest  (>10% 5-day | >20% 1-month | Volume Spike)")
    if companies_data:
        pdf.table(S4_HEADERS, S4_WIDTHS, _s4_rows(companies_data), pct_cols=S4_PCT_COLS)
    else:
        pdf.no_data_notice()

    # ── Section 5: Earnings Calendar ─────────────────────────
    pdf.section_title("Section 5 - Earnings Calendar  (Source: StockAnalysis.com / Finviz)")
    if earnings_data:
        pdf.table(S5_HEADERS, S5_WIDTHS, _s5_rows(earnings_data))
    else:
        pdf.no_data_notice()

    pdf.output(output_path)
    print(f"[PDF] Saved to: {output_path}")
    return output_path
