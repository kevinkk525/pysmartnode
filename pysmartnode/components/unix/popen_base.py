# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-07-02 

__updated__ = "2019-07-03"
__version__ = "0.2"

import os
import uasyncio as asyncio
from pysmartnode.utils.wrappers.timeit import timeitAsync


class Popen:
    def __init__(self, command, expected_return=None, execution_time=0, iterations=1, iter_delay=10):
        self._com = command
        self._expected_return = expected_return
        self._iterations = iterations
        self._iter_delay = iter_delay
        self._exec_time = execution_time

    @timeitAsync
    async def _execute(self):
        """
        Execute the stored function.
        :return:
        """
        f = os.popen(self._com)
        if self._exec_time > 0:
            await asyncio.sleep_ms(self._exec_time)
        try:
            r = f.read()
            print(r)
            if self._expected_return is not None:
                if r == self._expected_return:
                    return True
                return False
            else:
                return r
        except Exception as e:
            raise e
        finally:
            f.close()

    async def execute(self):
        """
        Executes the command self._iterations times and returns True if at least one return value
        equals the expected return otherwise it will return the returned value.
        :return:
        """
        eq = False
        for i in range(self._iterations):
            r = await self._execute()
            if r == self._expected_return:
                eq = True
            await asyncio.sleep_ms(self._iter_delay)
        return eq if eq is True else r
