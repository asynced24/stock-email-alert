from datetime import datetime
import pytz
from main import is_send_due

ET = pytz.timezone("America/New_York")
SPEC = [("wednesday", "20:00"), ("saturday", "08:00")]


def test_wed_8pm_is_due():
    t = ET.localize(datetime(2026, 6, 3, 20, 0))   # Wednesday
    assert is_send_due(t, SPEC)


def test_sat_8am_is_due():
    t = ET.localize(datetime(2026, 6, 6, 8, 0))     # Saturday
    assert is_send_due(t, SPEC)


def test_wed_noon_not_due():
    t = ET.localize(datetime(2026, 6, 3, 12, 0))
    assert not is_send_due(t, SPEC)


def test_thursday_8pm_not_due():
    t = ET.localize(datetime(2026, 6, 4, 20, 0))    # Thursday
    assert not is_send_due(t, SPEC)
