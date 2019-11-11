# Author: Kevin Köck
# Copyright Kevin Köck 2017-2019 Released under the MIT license
# Created on 2017-07-19

__updated__ = "2019-11-02"
__version__ = "2.9"

# TODO: Add possibility to use real logging module on esp32 and save logs locally or to sdcard

import gc
from pysmartnode.utils import sys_vars
from pysmartnode import config
import uasyncio as asyncio

gc.collect()
import time


async def asyncLog(name, level, *message, timeout=None, await_connection=True):
    if level == "debug" and not config.DEBUG:  # ignore debug messages if debug is disabled
        return
    if config.getMQTT():
        base_topic = "{!s}/log/{!s}/{!s}".format(config.MQTT_HOME, "{!s}", sys_vars.getDeviceID())
        # if level is before id other clients can subscribe to e.g. all critical logs
        message = (b"{} " * (len(message) + 1)).format("[{}]".format(name), *message)
        gc.collect()
        await config.getMQTT().publish(base_topic.format(level), message, qos=1, timeout=timeout,
                                       await_connection=await_connection)
        # format message as bytes so there's no need to encode it later.


def log(name, level, *message, local_only=False, return_only=False, timeout=None):
    if level == "debug" and not config.DEBUG:  # ignore debug messages if debug is disabled
        return
    if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
        if hasattr(time, "strftime"):
            print("[{}]".format(time.strftime("%Y-%m-%d %H:%M:%S")), "[{}]".format(name),
                  "[{}]".format(level), *message)
        else:
            t = time.localtime()
            print("[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(*t), "[{}]".format(name),
                  "[{}]".format(level), *message)
    else:
        print("[{!s}] [{!s}]".format(name, level), *message)
    if return_only:
        return
    if not local_only:
        asyncio.create_task(asyncLog(name, level, *message, timeout=timeout,
                                                      await_connection=True))


class Logger:
    def __init__(self, name):
        self.name = name

    def critical(self, *message, local_only=False):
        log(self.name, "critical", *message, local_only=local_only, timeout=None)

    def error(self, *message, local_only=False):
        log(self.name, "error", *message, local_only=local_only, timeout=None)

    def warn(self, *message, local_only=False):
        log(self.name, "warn", *message, local_only=local_only, timeout=None)

    def info(self, *message, local_only=False):
        log(self.name, "info", *message, local_only=local_only, timeout=20)

    def debug(self, *message, local_only=False):
        log(self.name, "debug", *message, local_only=local_only, timeout=5)

    async def asyncLog(self, level, *message, timeout=None, await_connection=True):
        log(self.name, level, *message, return_only=True)
        if timeout == 0:
            return
        await asyncLog(self.name, level, *message, timeout=timeout,
                       await_connection=await_connection)


def getLogger(name):
    return Logger(name)
