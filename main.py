"""
main.py — Daily Stock Market Report Orchestrator

Usage:
  python main.py               → Generate report NOW and email it
  python main.py --no-email    → Generate report NOW, skip email (just saves PDF)
  python main.py --schedule    → Run as a daemon, sends report daily at 8 PM ET

The report covers:
  Section 1: Macro Data          (FRED API)
  Section 2: Base Materials      (Yahoo Finance)
  Section 3: Industries          (StockAnalysis.com)
  Section 4: Companies of Interest (price/volume filter)
  Section 5: Earnings Calendar   (StockAnalysis.com)
"""
import argparse
import time
import traceback
from datetime import datetime

import pytz

from config import REPORT_OUTPUT_PATH, REPORT_TIMEZONE, REPORT_HOUR

from section1_macro      import fetch_macro_data
from section2_materials  import fetch_materials_data
from section3_industries import fetch_industries_data
from section4_companies  import fetch_companies_data
from section5_earnings   import fetch_earnings_data
from pdf_builder         import build_pdf
from email_sender        import send_report, send_alert


def _make_options_checker(pace=0.25, retries=3):
    """
    Return a sym->bool checker for option availability via yfinance.

    The options endpoint rate-limits when called in a burst right after the bulk
    history download (this previously emptied Section 6). We pace each call and
    retry on an empty/failed response so a transient rate-limit doesn't wrongly
    exclude an optionable stock.
    """
    import yfinance as yf
    def has_options(sym):
        for _ in range(retries):
            time.sleep(pace)
            try:
                if yf.Ticker(sym).options:
                    return True
            except Exception:
                pass
        return False
    return has_options


def _inject_buffett(macro_data, universe_df):
    """
    Compute the Buffett Indicator (total US market cap / GDP) and set its row.

    Dual-class share lines (e.g. GOOG + GOOGL, BRK-A + BRK-B) each carry the full
    company market cap, so we de-duplicate by company name before summing to avoid
    double-counting. It remains approximate (foreign ADRs add some cap not tied to
    US GDP), hence the "(approx.)" label on the row.
    """
    try:
        if universe_df is None or universe_df.empty:
            return
        import pandas as pd
        from fredapi import Fred
        from config import FRED_API_KEY
        deduped = universe_df.drop_duplicates(subset="name")
        total_cap = float(pd.to_numeric(deduped["market_cap"], errors="coerce").sum())
        gdp_billions = float(Fred(api_key=FRED_API_KEY).get_series("GDP").dropna().iloc[-1])
        buffett = total_cap / (gdp_billions * 1e9) * 100.0
        for row in macro_data:
            if str(row.get("metric", "")).startswith("Buffett Indicator"):
                row["current"] = f"{buffett:.1f}%"
                break
        print(f"[Macro] Buffett Indicator computed: {buffett:.1f}% "
              f"({len(universe_df) - len(deduped)} dual-class lines deduped)")
    except Exception as e:
        print(f"  [WARN] Buffett indicator computation failed: {e}")


