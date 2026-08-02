from powerup.active import ActivePowerUps
from powerup.powerup import PowerUpType


def test_nothing_is_active_on_a_fresh_tracker():
    active = ActivePowerUps()

    assert active.isActive(PowerUpType.SPEED) is False
    assert active.remainingSeconds(PowerUpType.SPEED) is None
    assert active.statuses() == []


def test_activate_reports_a_fresh_activation():
    active = ActivePowerUps()

    assert active.activate(PowerUpType.SPEED, 5.0, now=100) is True
    assert active.isActive(PowerUpType.SPEED) is True
    assert active.remainingSeconds(PowerUpType.SPEED, now=100) == 5.0


def test_reactivating_refreshes_the_timer_without_reporting_a_new_activation():
    # gameplay applies a power-up's effect only on a fresh activation, so
    # this is what stops a second pickup compounding the effect
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.activate(PowerUpType.SPEED, 5.0, now=103) is False
    assert active.remainingSeconds(PowerUpType.SPEED, now=103) == 5.0


def test_remaining_seconds_never_goes_negative():
    # expire() only clears a run-out power-up on the next tick, so it stays
    # readable for one frame - report 0 rather than a negative countdown
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.remainingSeconds(PowerUpType.SPEED, now=200) == 0


def test_expire_clears_and_returns_only_the_run_out_power_ups():
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)
    active.activate(PowerUpType.INVINCIBILITY, 3.0, now=100)

    assert active.expire(now=104) == [PowerUpType.INVINCIBILITY]
    assert active.isActive(PowerUpType.INVINCIBILITY) is False
    assert active.isActive(PowerUpType.SPEED) is True

    assert active.expire(now=106) == [PowerUpType.SPEED]
    assert active.isActive(PowerUpType.SPEED) is False


def test_expire_is_a_noop_when_nothing_has_run_out():
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.expire(now=101) == []
    assert active.isActive(PowerUpType.SPEED) is True


def test_expire_fires_exactly_on_the_expiry_moment():
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.expire(now=105) == [PowerUpType.SPEED]


def test_statuses_lists_every_running_power_up_in_activation_order():
    active = ActivePowerUps()
    active.activate(PowerUpType.INVINCIBILITY, 3.0, now=100)
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.statuses(now=101) == [
        (PowerUpType.INVINCIBILITY, 2.0),
        (PowerUpType.SPEED, 4.0),
    ]


def test_statuses_omits_a_power_up_with_no_time_left():
    # it is cleared by the next expire(); until then there is nothing worth
    # putting on the HUD for it
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)

    assert active.statuses(now=105) == []


def test_clear_drops_every_timer():
    active = ActivePowerUps()
    active.activate(PowerUpType.SPEED, 5.0, now=100)
    active.activate(PowerUpType.INVINCIBILITY, 3.0, now=100)

    active.clear()

    assert active.statuses(now=100) == []
    assert active.isActive(PowerUpType.SPEED) is False
