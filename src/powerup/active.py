import time

# @author Daniel McCoy Stephenson
# @since August 2nd, 2026


class ActivePowerUps:
    """Expiry bookkeeping for the power-ups currently running on a snake.

    Deliberately knows nothing about what a power-up *does* - it only tracks
    when each one runs out. Gameplay owns the effects and both renderers ask
    this same object what to display, so the two UIs cannot drift apart on
    which power-ups are active or how much time is left (the recurring
    problem behind PRs #92, #95 and #99).

    Time is taken as an optional `now` argument throughout rather than being
    read from a clock the caller can't see, so timing is testable without
    monkeypatching this module.
    """

    def __init__(self):
        self.expiresAt = {}

    def activate(self, powerUpType, durationSeconds, now=None):
        """Starts a power-up, or refreshes one that is already running.

        Returns True only for a fresh activation. Collecting a power-up that
        is already active extends its timer and returns False, which is what
        lets gameplay apply an effect exactly once instead of compounding it
        (e.g. halving an already-halved tick speed).
        """
        now = time.time() if now is None else now
        newlyActivated = not self.isActive(powerUpType)
        self.expiresAt[powerUpType] = now + durationSeconds
        return newlyActivated

    def isActive(self, powerUpType):
        """True from activation until expire() clears the power-up.

        A power-up whose timer has run out is still "active" until the next
        expire() call, matching how the game loop reverts effects once per
        tick rather than mid-tick.
        """
        return powerUpType in self.expiresAt

    def remainingSeconds(self, powerUpType, now=None):
        """Seconds left on a power-up, or None when it isn't running.

        Never negative: an expired-but-not-yet-cleared power-up reports 0,
        so a renderer reading it during that one frame can't show a
        countdown that has gone past zero.
        """
        if powerUpType not in self.expiresAt:
            return None
        now = time.time() if now is None else now
        return max(0.0, self.expiresAt[powerUpType] - now)

    def expire(self, now=None):
        """Clears every power-up whose timer has run out.

        Returns the types that just expired (in activation order) so the
        caller can revert their effects and announce them.
        """
        now = time.time() if now is None else now
        expired = [
            powerUpType
            for powerUpType, expiresAt in self.expiresAt.items()
            if now >= expiresAt
        ]
        for powerUpType in expired:
            del self.expiresAt[powerUpType]
        return expired

    def statuses(self, now=None):
        """[(powerUpType, secondsRemaining)] for everything still running.

        Power-ups with no time left are omitted: expire() clears them on the
        next tick, and until then there is nothing useful to show for them.
        Ordered by activation so a HUD line doesn't jump around between
        frames.
        """
        now = time.time() if now is None else now
        statuses = []
        for powerUpType in self.expiresAt:
            secondsRemaining = self.remainingSeconds(powerUpType, now)
            if secondsRemaining > 0:
                statuses.append((powerUpType, secondsRemaining))
        return statuses

    def clear(self):
        """Drops every timer, e.g. when a new run or level starts."""
        self.expiresAt.clear()

    def shiftDeadlines(self, seconds):
        """Pushes every running timer back by `seconds`.

        Timers are wall-clock based, so time a run spends held (see the
        pause action in issue #130) would otherwise drain them: a 5s boost
        paused for a minute would be gone the moment play resumed. Shifting
        the deadlines by the length of the hold gives each power-up back
        exactly the time it had left.

        Only the deadlines move; which power-ups are running is unchanged,
        so this stays the same kind of bookkeeping-only object it is
        elsewhere and never revives one that already expired.
        """
        for powerUpType in self.expiresAt:
            self.expiresAt[powerUpType] += seconds
