'''
Created on 10.03.2018

@author: Kevin Köck
'''

__updated__ = "2018-09-28"
__version__ = "2.2"

import gc
from pysmartnode.utils import sys_vars
from pysmartnode import config
import uasyncio as asyncio

gc.collect()


class Logging:
    def __init__(self):
        self.id = sys_vars.getDeviceID()
        self.base_topic = "{!s}/log/{!s}/{!s}".format(config.MQTT_HOME, "{!s}", sys_vars.getDeviceID())
        # if level is before id other clients can subscribe to e.g. all critical logs

    def _log(self, message, level, local_only=False):
        print("[{!s}] {}".format(level, message))
        if config.getMQTT() is not None and local_only is False:
            asyncio.get_event_loop().create_task(
                config.getMQTT().publish(self.base_topic.format(level), "{}".format(message)), qos=1)

    def critical(self, message, local_only=False):
        self._log(message, "critical", local_only)

    def error(self, message, local_only=False):
        self._log(message, "error", local_only)

    def warn(self, message, local_only=False):
        self._log(message, "warn", local_only)

    def info(self, message, local_only=False):
        self._log(message, "info", local_only)

    def debug(self, message, local_only=False):
        self._log(message, "debug", local_only)

    async def asyncLog(self, level, message):
        print("[{!s}] {}".format(level, message))
        if config.getMQTT() is not None:
            await config.getMQTT().publish(self.base_topic.format(level), "{}".format(message), qos=1)


log = Logging()


def getLogger(name):
    return log
