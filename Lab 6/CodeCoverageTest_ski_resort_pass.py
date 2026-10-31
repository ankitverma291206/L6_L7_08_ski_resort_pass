import pytest
from ski_resort_pass import process_resort_bookings, check_chairlift_anemometer


# ==========================================
# Code Coverage Tests for ski_resort_pass.py
# Target: >= 90% Line Coverage (Aiming for 100%)
# ==========================================

def test_invalid_groups_argument():
    """Verify ValueError is raised when groups is not a list."""
    with pytest.raises(ValueError, match="Invalid groups list or facility fee"):
        process_resort_bookings("invalid_group", 10.0)


def test_invalid_facility_fee():
    """Verify ValueError is raised when facility_fee is negative."""
    with pytest.raises(ValueError, match="Invalid groups list or facility fee"):
        process_resort_bookings([], -1.0)


def test_inactive_group():
    """Verify inactive groups are skipped."""
    groups = [
        {
            "is_active": False,
            "duration": "full_day",
            "skiers": [{"age": 25, "gear_rental": False, "blackout_override": False}]
        }
    ]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_invalid_duration_rejected():
    """Verify unknown duration increments rejected passes and continues."""
    groups = [
        {
            "is_active": True,
            "duration": "weekly",
            "skiers": [{"age": 25}]
        }
    ]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_season_duration_and_child_discount_with_lodge_locker():
    """Verify season duration rate, child discount (<12), and locker fee."""
    groups = [
        {
            "is_active": True,
            "duration": "season",
            "includes_lodge_locker": True,
            "skiers": [{"age": 10, "gear_rental": False, "blackout_override": False}]
        }
    ]
    # base = 300, child = 300 * 0.60 = 180, locker = 25 -> 205.0
    result = process_resort_bookings(groups, 25.0)
    assert result["total_revenue"] == 205.0
    assert result["status"] == "COMPLETED"


def test_half_day_duration_and_senior_discount_with_gear():
    """Verify half_day rate, senior discount (>=65), and gear rental."""
    groups = [
        {
            "is_active": True,
            "duration": "half_day",
            "includes_lodge_locker": False,
            "skiers": [{"age": 70, "gear_rental": True, "blackout_override": False}]
        }
    ]
    # base = 50, senior = 50 * 0.70 = 35, gear = 35 -> 70.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 70.0
    assert result["status"] == "COMPLETED"


def test_skier_invalid_age():
    """Verify skiers with age <= 0 are rejected."""
    groups = [
        {
            "is_active": True,
            "duration": "full_day",
            "skiers": [
                {"age": 0, "gear_rental": False, "blackout_override": False},
                {"age": 30, "gear_rental": False, "blackout_override": False}
            ]
        }
    ]
    # Skier 1 rejected, Skier 2 accepted: 80.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 80.0
    assert result["status"] == "COMPLETED"


def test_blackout_override_half_day_breaks_group():
    """Verify blackout override on half_day zeros out group and breaks."""
    groups = [
        {
            "is_active": True,
            "duration": "half_day",
            "skiers": [
                {"age": 30, "gear_rental": False, "blackout_override": True},
                {"age": 25, "gear_rental": False, "blackout_override": False}
            ]
        }
    ]
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 0.0
    assert result["status"] == "ZERO_SALES"


def test_blackout_override_full_day():
    """Verify blackout override on full_day adds 50% rate."""
    groups = [
        {
            "is_active": True,
            "duration": "full_day",
            "skiers": [{"age": 30, "gear_rental": False, "blackout_override": True}]
        }
    ]
    # base = 80 * 0.50 = 40.0
    result = process_resort_bookings(groups, 10.0)
    assert result["total_revenue"] == 40.0
    assert result["status"] == "COMPLETED"


def test_audit_review_status_when_rejected_exceeds_four():
    """Verify AUDIT_REVIEW status when rejected_passes > 4."""
    groups = [
        {
            "is_active": True,
            "duration": "invalid_duration",  # rejected 1
            "skiers": []
        },
        {
            "is_active": True,
            "duration": "full_day",
            "skiers": [
                {"age": -1},  # rejected 2
                {"age": 0},   # rejected 3
                {"age": 25, "blackout_override": True},  # rejected 4
                {"age": 25, "blackout_override": True},  # rejected 5
                {"age": 25}   # accepted: 80.0
            ]
        }
    ]
    result = process_resort_bookings(groups, 10.0)
    assert result["status"] == "AUDIT_REVIEW"


def test_anemometer_no_data():
    """Verify check_chairlift_anemometer returns NO_DATA for empty input."""
    assert check_chairlift_anemometer([]) == "NO_DATA"
    assert check_chairlift_anemometer(None) == "NO_DATA"


def test_anemometer_suspend_lift():
    """Verify check_chairlift_anemometer triggers SUSPEND_LIFT on 2 consecutive gusts > 45 mph."""
    wind_streams = [
        [30, 40, 50, 52, 20]
    ]
    assert check_chairlift_anemometer(wind_streams) == "SUSPEND_LIFT"


def test_anemometer_safe_operation_with_reset():
    """Verify gust streak resets when speed <= 45 mph and returns SAFE_OPERATION."""
    wind_streams = [
        [50, 30, 48, 40, 10]
    ]
    assert check_chairlift_anemometer(wind_streams) == "SAFE_OPERATION"
