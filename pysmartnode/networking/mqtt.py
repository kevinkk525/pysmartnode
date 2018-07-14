'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "1.6"
__updated__ = "2018-06-24"

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

log = logging.getLogger("MQTT")
gc.collect()


class MQTTHandler(MQTTClient):
    def __init__(self, receive_config=False, allow_wildcards=True):
        """
        receive_config: False, if true tries to get the configuration of components
            from a server connected to the mqtt broker
        allow_wildcards: True, if false no subscriptions ending with "/#" are allowed;
            this also saves RAM as the module "subscription" is used as a backend 
            to store subscriptions instead of the module "tree" which is bigger
        """
        if platform == "esp8266" and sys_vars.hasFilesystem():
            """ esp8266 has very limited RAM so choosing a module that allows wildcards
            but writes subscribed topics to a file if filesystem is enabled, else uses Tree.
            - less feature and less general
            + specifically made for mqtt and esp8266
            - makes it a lot slower (~30ms checking a subscription, ~120ms saving one)
            + saves at least 1kB with a few subscriptions
            """
            from pysmartnode.utils.subscriptionHandlers.subscribe_file import SubscriptionHandler
            self._subscriptions = SubscriptionHandler()
        else:
            """ 
            esp32 has a lot of RAM but if wildcards are not needed then
            the subscription module is faster and saves ram but does not support wildcards.
            For wildcard support the module tree is used.
            Also used for esp8266 with no filesystem (which saves ~6kB)
            """
            if allow_wildcards:
                from pysmartnode.utils.subscriptionHandlers.tree import Tree
                gc.collect()
                self._subscriptions = Tree(config.MQTT_HOME, ["Functions"])
            else:
                from pysmartnode.utils.subscriptionHandlers.subscription import SubscriptionHandler
                gc.collect()
                self._subscriptions = SubscriptionHandler(["Functions"])
        self._allow_wildcards = allow_wildcards
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

    async def _wifiChanged(self, state):
        if config.DEBUG:
            log.info("WIFI state {!s}".format(state), local_only=True)

    async def _connected(self, client):
        await self._publishDeviceStats()
        await self._subscribeTopics()
        if self.__receive_config:
            log.info("Recveiving config", local_only=True)
            await self.subscribe("{!s}/login/{!s}".format(self.mqtt_home, self.id), self._buildComponents, qos=1,
                                 check_retained=False)
            log.debug("waiting for config", local_only=True)
            await self.publish("{!s}/login/{!s}/set".format(self.mqtt_home, self.id), config.VERSION, qos=1)
            t = time.ticks_ms()
            while (time.ticks_ms() - t) < 10000:
                if self.__receive_config is not None:
                    await asyncio.sleep_ms(200)
                else:
                    break
            if self.__receive_config is not None:
                log.error("No configuration received, falling back to local config")
                asyncio.get_event_loop().create_task(config.loadComponentsFile())
        elif self.__receive_config is not None:
            self.__receive_config = None  # None says that first run is complete
            log.info("Using local components.json/py", local_only=True)
            asyncio.get_event_loop().create_task(config.loadComponentsFile())

    async def _buildComponents(self, topic=None, msg=None, retain=None):
        log.debug("Building components", local_only=True)
        loop = asyncio.get_event_loop()
        await self.unsubscribe("{!s}/login/".format(self.mqtt_home) + self.id)
        if type(msg) != dict:
            log.critical("Received config is no dict")
            msg = None
        if msg is None:
            log.error("No configuration received, falling back to last saved config")
            loop.create_task(config.loadComponentsFile())
        else:
            log.info("received config: {!s}".format(msg), local_only=True)
            # saving components
            config.saveComponentsFile(msg)
            if platform == "esp8266":
                # on esp8266 components are split in small files and loaded after each other
                # to keep RAM requirements low, only if filesystem is enabled
                if sys_vars.hasFilesystem():
                    loop.create_task(config.loadComponentsFile())
                else:
                    loop.create_task(config.registerComponentsAsync(msg))
            else:
                # on esp32 components are registered directly but async to let logs run between registrations
                loop.create_task(config.registerComponentsAsync(msg))
        self.__receive_config = None

    async def _subscribeTopics(self):
        for obj, topic in self._subscriptions.__iter__(with_path=True):
            await super().subscribe(topic, qos=1)

    async def unsubscribe(self, topic, callback=None):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        if callback is None:
            log.debug("unsubscribing topic {}".format(topic), local_only=True)
            self._subscriptions.removeObject(topic)
            log.warn(
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
                    log.warn("Callback to topic {!s} not subscribed".format(topic), local_only=True)
                    return
                self._subscriptions.setFunctions(topic, cbs)
            except ValueError:
                log.warn("Topic {!s} does not exist".format(topic))

    def scheduleSubscribe(self, topic, callback_coro, qos=0, check_retained=True):
        asyncio.get_event_loop().create_task(self.subscribe(topic, callback_coro, qos, check_retained))

    async def subscribe(self, topic, callback_coro, qos=0, check_retained=True):
        if self._isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        log.debug("Subscribing to topic {}".format(topic), local_only=True)
        loop = asyncio.get_event_loop()
        if not self._allow_wildcards and topic[-2:] == "/#":
            log.error("Wildcard subscriptions are not allowed, ignoring {!s}".format(topic))
            return False
        self._subscriptions.addObject(topic, callback_coro)
        if check_retained:
            if topic[-4:] == "/set":
                # subscribe to topic without /set to get retained message for this topic state
                # this is done additionally to the retained topic with /set in order to recreate
                # the current state and then get new instructions in /set
                state_topic = topic[:-4]
                self._retained.append(state_topic)
                self._subscriptions.addObject(state_topic, callback_coro)
                await super().subscribe(state_topic, qos)
                await self._await_retained(state_topic, callback_coro, True)
                # to give retained state time to process before adding /set subscription
            self._retained.append(topic)
        await super().subscribe(topic, qos)
        if check_retained:
            loop.create_task(self._await_retained(topic, callback_coro))

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
                log.info(str(os.uname()))
                log.info("Client version: {!s}".format(config.VERSION))
        else:
            log.debug("Reconnected")

    def getDeviceTopic(self, attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return ".{}".format(attrib)

    def _isDeviceTopic(self, topic):
        if topic[:1] == ".":
            return True
        return False

    def getRealTopic(self, device_topic):
        if device_topic[:1] != ".":
            raise ValueError("Topic does not start with .")
        return "{}/{}/{}".format(self.mqtt_home, self.id, device_topic[1:])

    async def _await_retained(self, topic, cb=None, remove_after=False):
        st = 0
        while topic in self._retained and st <= 8:
            await asyncio.sleep_ms(250)
            st += 1
        try:
            log.debug("removing retained topic {}".format(topic), local_only=True)
            self._retained.remove(topic)
        except ValueError:
            pass
        if remove_after:
            await self.unsubscribe(topic, cb)

    def _execute_sync(self, topic, msg):
        """mqtt library only handles sync callbacks so add it to async loop"""
        asyncio.get_event_loop().create_task(self._execute(topic, msg))

    async def _execute(self, topic, msg):
        log.debug("mqtt execution: {!s} {!s}".format(topic, msg), local_only=True)
        topic = topic.decode()
        msg = msg.decode()
        try:
            msg = json.loads(msg)
        except:
            pass  # maybe not a json string, no way of knowing
        cb = None
        retain = False
        if topic in self._retained:
            retain = True
        else:
            for topicR in self._retained:
                if topicR[-1:] == "#":
                    if topic.find(topicR[:-1]) != -1:
                        retain = True
                gc.collect()
        if retain:
            try:
                cb = self._subscriptions.getFunctions(topic + "/set")
                retain = True
            except IndexError:
                try:
                    cb = self._subscriptions.getFunctions(topic)
                    retain = True
                except IndexError:
                    pass
        if cb is None:
            try:
                cb = self._subscriptions.getFunctions(topic)
            except IndexError:
                log.warn("No cb found for topic {!s}".format(topic))
        if cb:
            for callback in cb if (type(cb) == list or type(cb) == tuple) else [cb]:
                try:
                    res = await callback(topic=topic, msg=msg, retain=retain)
                    if not retain:
                        if (type(res) == int and res is not None) or res == True:
                            # so that an integer 0 is interpreted as a result to send back
                            if res == True and type(res) != int:
                                res = msg
                                # send original msg back
                            if topic[-4:] == "/set":
                                # if a /set topic is found, send without /set
                                await self.publish(topic[:-4], res, retain=True)
                except Exception as e:
                    log.error("Error executing {!s} mqtt topic {!r}: {!s}".format(
                        "retained " if retain else "", topic, e))
            if retain and not self._allow_wildcards or topic[-2:] != "/#":
                # only remove if it is not a wildcard topic to allow other topics
                # to handle retained messages belonging to this wildcard
                try:
                    self._retained.remove(topic)
                except ValueError:
                    pass
                    # already removed by _await_retained

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
