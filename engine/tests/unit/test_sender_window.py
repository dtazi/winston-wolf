from datetime import datetime
from zoneinfo import ZoneInfo

from ww_engine import sender

ET = ZoneInfo("America/New_York")


def test_inside_window_tue_to_thu_morning():  # happy
    assert sender.in_send_window(datetime(2026, 5, 19, 10, 0, tzinfo=ET))  # Tue


def test_outside_window_edges():  # error/edge
    assert not sender.in_send_window(datetime(2026, 5, 18, 10, 0, tzinfo=ET))  # Mon
    assert not sender.in_send_window(datetime(2026, 5, 19, 8, 0, tzinfo=ET))   # early
    assert not sender.in_send_window(datetime(2026, 5, 19, 11, 0, tzinfo=ET))  # at end (exclusive)
    assert not sender.in_send_window(datetime(2026, 5, 23, 10, 0, tzinfo=ET))  # Sat


def test_next_window_slot_lands_inside_window():
    slot = sender.next_window_slot(datetime(2026, 5, 18, 23, 0, tzinfo=ET))  # Mon night
    dt = datetime.fromisoformat(slot).astimezone(ET)
    assert dt.weekday() in {1, 2, 3} and 9 <= dt.hour < 11
