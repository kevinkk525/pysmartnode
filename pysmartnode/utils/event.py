# Author: Kevin Köck
# Copyright Kevin Köck 2017-2019 Released under the MIT license
# Created on 2017-08-10

__updated__ = "2018-07-14"

import uasyncio as asyncio


class Event:
    def __init__(self, poll_ms=20):
        self.__poll_ms = poll_ms
        self._flag = False
        self._data = None

    def clear(self):
        self._flag = False
        self._data = None

    def __await__(self):
        while self._flag is not True:
            yield from asyncio.sleep_ms(self.__poll_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data