def generate_and_send(send_email: bool = True):
    """
    Full pipeline: build shared data layer -> fetch all sections -> build PDF -> (optionally) email.
    Each step is guarded so one failure doesn't abort the report.
    """
    start = datetime.now()
    print("=" * 70)
    print(f"  Stock Market Report - {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    from universe import fetch_universe, filter_by_market_cap
    from price_history import fetch_history
    import screens
    from config import MIN_CAP_SCREENS

    # ── Shared data layer ────────────────────────────────────
    try:
        universe_df = fetch_universe()
    except Exception:
        print("[Universe] CRITICAL FAILURE:")
        traceback.print_exc()
        universe_df = None

    if universe_df is None or universe_df.empty:
        from universe import sp500_fallback
        universe_df = sp500_fallback()
        if universe_df is not None and not universe_df.empty:
            send_alert("Universe scrape failed - using S&P 500 fallback",
                       "The StockAnalysis screener was unavailable. The report was built from "
                       "the S&P 500 constituent list, so screens are limited to large caps and "
                       "P/E and a few fields show NA. Check the source when convenient.")
        else:
            send_alert("Universe unavailable",
                       "Both the StockAnalysis screener and the S&P 500 fallback failed. "
                       "Sections 3, 4, 6, 7, 8 and 9 are empty in this run.")

    if universe_df is None or universe_df.empty:
        print("[ALERT] Universe unavailable — full-market sections (3,4,6,7,8,9) will be empty this run.")
        panel = None
    else:
        try:
            screen_syms = list(filter_by_market_cap(universe_df, MIN_CAP_SCREENS)["symbol"])
            panel = fetch_history(screen_syms)
        except Exception:
            print("[History] CRITICAL FAILURE:")
            traceback.print_exc()
            panel = None

    have_market = universe_df is not None and not universe_df.empty and panel is not None and not getattr(panel, "empty", True)

    # ── Section 1: FRED Macro (+ indices, valuation) ─────────
    try:
        macro_data = fetch_macro_data()
        _inject_buffett(macro_data, universe_df)
    except Exception:
        print("[Section 1] CRITICAL FAILURE:")
        traceback.print_exc()
        macro_data = []

    # ── Section 2: Base Materials ────────────────────────────
    try:
        materials_data = fetch_materials_data()
    except Exception:
        print("[Section 2] CRITICAL FAILURE:")
        traceback.print_exc()
        materials_data = []

    # ── Section 3: Industries (universe member-averaged) ─────
    try:
        industries_data = fetch_industries_data(universe_df, panel)
        if not industries_data:
            print("[ALERT] Section 3 industries empty — check the universe source.")
    except Exception:
        print("[Section 3] CRITICAL FAILURE:")
        traceback.print_exc()
        industries_data = []

    # ── Section 4: Companies of Interest (3 tables) ──────────
    try:
        companies_data = fetch_companies_data(universe_df, panel, MIN_CAP_SCREENS)
    except Exception:
        print("[Section 4] CRITICAL FAILURE:")
        traceback.print_exc()
        companies_data = {"five_day": [], "one_month": [], "volume": []}

    # ── Section 5: Earnings Calendar (>=$5B) ─────────────────
    try:
        earnings_data = fetch_earnings_data(universe_df)
    except Exception:
        print("[Section 5] CRITICAL FAILURE:")
        traceback.print_exc()
        earnings_data = []

    # ── Sections 6-9: Screens ────────────────────────────────
    from config import MIN_CAP_NEAR_MA
    section6 = section7 = section8 = []
    section9_50 = section9_200 = []
    if have_market:
        try:
            section6 = screens.long_term_pullback(universe_df, panel, MIN_CAP_SCREENS,
                                                  has_options=_make_options_checker())
            print(f"[Section 6] {len(section6)} long-term pullback (optionable) candidates.")
        except Exception:
            print("[Section 6] FAILURE:"); traceback.print_exc()
        try:
            section7 = screens.momentum_pullback(universe_df, panel, MIN_CAP_SCREENS)
        except Exception:
            print("[Section 7] FAILURE:"); traceback.print_exc()
        try:
            section8 = screens.reversal_bounce(universe_df, panel, MIN_CAP_SCREENS)
        except Exception:
            print("[Section 8] FAILURE:"); traceback.print_exc()
        try:
            section9_50  = screens.near_ma(universe_df, panel, MIN_CAP_NEAR_MA, window=50)
            section9_200 = screens.near_ma(universe_df, panel, MIN_CAP_NEAR_MA, window=200)
            print(f"[Section 9] {len(section9_50)} near 50d, {len(section9_200)} near 200d.")
        except Exception:
            print("[Section 9] FAILURE:"); traceback.print_exc()

    # ── Build PDF ────────────────────────────────────────────
    try:
        pdf_path = build_pdf(
            macro_data=macro_data,
            materials_data=materials_data,
            industries_data=industries_data,
            companies_data=companies_data,
            earnings_data=earnings_data,
            section6_data=section6,
            section7_data=section7,
            section8_data=section8,
            section9_50_data=section9_50,
            section9_200_data=section9_200,
            output_path=REPORT_OUTPUT_PATH,
        )
    except Exception:
        print("[PDF] CRITICAL FAILURE - PDF could not be built:")
        traceback.print_exc()
        return

    # ── Send Email ────────────────────────────────────────────
    if send_email:
        try:
            sent = send_report(pdf_path)
            if not sent:
                send_alert("Report email did not send",
                           f"The report was built ({pdf_path}) but the email send returned "
                           f"failure. Check email credentials / recipient configuration.")
        except Exception:
            print("[Email] CRITICAL FAILURE:")
            traceback.print_exc()
            send_alert("Report email crashed",
                       "An exception was raised while sending the report email. "
                       "The PDF was generated but delivery failed.")
    else:
        print(f"[Email] Skipped (--no-email flag). PDF saved at: {pdf_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print("=" * 70)
    print(f"  Report complete in {elapsed:.1f}s -> {pdf_path}")
    print("=" * 70)


def scheduled_job():
    """Wrapper kept for reference — generates and sends the report."""
    generate_and_send(send_email=True)


def is_send_due(now_et, schedule_spec):
    """True if now_et (tz-aware ET) matches any (weekday_name, 'HH:MM') slot to the minute."""
    day = now_et.strftime("%A").lower()
    hhmm = now_et.strftime("%H:%M")
    return any(day == d and hhmm == t for d, t in schedule_spec)


def run_scheduler():
    """Poll once a minute; send when an ET schedule slot matches. Guards against double-send."""
    from config import SEND_SCHEDULE
    tz = pytz.timezone(REPORT_TIMEZONE)
    print(f"[Scheduler] Active. Slots (ET): {SEND_SCHEDULE}. Ctrl+C to stop.")
    last_fired = None
    while True:
        now_et = datetime.now(tz)
        stamp = now_et.strftime("%Y-%m-%d %H:%M")
        if is_send_due(now_et, SEND_SCHEDULE) and stamp != last_fired:
            last_fired = stamp
            # An unhandled error in one run must NOT kill the daemon (which would
            # silently miss all future deliveries). Catch, alert, and keep polling.
            try:
                generate_and_send(send_email=True)
            except Exception:
                print("[Scheduler] UNHANDLED EXCEPTION in generate_and_send:")
                traceback.print_exc()
                try:
                    send_alert("Scheduled run crashed",
                               "generate_and_send raised an unhandled exception; "
                               "the scheduler is still running and will retry next slot.")
                except Exception:
                    pass
        time.sleep(15)


def main():
    parser = argparse.ArgumentParser(
        description="Daily Stock Market PDF Report Generator"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a daemon and send report daily at 8 PM ET.",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        dest="no_email",
        help="Generate the report but skip sending the email (just saves PDF).",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduler()
    else:
        generate_and_send(send_email=not args.no_email)


if __name__ == "__main__":
    main()
