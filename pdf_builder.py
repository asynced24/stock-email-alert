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
COLOR_HEADER_BG   = (16,  24,  39)    # dark navy (matches buddy table headers)
COLOR_HEADER_FG   = (255, 255, 255)
COLOR_SEC_TITLE   = (10,  80, 160)    # section banner blue
COLOR_POS         = (0,  120,  0)     # green text
COLOR_NEG         = (180,  0,   0)    # red text
COLOR_NEUTRAL     = (40,  40,  40)    # body text (matches buddy)
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

    def _lerp(a, b, t):
        return int(round(a + (b - a) * t))

    if frac > 0:     # green-500 (34,197,94) -> green-900 (20,83,45)
        return (_lerp(34, 20, intensity), _lerp(197, 83, intensity), _lerp(94, 45, intensity))
    elif frac < 0:   # red-500 (239,68,68) -> red-900 (127,29,29)
        return (_lerp(239, 127, intensity), _lerp(68, 29, intensity), _lerp(68, 29, intensity))
    return (255, 255, 255)


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

                # Text color.
                if col_idx in gradient_cols and val not in ("NA", "-", ""):
                    # White reads on the saturated green/red fills; a ~0% cell has a
                    # near-white fill, so use dark text there instead of invisible white.
                    _fill = pct_fill_color(val.replace("%", "").replace("+", "").strip())
                    self.set_text_color(*(COLOR_NEUTRAL if _fill == (255, 255, 255)
                                          else COLOR_HEADER_FG))
                elif col_idx in pct_cols and val != "NA" and val != "-":
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

S3_HEADERS = ["Industry", "P/E", "5 Day %", "1 Month %", "3 Month %",
              "6 Month %", "1 Year %", "3 Year %", "5 Year %"]
S3_WIDTHS  = [89, 20, 24, 24, 24, 24, 24, 24, 24]
_diff3 = USABLE - sum(S3_WIDTHS)
S3_WIDTHS[0] += _diff3
S3_GRADIENT_COLS = {2, 3, 4, 5, 6, 7, 8}   # the 7 period columns


def _s3_rows(data):
    return [[r.get("industry", "-"), r.get("pe", "-"), r.get("5d", "-"),
             r.get("1mo", "-"), r.get("3mo", "-"), r.get("6mo", "-"),
             r.get("1yr", "-"), r.get("3yr", "-"), r.get("5yr", "-")]
            for r in data]


# ── Section 4: Companies of Interest (three separate tables) ──

# 4a. >10% 5-Day Movers
S4_MOVERS5_HEADERS  = ["Company", "Ticker", "Price", "5 Day %", "1 Month %", "3 Month %"]
S4_MOVERS5_WIDTHS   = [125, 26, 28, 34, 34, 34]
S4_MOVERS5_WIDTHS[0] += USABLE - sum(S4_MOVERS5_WIDTHS)
S4_MOVERS5_GRADIENT = {3, 4, 5}

# 4b. >20% 1-Month Movers (adds 6-month + 1-year context)
S4_MOVERS1_HEADERS  = ["Company", "Ticker", "Price", "5 Day %", "1 Month %",
                       "3 Month %", "6 Month %", "1 Year %"]
S4_MOVERS1_WIDTHS   = [95, 22, 24, 28, 28, 28, 28, 28]
S4_MOVERS1_WIDTHS[0] += USABLE - sum(S4_MOVERS1_WIDTHS)
S4_MOVERS1_GRADIENT = {3, 4, 5, 6, 7}

# 4c. Volume Spikes
S4_VOL_HEADERS  = ["Company", "Ticker", "Price", "5 Day %", "Avg Vol (2wk)",
                   "Top Spike (3d)", "Peak Vol (3d)", "Peak Date"]
S4_VOL_WIDTHS   = [86, 22, 24, 28, 32, 30, 30, 29]   # sums to 281 (= USABLE)
S4_VOL_WIDTHS[0] += USABLE - sum(S4_VOL_WIDTHS)
S4_VOL_GRADIENT = {3}   # only the 5-day % is a gradient column


def _s4_movers5_rows(data):
    return [[r.get("company", "-"), r.get("symbol", "-"), r.get("price", "-"),
             r.get("5d", "-"), r.get("1mo", "-"), r.get("3mo", "-")] for r in data]


def _s4_movers1_rows(data):
    return [[r.get("company", "-"), r.get("symbol", "-"), r.get("price", "-"),
             r.get("5d", "-"), r.get("1mo", "-"), r.get("3mo", "-"),
             r.get("6mo", "-"), r.get("1yr", "-")] for r in data]


