from collections import Counter

from ww_engine import rotation


def test_every_lead_gets_all_three_angles_once():  # happy path
    for g in (0, 1, 2):
        angles = [rotation.angle_for(g, t) for t in (1, 2, 3)]
        assert sorted(angles) == sorted(rotation.ANGLES)


def test_position_balance_within_10pct_at_scale():  # SC-006
    n = 300
    by_pos = {1: Counter(), 2: Counter(), 3: Counter()}
    for i in range(n):
        g = rotation.group_for_lead(f"lead-{i}")
        for t in (1, 2, 3):
            by_pos[t][rotation.angle_for(g, t)] += 1
    for t in (1, 2, 3):
        for angle in rotation.ANGLES:
            assert abs(by_pos[t][angle] - n / 3) <= 0.10 * n


def test_group_assignment_is_stable():  # error/edge: deterministic re-enrol
    assert rotation.group_for_lead("abc") == rotation.group_for_lead("abc")
