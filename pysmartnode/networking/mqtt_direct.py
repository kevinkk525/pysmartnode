'''
Created on 17.02.2018

@author: Kevin Köck
'''

__updated__ = "2019-10-20"
__version__ = "5.0"

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
        self._subs = []
        self._sub_coro = None
        self._sub_retained = False
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
                             self.getRealTopic(
                                 self.getDeviceTopic(config.MQTT_AVAILABILITY_SUBTOPIC)),
                             "offline", True, 1),
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
        self.__last_disconnect = None
        self.__downtime = 0
        self.__reconnects = -1  # not counting the first connect
        gc.collect()

    def close(self):
        # subclassing close because mqtt_as doesn't provide a callback when connection
        # to mqtt broker is lost, only when wifi connection is lost.
        if self.__last_disconnect is None:
            self.__last_disconnect = time.ticks_ms()
        super().close()

    def getDowntime(self):
        if self.isconnected() or self.__last_disconnect is None:
            return self.__downtime
        else:
            return (time.ticks_ms() - self.__last_disconnect) / 1000 + self.__downtime

    def getReconnects(self):
        return self.__reconnects if self.__reconnects > 0 else 0

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
                _log.error("Error connecting to wifi or mqtt: {!s}".format(e), local_only=True)
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
        self.__reconnects += 1
        if self.__last_disconnect is not None:
            self.__downtime += (time.ticks_ms() - self.__last_disconnect) / 1000
        self.__last_disconnect = None
        if self._connected_coro is not None:
            # processed subscriptions would have to be done again anyway
            asyncio.cancel(self._connected_coro)
        self._connected_coro = self._connected_handler(client)
        asyncio.get_event_loop().create_task(self._connected_coro)

    async def _connected_handler(self, client):
        try:
            await self.publish(self.getDeviceTopic(config.MQTT_AVAILABILITY_SUBTOPIC), "online",
                               qos=1, retain=True)
            # if it hangs here because connection is lost, it will get canceled when reconnected.
            if self.__first_connect is True:
                # only log on first connection, not on reconnect as nothing has changed here
                await _log.asyncLog("info", str(os.name if platform == "linux" else os.uname()))
                await _log.asyncLog("info", "Client version: {!s}".format(config.VERSION))
                self.__first_connect = False
            elif self.__first_connect is False:
                # do not try to resubscribe on first connect as components will do it
                await _log.asyncLog("debug", "Reconnected")
                if self._sub_coro is not None:
                    asyncio.cancel(self._sub_coro)
                self._sub_coro = self._subscribeTopics()
                asyncio.get_event_loop().create_task(self._sub_coro)
            for cb in self._reconnected_subs:
                res = cb(client)
                if type(res) == type_gen:
                    await res
            self._connected_coro = None
        except asyncio.CancelledError:
            raise  # in case the calling function need to handle Cancellation too
        finally:
            if self._sub_coro is not None:
                asyncio.cancel(self._sub_coro)

    async def _subscribeTopics(self, start: int = 0):
        _log.debug("_subscribeTopics, start {!s}".format(start))
        for i in range(start, len(self._subs)):
            if len(self._subs) <= i:
                # entries got unsubscribed
                self._sub_coro = None
                return
            t = self._subs[i][0]
            if self.isDeviceTopic(t):
                t = self.getRealTopic(t)
            if len(self._subs[i]) == 4:  # requested retained state topic
                sub = self._subs[i]
                ts = time.ticks_ms()
                self._sub_retained = True
                _log.debug("_subscribing {!s}".format(t[:-4]))
                await self._preprocessor(super().subscribe, (t[:-4], 1))  # subscribe state topic
                while time.ticks_diff(time.ticks_ms(), ts) < 2000 and self._sub_retained:
                    # wait 2 seconds for answer
                    await asyncio.sleep_ms(100)
                if self._sub_retained is True:  # no state message received
                    self._subs[self._subs.index(sub)] = sub[:3]
                    self._sub_retained = False
                    # using _subs.index because index could have changed if unsubscribe happened
                    # while waiting for retained state message or unsubcribing
                    await self._preprocessor(super().unsubscribe, (t[:-4],),
                                             await_connection=False)
                # no timeouts because _subscribeTopics will get canceled when connection is lost
            _log.debug("_subscribing {!s}".format(t))
            await self._preprocessor(super().subscribe, (t, 1), await_connection=False)
        self._sub_coro = None

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
            if memoryview(subscription)[:pl + 1] == memoryview(topic)[:pl + 1]:  # equal until /+
                if subscription.endswith("/#"):
                    sub = subscription.replace("/+/", topic[pl:topic.find("/", pl + 1) + 1])
                    return MQTTHandler.matchesSubscription(topic, sub, ignore_command)
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

    def scheduleUnsubscribe(self, topic=None, component=None):
        asyncio.get_event_loop().create_task(self.unsubscribe(topic, component))

    async def unsubscribe(self, topic=None, component=None):
        """
        Unsubscribe a topic internally and from broker.
        :param topic: str
        :param component: optional
        subscribed topic is lost too so unsubscribe is not needed anymore
        :return:
        """
        if topic is None and component is None:
            raise TypeError("No topic and no component, can't unsubscribe")
        if topic is not None and self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        _log.debug("unsubscribing topic {!s} from component {}".format(topic, component),
                   local_only=True)
        found = False
        for sub in self._subs:
            if topic is None and sub[2] == component:
                self._subs.remove(sub)
                if not await self._preprocessor(super().unsubscribe, (self.getRealTopic(sub[0]),),
                                                await_connection=False):
                    _log.error("Error unsubscribing {!s} {!s}".format(sub[0], sub[2]),
                               local_only=True)
                found = True
            elif sub[0] == topic and (component is None or component == sub[2]):
                self._subs.remove(sub)
                if not await self._preprocessor(super().unsubscribe, (self.getRealTopic(topic),),
                                                await_connection=False):
                    _log.error("Error unsubscribing {!s} {!s}".format(sub[0], sub[2]),
                               local_only=True)
                found = True
                if component == sub[2]:
                    return True  # there should only be one topic sub for a specific component
        if found is False:
            _log.error(
                "Can't unsubscribe, topic not found: {!s}, comp {!s}".format(topic, component),
                local_only=True)
        return True

    def subscribe(self, topic, cb, component=None, qos=1, check_retained_state=False):
        _log.debug(
            "Subscribing to topic {} for component {!s}, checking retained {!s}".format(topic,
                                                                                        component,
                                                                                        check_retained_state),
            local_only=True)
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        if check_retained_state is True and topic.endswith("/set"):
            sub = (topic, cb, component, True)
        else:
            sub = (topic, cb, component)
        self._subs.append(sub)
        if self._sub_coro is None:
            self._sub_coro = self._subscribeTopics(self._subs.index(sub))
            asyncio.get_event_loop().create_task(self._sub_coro)

    async def awaitSubscriptionsDone(self, timeout=None, await_connection=True):
        start = time.ticks_ms()
        while timeout is None or time.ticks_diff(time.ticks_ms(), start) < timeout * 1000:
            if await_connection is False and self._isconnected is False:
                return False
            if self._sub_coro is None:
                # all topics subscribed.
                return True
            await asyncio.sleep_ms(50)
        # timeout
        return False

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
            # raise ValueError("Topic {!s} is no device topic".format(device_topic))
            return device_topic  # no need to raise an error
        return "{}/{}/{}".format(self.mqtt_home, self.client_id, device_topic[2:])

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
        loop = asyncio.get_event_loop()
        found = False
        for sub in self._subs:
            if self.matchesSubscription(topic, sub[0], ignore_command=len(sub) == 4):
                loop.create_task(self._execute_callback(sub, topic, msg, retained))
                _log.debug(
                    "execute_callback of comp {!s}: {!s} {!s}".format(sub[2], topic, msg),
                    local_only=True)
                found = True
        if found is False:
            _log.warn("Subscribed topic {!s} not found, should solve itself".format(topic),
                      local_only=True)

    async def _execute_callback(self, sub, topic, msg, retained):
        if len(sub) == 4 and sub[0].find("/+/") == -1:
            # retained state topic received without wildcards (could receive multiple states)
            self._subs[self._subs.index(sub)] = sub[:3]
            self._sub_retained = False
            if self.isDeviceTopic(sub[0]):
                t = self.getRealTopic(sub[0])[:-4]
            else:
                t = sub[0][:-4]
            await self._preprocessor(super().unsubscribe, (t,), await_connection=False)
            del t
            gc.collect()
            # unsubscribing before executing to prevent callback to publish to state topic
            if not retained:
                _log.error(
                    "Received non retained message when checking retained state topic {!s}, ignoring message".format(
                        topic),
                    local_only=True)
                return
        try:
            res = sub[1](topic, msg, retained)
            if type(res) == type_gen:
                res = await res
            if not retained and topic.endswith("/set"):
                # if a /set topic is found, send without /set, this is always retained:
                if res:  # Could be any return value
                    if res is True:
                        res = msg
                        # send original msg back
                    await self.publish(topic[:-4], res, qos=1, retain=True)
        except Exception as e:
            await _log.asyncLog("error",
                                "Error executing {!s}mqtt topic {!r}: {!s}".format(
                                    "retained " if retained else "", topic, e))

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

    def schedulePublish(self, topic, msg, retain=False, qos=0, timeout=None,
                        await_connection=True):
        asyncio.get_event_loop().create_task(
            self.publish(topic, msg, retain, qos, timeout, await_connection))

    # Await broker connection. Subclassed to reduce canceling time from 1s to 50ms
    async def _connection(self):
        while not self._isconnected:
            await asyncio.sleep_ms(50)

    async def _operationTimeout(self, coro, args):
        try:
            await coro(*args)
        except asyncio.CancelledError:
            raise  # in case the calling function need to handle Cancellation too
        finally:
            self._pub_coro = None

    async def _preprocessor(self, coroutine, args, timeout=None, await_connection=False):
        coro = None
        start = time.ticks_ms()
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
                        return True  # published
                await asyncio.sleep_ms(20)
        except asyncio.CancelledError:
            raise  # in case the calling function need to handle Cancellation too
        finally:
            if coro is not None and self._pub_coro == coro:
                async with self.lock:
                    asyncio.cancel(coro)
                return False
        return False
