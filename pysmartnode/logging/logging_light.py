# Author: Kevin Köck
# Copyright Kevin Köck 2018-2019 Released under the MIT license
# Created on 2018-03-10

__updated__ = "2019-11-02"
__version__ = "2.6"

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

    def _log(self, level, *message, local_only=False, timeout=None):
        print("[{!s}]".format(level), *message)
        if timeout == 0:
            return
        if config.getMQTT() and not local_only:
            message = (b"{} " * len(message)).format(*message)
            asyncio.create_task(
                config.getMQTT().publish(self.base_topic.format(level), message, qos=1,
                                         timeout=timeout, await_connection=True))
            # format message as bytes so there's no need to encode it later.

    def critical(self, *message, local_only=False):
        self._log("critical", *message, local_only=local_only, timeout=None)

    def error(self, *message, local_only=False):
        self._log("error", *message, local_only=local_only, timeout=None)

    def warn(self, *message, local_only=False):
        self._log("warn", *message, local_only=local_only, timeout=None)

    def info(self, *message, local_only=False):
        self._log("info", *message, local_only=local_only, timeout=20)

    def debug(self, *message, local_only=False):
        if config.DEBUG:  # ignore debug messages if debug is disabled
            self._log("debug", *message, local_only=local_only, timeout=5)

    async def asyncLog(self, level, *message, timeout=None, await_connection=True):
        if level == "debug" and not config.DEBUG:  # ignore debug messages if debug is disabled
            return
        print("[{!s}]".format(level), *message)
        if timeout == 0:
            return
        if config.getMQTT() is not None:
            await config.getMQTT().publish(self.base_topic.format(level),
                                           b"{}".format(message if len(message) > 1 else
                                                        message[0]),
                                           qos=1, timeout=timeout,
                                           await_connection=await_connection)


log = Logging()


def getLogger(name):
    return log
