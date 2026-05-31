"""
Offline guard test for the generate_and_send pipeline.

Verifies that when the universe (and every section) is unavailable the
pipeline degrades gracefully: no exception is raised, a PDF is written,
and no email attempt is made.
"""
import main


def test_generate_handles_no_universe(monkeypatch, tmp_path):
    # ── Patch all module-level section functions ──────────────
    # These names must match the `from <module> import <name>` statements
    # at the top of main.py so that monkeypatching the main-module attribute
    # correctly intercepts the calls inside generate_and_send.
    monkeypatch.setattr(main, "fetch_macro_data",    lambda: [])
    monkeypatch.setattr(main, "fetch_materials_data", lambda: [])
    monkeypatch.setattr(main, "fetch_industries_data", lambda u, p: [])
    monkeypatch.setattr(
        main, "fetch_companies_data",
        lambda u, p, c: {"five_day": [], "one_month": [], "volume": []},
    )
    monkeypatch.setattr(main, "fetch_earnings_data",  lambda u: [])

    # ── Patch the function-local imports (universe + history) ─
    # universe.fetch_universe is imported inside generate_and_send, so we
    # patch it on the source module.  Returning None triggers the
    # "universe unavailable" branch and skips all screen sections.
    import universe
    monkeypatch.setattr(universe, "fetch_universe", lambda: None)

    # price_history.fetch_history should never be called when the universe
    # is None, but patch it defensively to avoid any network hit.
    import price_history
    import pandas as pd
    monkeypatch.setattr(price_history, "fetch_history", lambda tickers, **kw: pd.DataFrame())

    # ── Redirect output PDF to a temp path ───────────────────
    out = tmp_path / "r.pdf"
    monkeypatch.setattr(main, "REPORT_OUTPUT_PATH", str(out))

    # ── Run: must not raise, must not email ──────────────────
    main.generate_and_send(send_email=False)

    # ── Assert a non-empty PDF was written ───────────────────
    assert out.exists(), "PDF file was not created"
    assert out.stat().st_size > 0, "PDF file is empty"
