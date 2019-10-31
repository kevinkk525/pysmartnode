# Author: Kevin Köck
# Copyright Kevin Köck 2018-2019 Released under the MIT license
# Created on 2018-03-10

__updated__ = "2019-10-28"
__version__ = "2.4"

import gc
from pysmartnode.utils import sys_vars
from pysmartnode import config
import uasyncio as asyncio

gc.collect()


class Logging:
    def __init__(self):
        self.id = sys_vars.getDeviceID()
        self.base_topic = "{!s}/log/{!s}/{!s}".format(config.MQTT_HOME, "{!s}",
                                                      sys_vars.getDeviceID())
        # if level is before id other clients can subscribe to e.g. all critical logs

    def _log(self, message, level, local_only=False, timeout=None):
        print("[{!s}] {}".format(level, message))
        if timeout == 0:
            return
        if config.getMQTT() is not None and local_only is False:
            asyncio.get_event_loop().create_task(
                config.getMQTT().publish(self.base_topic.format(level), b"{}".format(message),
                                         qos=1, timeout=timeout, await_connection=True))
            # format message as bytes so there's no need to encode it later.

    def critical(self, message, local_only=False):
        self._log(message, "critical", local_only, timeout=None)

    def error(self, message, local_only=False):
        self._log(message, "error", local_only, timeout=None)

    def warn(self, message, local_only=False):
        self._log(message, "warn", local_only, timeout=None)

    def info(self, message, local_only=False):
        self._log(message, "info", local_only, timeout=20)

    def debug(self, message, local_only=False):
        self._log(message, "debug", local_only, timeout=5)

    async def asyncLog(self, level, message, timeout=None, await_connection=True):
        print("[{!s}] {}".format(level, message))
        if timeout == 0:
            return
        if config.getMQTT() is not None:
            await config.getMQTT().publish(self.base_topic.format(level), "{}".format(message),
                                           qos=1, timeout=timeout,
                                           await_connection=await_connection)


log = Logging()


def getLogger(name):
    return log
