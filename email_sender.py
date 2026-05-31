"""
Email Sender: sends the daily PDF report via Gmail SMTP.
Requires EMAIL_SENDER and EMAIL_APP_PASSWORD to be set in config.py.

How to set up Gmail App Password (free):
  1. Enable 2-Factor Authentication on your Google account
  2. Go to: myaccount.google.com/apppasswords
  3. Create a new App Password (select "Mail" + your device)
  4. Paste the 16-character password into config.py → EMAIL_APP_PASSWORD
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import datetime

from config import EMAIL_SENDER, EMAIL_APP_PASSWORD, EMAIL_RECIPIENT


def _recipient_list():
    """EMAIL_RECIPIENT may be a comma-separated list; return clean addresses."""
    return [a.strip() for a in str(EMAIL_RECIPIENT or "").split(",") if a.strip()]


def send_report(pdf_path: str) -> bool:
    """
    Send the PDF report by email.

    Args:
        pdf_path: path to the generated PDF file

    Returns:
        True if sent successfully, False otherwise.
    """
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
        print("[Email] Skipping email — EMAIL_SENDER or EMAIL_APP_PASSWORD not configured in config.py.")
        return False

    if not EMAIL_RECIPIENT:
        print("[Email] Skipping email — EMAIL_RECIPIENT not configured in .env.")
        return False

    if not os.path.exists(pdf_path):
        print(f"[Email] PDF not found at {pdf_path}. Cannot send.")
        return False

    report_date = datetime.now().strftime("%B %d, %Y")
    subject     = f"Daily Stock Market Report — {report_date}"

    body = f"""\
Hi,

Please find attached your daily stock market report for {report_date}.

This report contains:
  • Section 1 — Macro Data (FRED API)
  • Section 2 — Base Materials & Commodities (Yahoo Finance)
  • Section 3 — Industries (StockAnalysis.com)
  • Section 4 — Companies of Interest (price/volume filtered)
  • Section 5 — Earnings Calendar (StockAnalysis.com)

This email was sent automatically at 8:00 PM Eastern Time.

Regards,
Your Automated Market Report
"""

    recipients = _recipient_list()
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach the PDF
        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(pdf_path)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())

        print(f"[Email] Report sent to {', '.join(recipients)}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[Email] Authentication failed. Check EMAIL_SENDER and EMAIL_APP_PASSWORD in config.py.")
        print("        Make sure you are using a Gmail App Password, not your regular password.")
        return False
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


def send_alert(subject: str, body: str) -> bool:
    """
    Send a short plain-text alert email (no attachment) to EMAIL_RECIPIENT.
    Used to surface data-source failures during scheduled runs, where stdout
    is not watched. Best-effort: returns False (and prints) if not configured.
    """
    recipients = _recipient_list()
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not recipients:
        print(f"[Alert] (email not configured) {subject}: {body}")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = f"[Stock Report ALERT] {subject}"
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        print(f"[Alert] Sent: {subject}")
        return True
    except Exception as e:
        print(f"[Alert] Failed to send alert ({subject}): {e}")
        return False
