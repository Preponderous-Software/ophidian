import time

# @author Daniel McCoy Stephenson
# @since July 4th, 2026


class UiBanner:
    """Queued, timed on-screen messages for the pygame UI.

    A plain single-slot "current message" would silently lose messages that
    fire back-to-back in the same tick - e.g. an ascension notification
    immediately followed by the next run's biome-arrival message, both set
    before any frame is ever drawn. Queuing them means each gets its turn on
    screen instead of only the last one ever being seen.
    """

    def __init__(self, durationSeconds=2.0):
        self.durationSeconds = durationSeconds
        self.queue = []
        self.expiresAt = None

    def push(self, message):
        self.queue.append(message)

    def current(self):
        """Returns the message that should currently be shown, or None.

        Call once per frame - advances/expires the queue as a side effect.
        """
        if not self.queue:
            return None
        if self.expiresAt is None:
            self.expiresAt = time.time() + self.durationSeconds
        if time.time() >= self.expiresAt:
            self.queue.pop(0)
            self.expiresAt = None
            if not self.queue:
                return None
        return self.queue[0]

    def draw(self, graphik, width, backgroundColor, textColor):
        message = self.current()
        if message is None:
            return
        graphik.drawRectangle(0, 0, width, 30, backgroundColor)
        graphik.drawText(message, width // 2, 15, 16, textColor)