def _s4_vol_rows(data):
    return [[r.get("company", "-"), r.get("symbol", "-"), r.get("price", "-"),
             r.get("5d", "-"), r.get("avg2wk_disp", "-"), r.get("spike_disp", "-"),
             r.get("peakvol_disp", "-"), r.get("peak_date", "-")] for r in data]


# ── Section 5: Earnings Calendar ─────────────────────────────

S5_HEADERS = ["Date", "Ticker", "Company", "Time", "Mkt Cap"]
S5_WIDTHS  = [40, 26, 150, 35, 30]
S5_WIDTHS[2] += USABLE - sum(S5_WIDTHS)   # any residual absorbed by the Company column


def _s5_rows(data):
    return [[r.get("date", "-"), r.get("symbol", "-"), r.get("company", "-"),
             r.get("time", "-"), r.get("market_cap", "-")] for r in data]


# ── Sections 6-9: Screen Tables ───────────────────────────────

SCREEN_HEADERS = ["Company", "Ticker", "Price", "5 Day %", "1 Month %", "3 Month %", "1 Year %"]
SCREEN_WIDTHS  = [110, 24, 26, 30, 30, 30, 31]
_diffS = USABLE - sum(SCREEN_WIDTHS)
SCREEN_WIDTHS[0] += _diffS
SCREEN_GRADIENT_COLS = {3, 4, 5, 6}


def _screen_rows(data):
    return [[r.get("company", "-"), r.get("symbol", "-"), r.get("price", "-"),
             r.get("5d", "-"), r.get("1mo", "-"), r.get("3mo", "-"),
             r.get("1yr", "-")] for r in data]


def _screen_section(pdf, title, rows):
    pdf.section_title(title)
    if rows:
        pdf.table(SCREEN_HEADERS, SCREEN_WIDTHS, _screen_rows(rows),
                  gradient_cols=SCREEN_GRADIENT_COLS)
    else:
        pdf.no_data_notice()


