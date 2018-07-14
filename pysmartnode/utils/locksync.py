class Lock:
    """ synchronous lock that does not block"""

    def __init__(self):
        self._locked = False

    def acquire(self):
        if self._locked:
            return False
        else:
            self._locked = True
            return True

    def locked(self):
        return self._locked

    def release(self):
        self._locked = False
        # not checking if it was locked
        return True
