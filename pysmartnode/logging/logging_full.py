'''
Created on 19.07.2017

@author: Kevin Köck
'''

__updated__ = "2019-10-25"
__version__ = "2.6"

# TODO: Add possibility to use real logging module on esp32_lobo and save logs locally or to sdcard

import gc
from pysmartnode.utils import sys_vars
from pysmartnode import config
import uasyncio as asyncio

gc.collect()
import time


async def asyncLog(name, message, level, timeout=None, await_connection=True):
    if config.getMQTT() is not None:
        base_topic = "{!s}/log/{!s}/{!s}".format(config.MQTT_HOME, "{!s}", sys_vars.getDeviceID())
        # if level is before id other clients can subscribe to e.g. all critical logs
        await config.getMQTT().publish(base_topic.format(level), "[{!s}] {}".format(name, message),
                                       qos=1, timeout=timeout, await_connection=await_connection)
    else:
        print(level, message)


def log(name, message, level, local_only=False, return_only=False, timeout=None):
    if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
        if hasattr(time, "strftime"):
            print("[{}] [{!s}] [{!s}] {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), name, level,
                                                 message))
        else:
            t = time.localtime()
            print(
                "[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}] [{!s}] [{!s}] {}".format(t[0], t[1], t[2],
                                                                                  t[3], t[4],
                                                                                  t[5], name,
                                                                                  level, message))
    else:
        print("[{!s}] [{!s}] {}".format(name, level, message))
    if return_only:
        return
    if local_only is False:
        asyncio.get_event_loop().create_task(asyncLog(name, message, level, timeout=timeout,
                                                      await_connection=True))


class Logger:
    def __init__(self, name):
        self.name = name

    def critical(self, message, local_only=False):
        log(self.name, message, "critical", local_only, timeout=None)

    def error(self, message, local_only=False):
        log(self.name, message, "error", local_only, timeout=None)

    def warn(self, message, local_only=False):
        log(self.name, message, "warn", local_only, timeout=None)

    def info(self, message, local_only=False):
        log(self.name, message, "info", local_only, timeout=20)

    def debug(self, message, local_only=False):
        log(self.name, message, "debug", local_only, timeout=5)

    async def asyncLog(self, level, message, timeout=None, await_connection=True):
        log(self.name, message, level, return_only=True)
        await asyncLog(self.name, message, level, timeout, await_connection)


def getLogger(name):
    return Logger(name)