def _explainer(pdf, text):
    """Render a short italic explanation line under a section banner."""
    pdf.set_font(FONT, "I", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(USABLE, 4.5, _safe(text), align="L")
    pdf.ln(2)


# ── Section 9: Near Moving Average (50-day and 200-day tables) ─

def _s9_headers(window):
    return ["Company", "Ticker", "Price", f"{window}-Day MA",
            "5 Day %", "1 Month %", "3 Month %", "6 Month %", "1 Year %", "5 Year %"]

S9_WIDTHS = [78, 20, 22, 26, 22, 22, 22, 22, 22, 23]
S9_WIDTHS[0] += USABLE - sum(S9_WIDTHS)
S9_GRADIENT = {4, 5, 6, 7, 8, 9}   # the six percentage columns


def _s9_rows(data):
    return [[r.get("company", "-"), r.get("symbol", "-"), r.get("price", "-"),
             r.get("ma", "-"), r.get("5d", "-"), r.get("1mo", "-"),
             r.get("3mo", "-"), r.get("6mo", "-"), r.get("1yr", "-"),
             r.get("5yr", "-")] for r in data]


def _near_ma_section(pdf, title, window, rows):
    pdf.section_title(title)
    if rows:
        pdf.table(_s9_headers(window), S9_WIDTHS, _s9_rows(rows),
                  gradient_cols=S9_GRADIENT)
    else:
        pdf.no_data_notice()


# ── Cover Page ────────────────────────────────────────────────

def _cover_page(pdf, report_date, mantra, mantra_defs, mistakes):
    """
    First page: replicates the exact above-the-TOC structure of the reference
    report (centered title, Generated line, Recipients line, full-width blue
    mantra banner, inline step definitions, Past-Mistakes line), then our own TOC.
    """
    pdf.add_page()
    # Title (centered, blue)
    pdf.set_y(18)
    pdf.set_font(FONT_B, "B", 26)
    pdf.set_text_color(*COLOR_SEC_TITLE)
    pdf.cell(USABLE, 13, "Stock Market Report", align="C")
    pdf.ln(15)
    # Generated
    pdf.set_font(FONT, "", 12)
    pdf.set_text_color(*COLOR_NEUTRAL)
    pdf.cell(USABLE, 6, _safe(f"Generated: {report_date}"), align="C")
    pdf.ln(7)
    # Recipients (all configured addresses)
    try:
        from config import EMAIL_RECIPIENT
        recips = "  |  ".join(a.strip() for a in str(EMAIL_RECIPIENT or "").split(",") if a.strip())
    except Exception:
        recips = "(not configured)"
    pdf.set_font(FONT, "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(USABLE, 5, _safe(f"Recipients: {recips}"), align="C")
    pdf.ln(9)
    # Mantra banner (full-width blue bar, white text)
    pdf.set_fill_color(*COLOR_SEC_TITLE)
    pdf.set_text_color(*COLOR_HEADER_FG)
    pdf.set_font(FONT_B, "B", 11)
    pdf.cell(USABLE, 8, _safe("  Sound Options Trading Mantra: " + "  -  ".join(mantra)),
             align="L", fill=True)
    pdf.ln(11)
    # Mantra definitions (bold blue label + gray description, inline)
    for step, desc in mantra_defs:
        y = pdf.get_y()
        pdf.set_font(FONT_B, "B", 8)
        pdf.set_text_color(10, 60, 120)
        pdf.cell(26, 5, _safe(f"  {step.upper()}:"), align="L")
        pdf.set_font(FONT, "", 8)
        pdf.set_text_color(*COLOR_NEUTRAL)
        pdf.set_xy(pdf.l_margin + 26, y)
        pdf.multi_cell(USABLE - 26, 5, _safe(desc), align="L")
    pdf.ln(3)
    # Past mistakes (bold, dark red)
    pdf.set_font(FONT_B, "B", 9)
    pdf.set_text_color(160, 30, 30)
    _mline = "  |  ".join(mistakes) if mistakes else "(none recorded)"
    pdf.cell(USABLE, 6, _safe("  Past Mistakes (learn from these): " + _mline), align="L")
    pdf.ln(10)

    # Table of contents
    pdf.set_font(FONT_B, "B", 10)
    pdf.set_text_color(*COLOR_NEUTRAL)
    toc = [
        "Section 1 - Macro Data: Market Indices + FRED Economic Series",
        "Section 2 - Base Materials & Commodities  (Yahoo Finance)",
        "Section 3 - Industries: PE Ratios & Performance  (StockAnalysis.com)",
        "Section 4A - Companies of Interest: >10% 5-Day Movers",
        "Section 4B - Companies of Interest: >20% 1-Month Movers",
        "Section 4C - Companies of Interest: Volume Spikes (>=$2B)",
        "Section 5 - Earnings Calendar: Next 5 Days, Companies >$5B",
        "Section 6 - Long-Term Winners Pulling Back (optionable)",
        "Section 7 - Uptrend Pullback",
        "Section 8 - Downtrend Bounce (down >20% YTD)",
        "Section 9A - Near 50-Day MA   |   Section 9B - Near 200-Day MA",
    ]
    for entry in toc:
        pdf.cell(USABLE, 6, _safe(f"   {entry}"), align="L")
        pdf.ln(6)


# ── Main Build Function ───────────────────────────────────────

def build_pdf(
    macro_data,
    materials_data,
    industries_data,
    companies_data,
    earnings_data,
    section6_data=None,
    section7_data=None,
    section8_data=None,
    section9_50_data=None,
    section9_200_data=None,
    output_path="stock_report.pdf",
):
    """
    Assemble all sections into a single PDF and save to output_path.

    Args:
        macro_data:      list of dicts from section1_macro.fetch_macro_data()
        materials_data:  list of dicts from section2_materials.fetch_materials_data()
        industries_data: list of dicts from section3_industries.fetch_industries_data()
        companies_data:  dict with keys five_day / one_month / volume
        earnings_data:   list of dicts from section5_earnings.fetch_earnings_data()
        section6_data:   list of row dicts from screens.long_term_pullback()
        section7_data:   list of row dicts from screens.momentum_pullback()
        section8_data:   list of row dicts from screens.reversal_bounce()
        section9_data:   list of row dicts from screens.near_ma()
        output_path:     file path for the output PDF

    Returns:
        output_path
    """
    report_date = datetime.now().strftime("%B %d, %Y - %I:%M %p ET")
    print(f"[PDF] Building report: {report_date}")

    pdf = ReportPDF(report_date)

    # ── Cover + Strategy combined onto the first page (reference layout) ──
    from config import MANTRA, MANTRA_DEFS, load_mistakes
    _cover_page(pdf, report_date, MANTRA, MANTRA_DEFS, load_mistakes())

    # ── Section 1: FRED Macro ─────────────────────────────────
    pdf.section_title("Section 1 - Macro Data  (Source: FRED API)")
    if macro_data:
        pdf.table(S1_HEADERS, S1_WIDTHS, _s1_rows(macro_data), gradient_cols=_std_pct_cols())
    else:
        pdf.no_data_notice()

    # ── Section 2: Base Materials ─────────────────────────────
    pdf.section_title("Section 2 - Base Materials & Commodities  (Source: Yahoo Finance)")
    if materials_data:
        pdf.table(S2_HEADERS, S2_WIDTHS, _s2_rows(materials_data), pct_cols=_std_pct_cols())
    else:
        pdf.no_data_notice()

    # ── Section 3: Industries ─────────────────────────────────
    pdf.section_title("Section 3 - Industries  (Source: StockAnalysis universe (member-averaged))")
    if industries_data:
        pdf.table(S3_HEADERS, S3_WIDTHS, _s3_rows(industries_data),
                  gradient_cols=S3_GRADIENT_COLS)
    else:
        pdf.no_data_notice()

    # ── Section 4: Companies of Interest (three blue-bannered tables) ─
    buckets = companies_data or {}

    # 4a. >10% 5-Day Movers
    pdf.section_title("Section 4 - Companies of Interest:  >10% 5-Day Movers")
    five = buckets.get("five_day", [])
    if five:
        pdf.table(S4_MOVERS5_HEADERS, S4_MOVERS5_WIDTHS, _s4_movers5_rows(five),
                  gradient_cols=S4_MOVERS5_GRADIENT)
    else:
        pdf.no_data_notice()

    # 4b. >20% 1-Month Movers
    pdf.section_title("Section 4 - Companies of Interest:  >20% 1-Month Movers")
    month = buckets.get("one_month", [])
    if month:
        pdf.table(S4_MOVERS1_HEADERS, S4_MOVERS1_WIDTHS, _s4_movers1_rows(month),
                  gradient_cols=S4_MOVERS1_GRADIENT)
    else:
        pdf.no_data_notice()

    # 4c. Volume Spikes
    pdf.section_title("Section 4 - Companies of Interest:  Volume Spikes")
    _explainer(pdf,
        "Volume spike = the single highest daily trading volume over the last 3 trading days "
        "is at least 2x the average daily volume of the prior 2 weeks (10 trading days). "
        "Only companies with a market cap of $2B or more are included. "
        "'Avg Vol (2wk)' is that 2-week average; 'Top Spike (3d)' is the peak/average ratio; "
        "'Peak Vol (3d)' is the highest single-day volume and 'Peak Date' is the day it occurred.")
    vol = buckets.get("volume", [])
    if vol:
        pdf.table(S4_VOL_HEADERS, S4_VOL_WIDTHS, _s4_vol_rows(vol),
                  gradient_cols=S4_VOL_GRADIENT)
    else:
        pdf.no_data_notice()

    # ── Section 5: Earnings Calendar ─────────────────────────
    pdf.section_title("Section 5 - Earnings Calendar  (Source: StockAnalysis.com / Finviz)")
    if earnings_data:
        pdf.table(S5_HEADERS, S5_WIDTHS, _s5_rows(earnings_data))
    else:
        pdf.no_data_notice()

    # -- Section 6: Long-Term Winners Pulling Back
    _screen_section(pdf,
                    "Section 6 - Long-Term Winners Pulling Back  (>0% 5yr, >20% 1yr, <-10% 3mo, optionable)",
                    section6_data or [])

    # -- Section 7: Uptrend Pullback
    _screen_section(pdf,
                    "Section 7 - Uptrend Pullback  (up >50% 1yr, down >10% over 5d/1mo/3mo)",
                    section7_data or [])

    # -- Section 8: Downtrend Bounce
    _screen_section(pdf,
                    "Section 8 - Downtrend Bounce  (down >20% 1yr, up >10% over 5d/1mo)",
                    section8_data or [])

    # -- Section 9: Near Moving Average (two tables: 50-day, then 200-day)
    _near_ma_section(pdf,
                     "Section 9A - Near 50 day MA, >5bn market cap, >25% last 5 years",
                     50, section9_50_data or [])
    _near_ma_section(pdf,
                     "Section 9B - Near 200 day MA, >5bn market cap, >25% last 5 years",
                     200, section9_200_data or [])

    return _write_pdf(pdf, output_path)


def _write_pdf(pdf, output_path):
    """
    Write the PDF robustly. The target may be locked (e.g. open in a viewer on
    Windows/OneDrive); rendering to a temp file and replacing avoids a half-written
    file, and a timestamped fallback guarantees the run still produces an attachable
    PDF instead of failing the whole report (and email).
    """
    import os
    tmp = output_path + ".tmp"
    pdf.output(tmp)   # render once to a scratch file
    try:
        os.replace(tmp, output_path)   # atomic on the same volume
        print(f"[PDF] Saved to: {output_path}")
        return output_path
    except PermissionError:
        base, ext = os.path.splitext(output_path)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = f"{base}_{stamp}{ext}"
        os.replace(tmp, fallback)
        print(f"[PDF] '{output_path}' is locked (open in a viewer?). Saved to: {fallback}")
        return fallback
