import pytest
from ski_resort_pass import process_resort_bookings, check_chairlift_anemometer


# ==========================================================
# Branch Coverage Tests for ski_resort_pass.py
# Target: >= 90% Branch Coverage (Aiming for 100% Branch Coverage)
# Covers every decision branch: True/False on all conditions
# ==========================================================

# --- Branch Tests for process_resort_bookings ---

def test_branch_groups_not_a_list():
    """Branch: not isinstance(groups, list) is True."""
    with pytest.raises(ValueError, match="Invalid groups list or facility fee"):
        process_resort_bookings("not_a_list", 10.0)


def test_branch_negative_facility_fee():
    """Branch: facility_fee < 0 is True."""
    with pytest.raises(ValueError, match="Invalid groups list or facility fee"):
        process_resort_bookings([], -0.01)


def test_branch_empty_groups_zero_sales():
    """Branch: groups is empty list (loop 0 iterations) and total_revenue == 0.0."""
    result = process_resort_bookings([], 0.0)
    assert result == {"total_revenue": 0.0, "status": "ZERO_SALES"}


def test_branch_inactive_group():
    """Branch: group.get('is_active') evaluates to False."""
    groups = [{"is_active": False, "duration": "full_day", "skiers": [{"age": 25}]}]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_branch_invalid_duration():
    """Branch: duration not season, full_day, or half_day (else branch)."""
    groups = [{"is_active": True, "duration": "quarter_day", "skiers": [{"age": 25}]}]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_branch_season_pass_child_without_locker():
    """Branch: duration=='season', age < 12, includes_lodge_locker=False, gear_rental=False."""
    groups = [
        {
            "is_active": True,
            "duration": "season",
            "includes_lodge_locker": False,
            "skiers": [{"age": 11, "gear_rental": False, "blackout_override": False}]
        }
    ]
    # base = 300, child = 300 * 0.60 = 180.0
    result = process_resort_bookings(groups, 20.0)
    assert result["total_revenue"] == 180.0
    assert result["status"] == "COMPLETED"


def test_branch_full_day_senior_with_locker_and_gear():
    """Branch: duration=='full_day', age >= 65, includes_lodge_locker=True, gear_rental=True."""
    groups = [
        {
            "is_active": True,
            "duration": "full_day",
            "includes_lodge_locker": True,
            "skiers": [{"age": 65, "gear_rental": True, "blackout_override": False}]
        }
    ]
    # base = 80, senior = 80 * 0.70 = 56.0, gear = 35.0, locker = 15.0 -> 106.0
    result = process_resort_bookings(groups, 15.0)
    assert result["total_revenue"] == 106.0
    assert result["status"] == "COMPLETED"


def test_branch_half_day_standard_adult():
    """Branch: duration=='half_day', adult (12 <= age < 65)."""
    groups = [
        {
            "is_active": True,
            "duration": "half_day",
            "includes_lodge_locker": False,
            "skiers": [
                {"age": 12, "gear_rental": False, "blackout_override": False},
                {"age": 64, "gear_rental": False, "blackout_override": False}
            ]
        }
    ]
    # base = 50 * 2 = 100.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 100.0
    assert result["status"] == "COMPLETED"


def test_branch_skier_invalid_age():
    """Branch: age <= 0 (tested with 0 and negative)."""
    groups = [
        {
            "is_active": True,
            "duration": "full_day",
            "skiers": [
                {"age": 0},
                {"age": -10},
                {"age": 25}
            ]
        }
    ]
    # 2 invalid skiers skipped, 1 adult accepted = 80.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 80.0
    assert result["status"] == "COMPLETED"


def test_branch_blackout_override_half_day_break():
    """Branch: blackout_override is True AND pass_duration == 'half_day' (zeros total and breaks)."""
    groups = [
        {
            "is_active": True,
            "duration": "half_day",
            "skiers": [
                {"age": 30, "blackout_override": True},
                {"age": 30, "blackout_override": False}  # unreachable due to break
            ]
        }
    ]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_branch_blackout_override_non_half_day():
    """Branch: blackout_override is True AND pass_duration != 'half_day' (applies 50% base rate)."""
    groups = [
        {
            "is_active": True,
            "duration": "season",
            "skiers": [{"age": 30, "blackout_override": True}]
        }
    ]
    # base = 300 * 0.50 = 150.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 150.0
    assert result["status"] == "COMPLETED"


def test_branch_audit_review_exceeds_four_rejections():
    """Branch: rejected_passes > 4 triggers AUDIT_REVIEW status."""
    groups = [
        {"is_active": True, "duration": "bad_duration", "skiers": []},  # +1
        {"is_active": True, "duration": "bad_duration_2", "skiers": []},  # +2
        {
            "is_active": True,
            "duration": "full_day",
            "skiers": [
                {"age": 0},   # +3
                {"age": -5},  # +4
                {"age": 20, "blackout_override": True},  # +5
                {"age": 30}   # valid: 80.0
            ]
        }
    ]
    # 5 rejections (> 4), valid skier gives 80 + (300/80*0.5=40) = 120.0
    result = process_resort_bookings(groups, 10.0)
    assert result["status"] == "AUDIT_REVIEW"
    assert result["total_revenue"] == 120.0


# --- Branch Tests for check_chairlift_anemometer ---

def test_branch_anemometer_empty_and_none():
    """Branch: not wind_streams evaluates to True."""
    assert check_chairlift_anemometer([]) == "NO_DATA"
    assert check_chairlift_anemometer(None) == "NO_DATA"


def test_branch_anemometer_suspend_lift_immediate_two_gusts():
    """Branch: speed_mph > 45 True twice consecutively -> wind_gust_streak >= 2 True."""
    wind_streams = [
        [46, 47]
    ]
    assert check_chairlift_anemometer(wind_streams) == "SUSPEND_LIFT"


def test_branch_anemometer_gust_resets_on_low_speed():
    """Branch: speed_mph <= 45 (boundary 45 and below) resets streak to 0, returns SAFE_OPERATION."""
    wind_streams = [
        [45, 46, 45, 46, 30],  # Single gusts interspersed with <= 45 readings
        [20, 25, 40]
    ]
    assert check_chairlift_anemometer(wind_streams) == "SAFE_OPERATION"


def test_branch_anemometer_multiple_streams_no_gusts():
    """Branch: all readings safe across multiple lift streams."""
    wind_streams = [
        [10, 20, 30],
        [],
        [40, 44, 45]
    ]
    assert check_chairlift_anemometer(wind_streams) == "SAFE_OPERATION"
