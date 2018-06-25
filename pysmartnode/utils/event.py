'''
Created on 10.08.2017

@author: Kevin Köck
'''

__updated__ = "2018-05-22"

import uasyncio as asyncio


class Event:
    """ Extended Event class also usable as a Lock with onTrue=True"""

    def __init__(self, poll_ms=20, onTrue=True):
        self.__poll_ms = poll_ms
        self.__onTrue = onTrue
        self._flag = False
        self._data = None
        self.clear()

    def clear(self):
        self._flag = False
        self._data = None

    def __await__(self):
        while self._flag != self.__onTrue:
            yield from asyncio.sleep_ms(self.__poll_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data
