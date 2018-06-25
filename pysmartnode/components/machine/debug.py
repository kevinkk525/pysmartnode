'''
Created on 14.04.2018

@author: Kevin
'''

__updated__ = "2018-05-22"
__version__ = "1.1"

import gc
from pysmartnode import config
from pysmartnode import logging

log = logging.getLogger("machine.debug")
import uasyncio as asyncio
import time

gc.collect()


def overwatch(coro_name, threshold, asyncr=False):
    def func_wrapper(coro):
        if asyncr is True:
            raise TypeError("overwatch does not support coroutines")
            # as it makes not sense. a freeze would trigger every coroutine
        else:
            def wrapper(*args, **kwargs):
                startt = time.ticks_ms()
                res = coro(*args, **kwargs)
                if str(type(res)) == "<class 'generator'>":
                    log.error("Coroutine in sync overwatch")
                endt = time.ticks_ms()
                diff = time.ticks_diff(endt, startt)
                if diff > threshold:
                    log.error("Coro {!s} took {!s}ms, threshold {!s}ms".format(coro_name, diff, threshold))
                return res

            return wrapper

    return func_wrapper


def stability_log(interval=600):
    asyncio.get_event_loop().create_task(_stability_log(interval))
    asyncio.get_event_loop().create_task(_interrupt(600))


async def _interrupt(interval):  # interval in sec
    import machine
    timer = machine.Timer(1)
    global interrupt_array
    interrupt_array = [time.ticks_ms(), time.ticks_ms()]
    timer.init(period=interval * 1000, mode=machine.Timer.PERIODIC, callback=__interrupt)
    log.debug("Interrupt initialized")
    while True:
        await asyncio.sleep(interval)
        if time.ticks_diff(interrupt_array[1], interrupt_array[0]) > interval * 1.1 * 1000:
            log.warn("Interrupt has difference of {!s}".format(time.ticks_diff(interrupt_array[1], interrupt_array[0])))


def __interrupt(t):
    global interrupt_array
    interrupt_array[0] = interrupt_array[1]
    interrupt_array[1] = time.ticks_ms()
    print(interrupt_array[1], "inside interrupt")


async def _stability_log(interval):
    st = time.ticks_ms()
    while True:
        await asyncio.sleep(interval)
        st_new = time.ticks_ms()
        diff = time.ticks_diff(st_new, st) / 1000
        st = st_new
        log.debug("Still online, diff to last log: {!s}".format(diff))
        if diff > 600 * 1.1 or diff < 600 * 0.9:
            log.warn("Diff to last log not within 10%: {!s}, expected {!s}".format(diff, interval))
        gc.collect()


def start_get_stuck(interval=5000):
    asyncio.get_event_loop().create_task(_get_stuck(interval))


async def _get_stuck(interval):
    # await asyncio.sleep_ms(10)
    print("Starting stuck")
    t = time.ticks_ms()
    while time.ticks_ms() - t < interval:
        pass
    print("Stop stuck")
    # await asyncio.sleep_ms(10)
    # print("end_stuck")
