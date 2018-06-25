'''
Created on 19.07.2017

@author: Kevin Köck
'''

__updated__ = "2018-05-22"
__version__ = "2.2"

# TODO: Add possibility to use real logging module on esp32_lobo and save logs locally or to sdcard

import gc
from pysmartnode.utils import sys_vars
from pysmartnode import config

gc.collect()
import time


class Logging:
    def __init__(self):
        self.loop = None
        self.mqtt = None
        self.base_topic = "{!s}/log/{!s}/{!s}".format(config.MQTT_HOME, "{!s}", sys_vars.getDeviceID())
        # if level is before id other clients can subscribe to e.g. all critical logs

    def setLoop(self, loop):
        self.loop = loop

    async def log(self, name, message, level):
        if self.mqtt is not None:
            await self.mqtt.publish(self.base_topic.format(level), "[{!s}] {}".format(name, message))
        else:
            print(level, message)

    def setMQTT(self, mqtt):
        self.mqtt = mqtt


log = Logging()


class Logger:
    def __init__(self, name):
        self.name = name
        self.parent = log

    def setLoop(self, loop):
        self.parent.setLoop(loop)

    def setMQTT(self, mqtt):
        self.parent.setMQTT(mqtt)

    def _log(self, message, level, local_only):
        if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
            if hasattr(time, "strftime"):
                print("[{}] [{!s}] [{!s}] {}".format(time.strftime(
                    "%Z %Y-%m-%d %H:%M:%S"), self.name, level, message))
            else:
                t = time.localtime()
                print("[{} {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}] [{!s}] [{!s}] {}".format("GMT",
                                                                                           t[0], t[1], t[2], t[3], t[4],
                                                                                           t[5], self.name, level,
                                                                                           message))
        else:
            print("[{!s}] [{!s}] {}".format(self.name, level, message))
        if local_only is False and self.parent.loop is not None:
            self.parent.loop.create_task(self.parent.log(self.name, message, level))

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


def getLogger(name):
    return Logger(name)
