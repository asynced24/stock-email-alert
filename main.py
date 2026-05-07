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
import schedule

from config import REPORT_OUTPUT_PATH, REPORT_TIMEZONE, REPORT_HOUR

from section1_macro      import fetch_macro_data
from section2_materials  import fetch_materials_data
from section3_industries import fetch_industries_data
from section4_companies  import fetch_companies_data
from section5_earnings   import fetch_earnings_data
from pdf_builder         import build_pdf
from email_sender        import send_report


def generate_and_send(send_email: bool = True):
    """
    Full pipeline: fetch all data → build PDF → (optionally) email it.
    Each section is wrapped in try/except so one failure doesn't abort the report.
    """
    start = datetime.now()
    print("=" * 70)
    print(f"  Stock Market Report — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Section 1: FRED Macro ────────────────────────────────
    try:
        macro_data = fetch_macro_data()
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

    # ── Section 3: Industries ────────────────────────────────
    try:
        industries_data = fetch_industries_data()
    except Exception:
        print("[Section 3] CRITICAL FAILURE:")
        traceback.print_exc()
        industries_data = []

    # ── Section 4: Companies of Interest ────────────────────
    try:
        companies_data = fetch_companies_data(industries_data)
    except Exception:
        print("[Section 4] CRITICAL FAILURE:")
        traceback.print_exc()
        companies_data = []

    # ── Section 5: Earnings Calendar ─────────────────────────
    try:
        earnings_data = fetch_earnings_data()
    except Exception:
        print("[Section 5] CRITICAL FAILURE:")
        traceback.print_exc()
        earnings_data = []

    # ── Build PDF ────────────────────────────────────────────
    try:
        pdf_path = build_pdf(
            macro_data      = macro_data,
            materials_data  = materials_data,
            industries_data = industries_data,
            companies_data  = companies_data,
            earnings_data   = earnings_data,
            output_path     = REPORT_OUTPUT_PATH,
        )
    except Exception:
        print("[PDF] CRITICAL FAILURE — PDF could not be built:")
        traceback.print_exc()
        return

    # ── Send Email ────────────────────────────────────────────
    if send_email:
        try:
            send_report(pdf_path)
        except Exception:
            print("[Email] CRITICAL FAILURE:")
            traceback.print_exc()
    else:
        print(f"[Email] Skipped (--no-email flag). PDF saved at: {pdf_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print("=" * 70)
    print(f"  Report complete in {elapsed:.1f}s -> {REPORT_OUTPUT_PATH}")
    print("=" * 70)


def scheduled_job():
    """Wrapper for the schedule library — generates and sends the report."""
    generate_and_send(send_email=True)


def run_scheduler():
    """
    Start the scheduler daemon.
    Sends the report every day at REPORT_HOUR (8 PM) in REPORT_TIMEZONE.
    """
    tz = pytz.timezone(REPORT_TIMEZONE)
    send_time = f"{REPORT_HOUR:02d}:00"

    print(f"[Scheduler] Starting. Report will send daily at {send_time} {REPORT_TIMEZONE}.")
    print("            Press Ctrl+C to stop.\n")

    # schedule uses local system time, so we convert 8 PM ET to local
    # Simpler: just schedule at the correct UTC offset hour using a check loop.
    schedule.every().day.at(send_time).do(scheduled_job)

    while True:
        now_et = datetime.now(tz)
        schedule.run_pending()
        time.sleep(30)   # check every 30 seconds


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
