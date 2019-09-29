'''
Created on 17.02.2018

@author: Kevin Köck
'''

__updated__ = "2019-09-29"
__version__ = "4.2"

import gc
import ujson
import time

gc.collect()

from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars
from micropython_mqtt_as.mqtt_as import MQTTClient, Lock
import uasyncio as asyncio
import os
from pysmartnode.utils.wrappers.timeit import timeit

gc.collect()

_log = logging.getLogger("MQTT")
gc.collect()

type_gen = type((lambda: (yield))())  # Generator type


class MQTTHandler(MQTTClient):
    def __init__(self):
        self.payload_on = ("ON", True, "True")
        self.payload_off = ("OFF", False, "False")
        self.client_id = sys_vars.getDeviceID()
        self.mqtt_home = config.MQTT_HOME
        super().__init__(client_id=self.client_id,
                         server=config.MQTT_HOST,
                         port=config.MQTT_PORT if hasattr(config, "MQTT_PORT") is True else 1883,
                         user=config.MQTT_USER,
                         password=config.MQTT_PASSWORD,
                         keepalive=config.MQTT_KEEPALIVE,
                         subs_cb=self._execute_sync,
                         wifi_coro=self._wifiChanged,
                         connect_coro=self._connected,
                         will=(
                             self.getRealTopic(self.getDeviceTopic("status")), "offline", True, 1),
                         clean=False,
                         ssid=config.WIFI_SSID,
                         wifi_pw=config.WIFI_PASSPHRASE)
        asyncio.get_event_loop().create_task(self._connectCaller())
        self.__first_connect = True
        self._awaiting_config = False
        self._connected_coro = None
        self._reconnected_subs = []
        self._wifi_coro = None
        self._wifi_subs = []
        self._pub_coro = None
        gc.collect()

    def registerWifiCallback(self, cb):
        """Supports callbacks and coroutines.
        Will get canceled if Wifi changes during execution"""
        self._wifi_subs.append(cb)

    def registerConnectedCallback(self, cb):
        """Supports callbacks and coroutines.
        Will get canceled if connection changes during execution"""
        self._reconnected_subs.append(cb)

    async def _connectCaller(self):
        if platform == "esp8266":
            import network
            ap = network.WLAN(network.AP_IF)
            ap.active(False)
        while True:
            try:
                await self.connect()
                return
            except OSError as e:
                _log.error("Error connecting to wifi: {!s}".format(e), local_only=True)
                # not connected after trying.. not much we can do without a connection except
                # trying again.
                # Don't like resetting the machine as components could be working without wifi.
                await asyncio.sleep(10)
                continue

    async def _wifiChanged(self, state):
        if self._wifi_coro is not None:
            asyncio.cancel(self._wifi_coro)
        self._wifi_coro = self._wifi_changed(state)
        asyncio.get_event_loop().create_task(self._wifi_coro)

    async def _wifi_changed(self, state):
        if config.DEBUG:
            _log.info("WIFI state {!s}".format(state), local_only=True)
        for cb in self._wifi_subs:
            res = cb(self)
            if type(res) == type_gen:
                await res
        self._wifi_coro = None

    async def _connected(self, client):
        if self._connected_coro is not None:
            asyncio.cancel(
                self._connected_coro)  # processed subscriptions would have to be done again anyway
        self._connected_coro = self._connected_handler(client)
        asyncio.get_event_loop().create_task(self._connected_coro)

    async def _connected_handler(self, client):
        await self.publish(self.getDeviceTopic("status"), "online", qos=1, retain=True)
        # if it hangs here because connection is lost, it will get canceled when reconnected.
        if self.__first_connect is True:
            # only log on first connection, not on reconnect as nothing has changed here
            await _log.asyncLog("info", str(os.name if platform == "linux" else os.uname()))
            await _log.asyncLog("info", "Client version: {!s}".format(config.VERSION))
            self.__first_connect = False
        elif self.__first_connect is False:
            # do not try to resubscribe on first connect as components will do it
            await _log.asyncLog("debug", "Reconnected")
            await self._subscribeTopics()
        for cb in self._reconnected_subs:
            res = cb(client)
            if type(res) == type_gen:
                await res
        self._connected_coro = None

    async def _subscribeTopics(self):
        c = config._components
        while c is not None:
            if hasattr(c, "_topics") is True:
                ts = c._topics
                for t in ts:
                    if self.isDeviceTopic(t):
                        t = self.getRealTopic(t)
                    await super().subscribe(t, qos=1)
            if config.MQTT_DISCOVERY_ON_RECONNECT is True and config.MQTT_DISCOVERY_ENABLED is True:
                await c._discovery()
            c = c._next_component
            gc.collect()

    def _convertToDeviceTopic(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.client_id), "./")
        raise TypeError("Topic is not a device subscription: {!s}".format(topic))

    def _isDeviceSubscription(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return True
        return False

    @staticmethod
    def matchesSubscription(topic, subscription, ignore_command=False):
        if topic == subscription:
            return True
        if ignore_command is True and subscription.endswith("/set"):
            if memoryview(topic) == memoryview(subscription)[:-4]:
                return True
        if subscription.endswith("/#") or subscription.endswith("/+"):
            lens = len(subscription)
            if memoryview(topic)[:lens - 2] == memoryview(subscription)[:-2]:
                if subscription.endswith("/#"):
                    if len(topic) == lens - 2 or memoryview(topic)[lens - 2:lens - 1] == b"/":
                        # check if identifier matches subscription or has sublevel
                        # (home/test/# does not listen to home/testing but to home/test)
                        return True
                else:
                    if topic.count("/") == subscription.count("/"):
                        # only the same sublevel matches
                        return True
        pl = subscription.find("/+/")
        if pl != -1:
            st = topic.find("/", pl + 1) + 1
            if memoryview(subscription)[:pl + 1] == memoryview(topic)[:pl + 1]:
                if ignore_command is True:
                    if memoryview(subscription)[-5:] == b"+/set" and st == 0:  # st==0 no subtopics
                        return True
                    elif memoryview(subscription)[-4:] == b"/set":
                        ed = len(subscription) - 4
                    else:
                        ed = len(subscription)
                else:
                    ed = len(subscription)
                if memoryview(subscription)[pl + 3:ed] == memoryview(topic)[st:]:
                    return True
            return False
        return False

    def scheduleUnsubscribe(self, topic=None, component=None, timeout=None, await_connection=True):
        asyncio.get_event_loop().create_task(
            self.unsubscribe(topic, component, timeout, await_connection))

    async def unsubscribe(self, topic=None, component=None, timeout=None, await_connection=False):
        """
        Unsubscribe a topic internally and from broker.
        :param topic: str
        :param component: optional
        :param timeout: in seconds
        :param await_connection: defaults to False because if connection is lost,
        subscribed topic is lost too so unsubscribe is not needed anymore
        :return:
        """
        if topic is None and component is None:
            raise TypeError("No topic and no component, can't unsubscribe")
        _log.debug("unsubscribing topic {!s} from component {}".format(topic, component),
                   local_only=True)
        if component is not None and topic is None:
            topic = component._topics if hasattr(component, "_topics") else [None]
            # removing all topics from component in iteration below
        topic = [topic] if type(topic) == str else topic
        st = time.ticks_ms()
        for t in topic:
            found = False
            c = config._components
            while c is not None:
                if hasattr(c, "_topics") is True:
                    # search if other components subscribed topic
                    # (expensive although typically not needed as every topic is unlikely
                    # to be used by other components too)
                    if c != component:
                        ts = c._topics
                        for tc in ts:
                            if component is None:
                                # if no component specified, unsubscribe topic from every component
                                if tc == t:
                                    del c._topics[t]
                                    break
                            if self.isDeviceTopic(tc):
                                tc = self.getRealTopic(tc)
                                if self.matchesSubscription(
                                        t if self.isDeviceTopic(t) is False else self.getRealTopic(
                                            t), tc) is True:
                                    found = True
                                    break
                    else:  # remove topic from component topic dict
                        if t in c._topics:
                            del c._topics[t]
                c = c._next_component
            if found is False:
                # no component is still subscribed to topic
                if self.isDeviceTopic(t):
                    t = self.getRealTopic(t)
                if await_connection is False and self.isconnected() is False:
                    continue
                if timeout is not None:
                    timeout = timeout - (time.ticks_diff(time.ticks_ms(), st)) / 1000
                    # the whole process can't take longer than timeout.
                if await self._preprocessor(super().unsubscribe, (t,), timeout,
                                            await_connection) is False:
                    _log.error("Couldn't unsubscribe topic {!s} from broker".format(t),
                               local_only=True)
                st = time.ticks_ms()
        return True  # always True because at least internally it has been unsubscribed.

    def scheduleSubscribe(self, topic, qos=0, timeout=None, await_connection=True):
        asyncio.get_event_loop().create_task(self.subscribe(topic, qos, timeout, await_connection))

    async def subscribe(self, topic, qos=1, timeout=None, await_connection=True):
        _log.debug("Subscribing to topic {}".format(topic), local_only=True)
        if await_connection is False and self.isconnected() is False:
            return False
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        return await self._preprocessor(super().subscribe, (topic, qos), timeout, await_connection)

    @staticmethod
    def getDeviceTopic(attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return "./{}".format(attrib)

    @staticmethod
    def isDeviceTopic(topic):
        return topic.startswith("./")

    def getRealTopic(self, device_topic):
        if device_topic.startswith("./") is False:
            raise ValueError("Topic {!s} is no device topic".format(device_topic))
        return "{}/{}/{}".format(self.mqtt_home, self.client_id, device_topic[2:])

    @timeit
    def _execute_sync(self, topic, msg, retained):
        _log.debug("mqtt execution: {!s} {!s} {!s}".format(topic, msg, retained), local_only=True)
        topic = topic.decode()
        msg = msg.decode()
        try:
            msg = ujson.loads(msg)
        except ValueError:
            pass  # maybe not a json string, no way of knowing
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        c = config._components
        loop = asyncio.get_event_loop()
        found = False
        while c is not None:
            if hasattr(c, "_topics") is True:
                t = c._topics  # _topics is dict
                for tt in t:
                    if self.matchesSubscription(topic, tt) is True:
                        loop.create_task(self._execute_callback(t[tt], topic, msg, retained))
                        _log.debug("execute_callback {!s} {!s} {!s}".format(t[tt], topic, msg),
                                   local_only=True)
                        found = True
            c = c._next_component
        if found is False:
            _log.warn("Subscribed topic {!s} not found, unsubscribing from server".format(topic))
            self.scheduleUnsubscribe(topic, timeout=2, await_connection=False)
            # unsubscribe to prevent it from spamming.
            # Could also be still subscribed because unsubscribe timeout out.
            # TODO: better use unsubscribe of MQTTBase

    async def _execute_callback(self, cb, topic, msg, retained):
        try:
            res = cb(topic, msg, retained)
            if type(res) == type_gen:
                res = await res
            if not retained and topic.endswith("/set"):
                # if a /set topic is found, send without /set, this is always retained:
                if res is not None and res is not False:  # Could be any return value
                    if res is True:
                        res = msg
                        # send original msg back
                    await self.publish(topic[:-4], res, qos=1, retain=True)
        except Exception as e:
            await _log.asyncLog("error",
                                "Error executing {!s}mqtt topic {!r}: {!s}".format(
                                    "retained " if retained else "",
                                    topic, e))

    async def publish(self, topic, msg, retain=False, qos=0, timeout=None, await_connection=True):
        """
        publish a message to mqtt
        :param topic: str
        :param msg: json convertable object
        :param retain: bool
        :param qos: 0 or 1
        :param timeout: seconds, after timeout False will be returned and publish canceled.
        :param await_connection: wait for wifi to be available.
        Depending on application this might not be desired as it could block further processing but
        due to restraint resources and complexity you don't want to launch a new coroutine for
        each publish.
        :return:
        """
        if await_connection is False and self.isconnected() is False:
            return False
        if type(msg) == dict or type(msg) == list:
            msg = ujson.dumps(msg)
        elif type(msg) != str:
            msg = str(msg)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        msg = (topic.encode(), msg.encode(), retain, qos)
        gc.collect()
        return await self._preprocessor(super().publish, msg, timeout, await_connection)

    def schedulePublish(self, topic, msg, qos=0, retain=False, timeout=None,
                        await_connection=True):
        asyncio.get_event_loop().create_task(
            self.publish(topic, msg, qos, retain, timeout, await_connection))

    # Await broker connection. Subclassed to reduce canceling time from 1s to 50ms
    async def _connection(self):
        while not self._isconnected:
            await asyncio.sleep_ms(50)

    async def _operationTimeout(self, coro, args):
        print(time.ticks_ms(), "Coro started")
        try:
            await coro(*args)
        except asyncio.CancelledError:
            print(time.ticks_ms(), "Coro Canceled")
        finally:
            print(time.ticks_ms(), "coro done")
            self._pub_coro = None

    async def _preprocessor(self, coroutine, args, timeout=None, await_connection=False):
        coro = None
        start = time.ticks_ms()
        print(time.ticks_ms(), "Operation queued with timeout:", timeout)
        try:
            while timeout is None or time.ticks_diff(time.ticks_ms(), start) < timeout * 1000:
                if await_connection is False and self._isconnected is False:
                    return False
                if self._pub_coro is None and coro is None:
                    coro = self._operationTimeout(coroutine, args)
                    asyncio.get_event_loop().create_task(coro)
                    self._pub_coro = coro
                elif coro is not None:
                    if self._pub_coro != coro:
                        print(time.ticks_ms(), "Coro not equal")
                        return True  # published
                await asyncio.sleep_ms(20)
        except asyncio.CancelledError:
            print("preprocessor got canceled")
        finally:
            if coro is not None and self._pub_coro == coro:
                async with self.lock:
                    asyncio.cancel(coro)
                return False
        print(time.ticks_ms(), "timeout reached")
        return False
