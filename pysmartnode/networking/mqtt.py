'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "1.9"
__updated__ = "2018-09-18"

import gc
import json
import time

gc.collect()

from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars

if platform == "esp8266" and (hasattr(config, "MQTT_MINIMAL_VERSION") is False or config.MQTT_MINIMAL_VERSION is True):
    print("Minimal MQTTClient")
    from micropython_mqtt_as.mqtt_as_minimal import MQTTClient, Lock
else:
    print("Full MQTTClient")
    from micropython_mqtt_as.mqtt_as import MQTTClient, Lock
gc.collect()
import uasyncio as asyncio
import os
import sys

_log = logging.getLogger("MQTT")
gc.collect()


class MQTTHandler(MQTTClient):
    def __init__(self, receive_config=False):
        """
        receive_config: False, if true tries to get the configuration of components
            from a server connected to the mqtt broker
        allow_wildcards: True, if false no subscriptions ending with "/#" are allowed;
            this also saves RAM as the module "subscription" is used as a backend 
            to store subscriptions instead of the module "tree" which is bigger
        """
        if platform == "esp8266" and sys_vars.hasFilesystem():
            """ esp8266 has very limited RAM so choosing a module that writes subscribed topics 
            to a file if filesystem is enabled, else uses Subscription module.
            - less feature and less general
            + specifically made for mqtt and esp8266
            - makes it a lot slower (~30ms checking a subscription, ~120ms saving one)
            + saves at least 1kB with a few subscriptions
            """
            from pysmartnode.utils.subscriptionHandlers.subscribe_file import SubscriptionHandler
        else:
            """ 
            For esp32 and esp8266 with no filesystem (which saves ~6kB) Subscription module is used
            """
            from pysmartnode.utils.subscriptionHandlers.subscription import SubscriptionHandler
        gc.collect()
        self._subscriptions = SubscriptionHandler()
        self.payload_on = ("ON", True, "True")
        self.payload_off = ("OFF", False, "False")
        self._retained = []
        self.id = config.id
        self.mqtt_home = config.MQTT_HOME
        super().__init__(server=config.MQTT_HOST,
                         port=1883,
                         user=config.MQTT_USER,
                         password=config.MQTT_PASSWORD,
                         keepalive=config.MQTT_KEEPALIVE,
                         subs_cb=self._execute_sync,
                         wifi_coro=self._wifiChanged,
                         connect_coro=self._connected,
                         will=(self.getRealTopic(self.getDeviceTopic("status")), "OFFLINE", True, 1),
                         clean=False,
                         ssid=config.WIFI_SSID,
                         wifi_pw=config.WIFI_PASSPHRASE)
        asyncio.get_event_loop().create_task(self.connect())
        self.__receive_config = receive_config
        # True=receive config, None=config received
        self._awaiting_config = False

    async def _wifiChanged(self, state):
        if config.DEBUG:
            _log.info("WIFI state {!s}".format(state), local_only=True)

    async def _connected(self, client):
        await self._publishDeviceStats()
        await self._subscribeTopics()
        if self.__receive_config is True:
            asyncio.get_event_loop().create_task(self._receiveConfig())

    async def _receiveConfig(self):
        self.__receive_config = None
        while True:
            gc.collect()
            _log.debug("RAM before receiveConfig import: {!s}".format(gc.mem_free()), local_only=True)
            import pysmartnode.networking.mqtt_receive_config
            gc.collect()
            _log.debug("RAM after receiveConfig import: {!s}".format(gc.mem_free()), local_only=True)
            result = await pysmartnode.networking.mqtt_receive_config.requestConfig(config, self,
                                                                                    _log)
            if result is False:
                _log.info("Using local components.json/py", local_only=True)
                gc.collect()
                _log.debug("RAM before receiveConfig deletion: {!s}".format(gc.mem_free()), local_only=True)
                del pysmartnode.networking.mqtt_receive_config
                del sys.modules["pysmartnode.networking.mqtt_receive_config"]
                gc.collect()
                _log.debug("RAM after receiveConfig deletion: {!s}".format(gc.mem_free()))
                local_works = await config.loadComponentsFile()
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
                        loop.create_task(config.loadComponentsFile())
                    else:
                        loop.create_task(config.registerComponentsAsync(result))
                else:
                    # on esp32 components are registered directly but async to let logs run between registrations
                    loop.create_task(config.registerComponentsAsync(result))
                return True
            await asyncio.sleep(60)  # if connection not stable or broker unreachable, try again in 60s

    async def _subscribeTopics(self):
        for obj, topic in self._subscriptions.__iter__(with_path=True):
            await super().subscribe(topic, qos=1)

    def _convertToDeviceTopic(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.id)):
            return topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.id), ".")
        raise TypeError("Topic is not a device subscription: {!s}".format(topic))

    def _isDeviceSubscription(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.id)):
            return True
        return False

    async def unsubscribe(self, topic, callback=None):
        # if self._isDeviceTopic(topic):
        #    topic = self.getRealTopic(topic)
        if callback is None:
            _log.debug("unsubscribing topic {}".format(topic), local_only=True)
            self._subscriptions.removeObject(topic)
            _log.warn(
                "MQTT backend does not support unsubscribe, but function won't be called anymore", local_only=True)
            # mqtt library has no unsubscribe function but it is removed from subscriptions
        else:
            try:
                cbs = self._subscriptions.getFunctions(topic)
                if type(cbs) not in (tuple, list):
                    self._subscriptions.removeObject(topic)
                    return
                try:
                    cbs = list(cbs)
                    cbs.remove(callback)
                except ValueError:
                    _log.warn("Callback to topic {!s} not subscribed".format(topic), local_only=True)
                    return
                self._subscriptions.setFunctions(topic, cbs)
            except ValueError:
                _log.warn("Topic {!s} does not exist".format(topic))

    def scheduleSubscribe(self, topic, callback_coro, qos=0, check_retained=True):
        asyncio.get_event_loop().create_task(self.subscribe(topic, callback_coro, qos, check_retained))

    async def subscribe(self, topic, callback_coro, qos=0, check_retained=True):
        # if self._isDeviceTopic(topic):
        #    topic = self.getRealTopic(topic)
        _log.debug("Subscribing to topic {}".format(topic), local_only=True)
        loop = asyncio.get_event_loop()
        self._subscriptions.addObject(topic, callback_coro)
        if check_retained:
            if topic.endswith("/set"):
                # subscribe to topic without /set to get retained message for this topic state
                # this is done additionally to the retained topic with /set in order to recreate
                # the current state and then get new instructions in /set
                state_topic = topic[:-4]
                self._retained.append(state_topic)
                self._subscriptions.addObject(state_topic, callback_coro)
                state_topic_new = state_topic
                if self._isDeviceSubscription(state_topic):
                    state_topic_new = self._convertToDeviceTopic(state_topic)
                if self._isDeviceTopic(state_topic):
                    state_topic_new = self.getRealTopic(state_topic)
                await super().subscribe(state_topic_new, qos)
                await self._await_retained(state_topic, callback_coro, True)
                # to give retained state time to process before adding /set subscription
            self._retained.append(topic)
        topic_new = topic
        if self._isDeviceSubscription(topic):
            topic_new = self._convertToDeviceTopic(topic)
        if self._isDeviceTopic(topic):
            topic_new = self.getRealTopic(topic)
        await super().subscribe(topic_new, qos)
        if check_retained:
            loop.create_task(self._await_retained(topic, callback_coro))
            # TODO: optimize this to prevent coro spam on controller reset when all components subscribe topics

    async def _publishDeviceStats(self):
        await self.publish(self.getDeviceTopic("version"), config.VERSION, True, 1)
        await self.publish(self.getDeviceTopic("status"), "ONLINE", True, 1)
        if self.__receive_config is not None:
            # only log on first connection, not on reconnect as nothing has changed here
            if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
                t = time.localtime()
                await self.publish(self.getDeviceTopic("last_boot"),
                                   "{} {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format("GMT", t[0], t[1], t[2], t[3],
                                                                                     t[4],
                                                                                     t[5]), True, 1)
                _log.info(str(os.uname()))
                _log.info("Client version: {!s}".format(config.VERSION))
        else:
            _log.debug("Reconnected")

    def getDeviceTopic(self, attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return ".{}".format(attrib)

    def _isDeviceTopic(self, topic):
        return topic.startswith(".")

    def getRealTopic(self, device_topic):
        if device_topic.startswith(".") is False:
            raise ValueError("Topic {!s} is no device topic".format(device_topic))
        return "{}/{}/{}".format(self.mqtt_home, self.id, device_topic[1:])

    async def _await_retained(self, topic, cb=None, remove_after=False):
        st = 0
        while topic in self._retained and st <= 8:
            await asyncio.sleep_ms(250)
            st += 1
        try:
            _log.debug("removing retained topic {}".format(topic), local_only=True)
            self._retained.remove(topic)
        except ValueError:
            pass
        if remove_after:
            await self.unsubscribe(topic, cb)

    def _execute_sync(self, topic, msg):
        """mqtt library only handles sync callbacks so add it to asyncio loop"""
        asyncio.get_event_loop().create_task(self._execute(topic, msg))

    async def _execute(self, topic, msg):
        _log.debug("mqtt execution: {!s} {!s}".format(topic, msg), local_only=True)
        topic = topic.decode()
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.id)):
            topic = topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.id), ".")
        msg = msg.decode()
        try:
            msg = json.loads(msg)
        except:
            pass  # maybe not a json string, no way of knowing
        cb = None
        retain = False
        _subscriptions = self._subscriptions
        _retained = self._retained
        if topic in _retained:
            retain = True
        else:
            for topicR in _retained:
                if topicR.endswith("#") and _subscriptions.matchesSubscription(topic, topicR):
                    retain = True
                gc.collect()
        if retain:
            try:
                cb = _subscriptions.getFunctions(topic + "/set")
            except IndexError:
                try:
                    cb = _subscriptions.getFunctions(topic)
                except IndexError:
                    pass
        if cb is None:
            try:
                cb = _subscriptions.getFunctions(topic)
            except IndexError:
                _log.warn("No callback found for topic {!s}".format(topic))
        if cb:
            for callback in cb if (type(cb) == list or type(cb) == tuple) else [cb]:
                try:
                    res = await callback(topic=topic, msg=msg, retain=retain)
                    if not retain:
                        if res is not None and res is not False:
                            if res is True:
                                res = msg
                                # send original msg back
                            if topic.endswith("/set"):
                                # if a /set topic is found, send without /set, this is always retained
                                await self.publish(topic[:-4], res, retain=True)
                except Exception as e:
                    _log.error("Error executing {!s}mqtt topic {!r}: {!s}".format(
                        "retained " if retain else "", topic, e))
            if retain and topic.endswith("/#") is False:
                # only remove if it is not a wildcard topic to allow other topics
                # to handle retained messages belonging to this wildcard
                try:
                    _retained.remove(topic)
                except ValueError:
                    pass
                    # already removed by _await_retained while executing topic

    async def publish(self, topic, msg, retain=False, qos=0):
        if type(msg) == dict or type(msg) == list:
            msg = json.dumps(msg)
        elif type(msg) != str:
            msg = str(msg)
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        gc.collect()
        await super().publish(topic.encode(), msg.encode(), retain, qos)

    def schedulePublish(self, topic, msg, retain=False, qos=0):
        asyncio.get_event_loop().create_task(self.publish(topic, msg, retain, qos))
