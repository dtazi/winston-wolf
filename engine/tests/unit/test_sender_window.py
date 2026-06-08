from datetime import datetime
from zoneinfo import ZoneInfo

from ww_engine import sender

ET = ZoneInfo("America/New_York")


def test_inside_window_tue_to_thu_midday():  # happy — 004: recipient-local 10-14
    assert sender.in_send_window(datetime(2026, 5, 19, 10, 0, tzinfo=ET))  # Tue 10am
    assert sender.in_send_window(datetime(2026, 5, 19, 13, 0, tzinfo=ET))  # Tue 1pm


def test_outside_window_edges():  # error/edge
    assert not sender.in_send_window(datetime(2026, 5, 18, 10, 0, tzinfo=ET))  # Mon
    assert not sender.in_send_window(datetime(2026, 5, 19, 9, 0, tzinfo=ET))   # early
    assert not sender.in_send_window(datetime(2026, 5, 19, 14, 0, tzinfo=ET))  # at end (exclusive)
    assert not sender.in_send_window(datetime(2026, 5, 23, 10, 0, tzinfo=ET))  # Sat


def test_next_window_slot_lands_inside_window():
    slot = sender.next_window_slot(datetime(2026, 5, 18, 23, 0, tzinfo=ET))  # Mon night
    dt = datetime.fromisoformat(slot).astimezone(ET)
    assert dt.weekday() in {1, 2, 3} and 10 <= dt.hour < 14


def test_per_recipient_timezone():  # 004 D2 — window honors the lead's tz
    # 11:00 UTC is 06:00 in Chicago (outside) but 12:00 in Casablanca (inside).
    utc_now = datetime(2026, 5, 19, 11, 0, tzinfo=ZoneInfo("UTC"))  # Tue
    assert not sender.in_send_window(utc_now, tz="America/Chicago")
    assert sender.in_send_window(utc_now, tz="Africa/Casablanca")
