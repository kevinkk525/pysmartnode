'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "3.5"
__updated__ = "2019-01-03"

import gc
import json
import time

gc.collect()

from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars

from micropython_iot_generic.client import apphandler
from micropython_iot_generic.client.apps.mqtt import Mqtt
from micropython_iot import Lock, Event
from machine import Pin

gc.collect()
import uasyncio as asyncio
import os
import sys

_log = logging.getLogger("MQTT")
gc.collect()

type_gen = type((lambda: (yield))())  # Generator type

app_handler = apphandler.AppHandler(asyncio.get_event_loop(), sys_vars.getDeviceID(), config.MQTT_HOST,
                                    8888, timeout=3000, verbose=True,
                                    led=Pin(2, Pin.OUT, value=1))


class MQTTHandler(Mqtt):
    def __init__(self, receive_config=False):
        """
        receive_config: False, if true tries to get the configuration of components
            from a server connected to the mqtt broker
        allow_wildcards: True, if false no subscriptions ending with "/#" are allowed;
            this also saves RAM as the module "subscription" is used as a backend
            to store subscriptions instead of the module "tree" which is bigger
        """
        gc.collect()
        self.payload_on = ("ON", True, "True")
        self.payload_off = ("OFF", False, "False")
        self.client_id = sys_vars.getDeviceID()
        self.mqtt_home = config.MQTT_HOME
        super().__init__((self.getRealTopic(self.getDeviceTopic("status")), "OFFLINE", 1, True),
                         (self.getRealTopic(self.getDeviceTopic("status")), "ONLINE", 1, True))
        self.__receive_config = receive_config
        # True=receive config, None=config received
        self._awaiting_config = False

    def concb(self, state):
        if config.DEBUG:
            _log.info("WIFI state {!s}".format(state), local_only=True)
        if state is True:
            asyncio.get_event_loop().create_task(self._publishDeviceStats())
            if self.__receive_config is True:
                asyncio.get_event_loop().create_task(self._receiveConfig())
        super().concb(state)

    async def _receiveConfig(self):
        self.__receive_config = None
        while True:
            gc.collect()
            _log.debug("RAM before receiveConfig import: {!s}".format(gc.mem_free()), local_only=True)
            import pysmartnode.networking.mqtt_receive_config
            gc.collect()
            _log.debug("RAM after receiveConfig import: {!s}".format(gc.mem_free()), local_only=True)
            result = await pysmartnode.networking.mqtt_receive_config.requestConfig(config, self, _log)
            if result is False:
                _log.info("Using local components.json/py", local_only=True)
                gc.collect()
                _log.debug("RAM before receiveConfig deletion: {!s}".format(gc.mem_free()), local_only=True)
                del pysmartnode.networking.mqtt_receive_config
                del sys.modules["pysmartnode.networking.mqtt_receive_config"]
                gc.collect()
                _log.debug("RAM after receiveConfig deletion: {!s}".format(gc.mem_free()), local_only=True)
                local_works = await config._loadComponentsFile()
                if local_works is True:
                    return True
            else:
                gc.collect()
                _log.debug("RAM before receiveConfig deletion: {!s}".format(gc.mem_free()), local_only=True)
                del pysmartnode.networking.mqtt_receive_config
                del sys.modules["pysmartnode.networking.mqtt_receive_config"]
                gc.collect()
                _log.debug("RAM after receiveConfig deletion: {!s}".format(gc.mem_free()), local_only=True)
                result = json.loads(result)
                loop = asyncio.get_event_loop()
                if platform == "esp8266":
                    # on esp8266 components are split in small files and loaded after each other
                    # to keep RAM requirements low, only if filesystem is enabled
                    if sys_vars.hasFilesystem():
                        loop.create_task(config._loadComponentsFile())
                    else:
                        loop.create_task(config._registerComponentsAsync(result))
                else:
                    # on esp32 components are registered directly but async to let logs run between registrations
                    loop.create_task(config._registerComponentsAsync(result))
                return True
            await asyncio.sleep(60)  # if connection not stable or broker unreachable, try again in 60s

    def _convertToDeviceTopic(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.client_id), ".")
        raise TypeError("Topic is not a device subscription: {!s}".format(topic))

    def _isDeviceSubscription(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return True
        return False

    async def unsubscribe(self, topic, callback=None):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        if callback is None:
            _log.debug("unsubscribing topic {}".format(topic), local_only=True)
        else:
            _log.debug("unsubscribing callback from topic {}".format(topic), local_only=True)
        try:
            await super().unsubscribe(topic, callback)
        except AttributeError:
            _log.warn("Topic {!s} does not exist".format(topic))

    def scheduleSubscribe(self, topic, callback_coro, qos=0, check_retained_state_topic=True):
        asyncio.get_event_loop().create_task(self.subscribe(topic, callback_coro, qos, check_retained_state_topic))

    async def subscribe(self, topic, callback_coro, qos=0, check_retained_state_topic=True):
        _log.debug("Subscribing to topic {}".format(topic), local_only=True)
        if type(callback_coro) is None:
            await _log.asyncLog("error", "Can't subscribe with callback of type None to topic {!s}".format(topic))
            return False
        # if self._isDeviceSubscription(topic):
        #    topic = self._convertToDeviceTopic(topic)
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        await super().subscribe(topic, callback_coro, qos, check_retained_state_topic)

    async def _publishDeviceStats(self):
        if self.__receive_config is not None:  # only works if not yielded before
            await self.publish(self.getDeviceTopic("version"), config.VERSION, 1, True)
            # only log on first connection, not on reconnect as nothing has changed here
            if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
                t = time.localtime()
                await self.publish(self.getDeviceTopic("last_boot"),
                                   "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3],
                                                                                  t[4],
                                                                                  t[5]), 1, True)
                _log.info(str(os.uname()))
                _log.info("Client version: {!s}".format(config.VERSION))
        else:
            await _log.asyncLog("debug", "Reconnected")
        await self.publish(self.getDeviceTopic("status"), "ONLINE", 1, True)

    @staticmethod
    def getDeviceTopic(attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return ".{}".format(attrib)

    @staticmethod
    def _isDeviceTopic(topic):
        return topic.startswith(".")

    def getRealTopic(self, device_topic):
        if device_topic.startswith(".") is False:
            raise ValueError("Topic {!s} is no device topic".format(device_topic))
        return "{}/{}/{}".format(self.mqtt_home, self.client_id, device_topic[1:])

    def handle(self, header, data):
        """mqtt library only handles sync callbacks so add it to asyncio loop"""
        _log.debug("mqtt execution: {!s}, {!s}".format(header, data), local_only=True)
        super().handle(header, data)

    async def _wrapper(self, cb, data):
        self._cbs += 1
        if self._isDeviceSubscription(data[0]):
            topic = self._convertToDeviceTopic(data[0])
        else:
            topic = data[0]
        try:
            msg = json.loads(data[2])
        except ValueError:
            msg = data[2]
        try:
            res = cb(topic, msg, data[3])
            if type(res) == type_gen:
                await res
        except Exception as e:
            await _log.asyncLog("error", "Exception executing mqtt: {!s}".format(e))
        finally:
            self._cbs -= 1

    async def publish(self, topic, msg, qos=0, retain=False):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        await super().publish(topic, msg, qos, retain)

    def schedulePublish(self, topic, msg, qos=0, retain=False):
        asyncio.get_event_loop().create_task(self.publish(topic, msg, qos, retain))
