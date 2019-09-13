'''
Created on 17.02.2018

@author: Kevin Köck
'''

__updated__ = "2019-09-12"
__version__ = "4.1"

import gc
import ujson
import time

gc.collect()

from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars
from pysmartnode.utils.event import Event
from micropython import const
from micropython_mqtt_as.mqtt_as import MQTTClient, Lock
import uasyncio as asyncio
import os
import sys

gc.collect()

_log = logging.getLogger("MQTT")
gc.collect()

type_gen = type((lambda: (yield))())  # Generator type
_DEFAULT_TIMEOUT = const(2635200)  # 1 month, basically math.huge


class MQTTHandler(MQTTClient):
    def __init__(self, receive_config=False):
        """
        receive_config: False, if true tries to get the configuration of components
            from a server connected to the mqtt broker
        allow_wildcards: True, if false no subscriptions ending with "/#" are allowed;
            this also saves RAM as the module "subscription" is used as a backend 
            to store subscriptions instead of the module "tree" which is bigger
        """
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
                         will=(self.getRealTopic(self.getDeviceTopic("status")), "offline", True, 1),
                         clean=False,
                         ssid=config.WIFI_SSID,
                         wifi_pw=config.WIFI_PASSPHRASE)
        asyncio.get_event_loop().create_task(self._connectCaller())
        self.__receive_config = receive_config
        # True=receive config, None=config received
        self._awaiting_config = False
        self._temp = []  # temporary storage for retained state topics
        self._connected_coro = None
        self._reconnected_subs = []
        self._wifi_coro = None
        self._wifi_subs = []
        self._queue = Event()
        asyncio.get_event_loop().create_task(self._processor())
        gc.collect()

    def registerWifiCallback(self, cb):
        """Supports callbacks and coroutines. Will get canceled if Wifi changes during execution"""
        self._wifi_subs.append(cb)

    def registerConnectedCallback(self, cb):
        """Supports callbacks and coroutines. Will get canceled if connection changes during execution"""
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
                # not connected after trying.. not much we can do without a connection except trying again.
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
            asyncio.cancel(self._connected_coro)  # processed subscriptions would have to be done again anyway
        self._connected_coro = self._connected_handler(client)
        asyncio.get_event_loop().create_task(self._connected_coro)

    async def _connected_handler(self, client):
        await self.publish(self.getDeviceTopic("status"), "online", 1, True)
        # if it hangs here because connection is lost, it will get canceled when reconnected.
        if self.__receive_config is not None:
            # only log on first connection, not on reconnect as nothing has changed here
            await _log.asyncLog("info", str(os.name if platform == "linux" else os.uname()))
            await _log.asyncLog("info", "Client version: {!s}".format(config.VERSION))
        if self.__receive_config is None:
            # do not try to resubscribe on first connect as components will do it
            await _log.asyncLog("debug", "Reconnected")
            await self._subscribeTopics()
        if self.__receive_config is True:
            asyncio.get_event_loop().create_task(self._receiveConfig())
        else:
            self.__receive_config = None  # first connect processed
        for cb in self._reconnected_subs:
            res = cb(client)
            if type(res) == type_gen:
                await res
        self._connected_coro = None

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
                result = ujson.loads(result)
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

    def _convertToDeviceTopic(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.client_id), ".")
        raise TypeError("Topic is not a device subscription: {!s}".format(topic))

    def _isDeviceSubscription(self, topic):
        if topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id)):
            return True
        return False

    @staticmethod
    def matchesSubscription(topic, subscription, ignore_command=False):
        if topic == subscription:
            return True
        atopic = bytearray(topic)
        asubscription = bytearray(subscription)
        if ignore_command is True and subscription.endswith("/set"):
            if atopic == memoryview(asubscription)[:-4]:
                return True
        if subscription.endswith("/#"):
            lens = len(asubscription)
            if memoryview(atopic)[:lens - 2] == memoryview(asubscription)[:-2]:
                if len(atopic) == lens - 2 or memoryview(atopic)[lens - 2:lens - 1] == b"/":
                    # check if identifier matches subscription or has sublevel
                    # (home/test/# does not listen to home/testing but to home/test)
                    return True
        pl = subscription.find("/+/")
        if pl != -1:
            st = topic.find("/", pl + 1) + 1
            if memoryview(asubscription)[:pl + 1] == memoryview(atopic)[:pl + 1]:
                if ignore_command is True:
                    if memoryview(asubscription)[-5:] == b"+/set" and st == 0:  # st==0 no subtopics
                        return True
                    elif memoryview(asubscription)[-4:] == b"/set":
                        ed = len(asubscription) - 4
                    else:
                        ed = len(asubscription)
                else:
                    ed = len(asubscription)
                if memoryview(asubscription)[pl + 3:ed] == memoryview(atopic)[st:]:
                    return True
            return False
        return False

    def scheduleUnsubscribe(self, topic=None, component=None, timeout=_DEFAULT_TIMEOUT, wait_for_wifi=True):
        asyncio.get_event_loop().create_task(self.unsubscribe(topic, component, timeout, wait_for_wifi))

    async def unsubscribe(self, topic=None, component=None, timeout=_DEFAULT_TIMEOUT, wait_for_wifi=True):
        if topic is None and component is None:
            raise TypeError("No topic and no component, can't unsubscribe")
        _log.debug("unsubscribing topic {!s} from component {}".format(topic, component), local_only=True)
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
                            if component is None:  # if no component specified, unsubscribe topic from every component
                                if tc == t:
                                    del c._topics[t]
                                    break
                            if self.isDeviceTopic(tc):
                                tc = self.getRealTopic(tc)
                                if self.matchesSubscription(
                                        t if self.isDeviceTopic(t) is False else self.getRealTopic(t), tc) is True:
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
                if wait_for_wifi is False and self.isconnected() is False:
                    continue
                timeout = timeout - (time.ticks_ms() - st) / 1000  # the whole process can't take longer than timeout.
                if await self._preprocessor(super().unsubscribe, (t,), timeout) is False:
                    _log.error("Couldn't unsubscribe topic {!s} from broker".format(t), local_only=True)
                st = time.ticks_ms()
        return True  # always True because at least internally it has been unsubscribed.

    def scheduleSubscribe(self, topic, qos=0, check_retained_state_topic=True, timeout=_DEFAULT_TIMEOUT,
                          wait_for_wifi=True):
        asyncio.get_event_loop().create_task(
            self.subscribe(topic, qos, check_retained_state_topic, timeout, wait_for_wifi))

    async def subscribe(self, topic, qos=1, check_retained_state_topic=True, timeout=_DEFAULT_TIMEOUT,
                        wait_for_wifi=True):
        _log.debug("Subscribing to topic {}".format(topic), local_only=True)
        if wait_for_wifi is False and self.isconnected() is False:
            return False
        if check_retained_state_topic:
            if topic.endswith("/set"):
                # subscribe to topic without /set to get retained message for this topic state
                # this is done additionally to the retained topic with /set in order to recreate
                # the current state and then get new instructions in /set
                state_topic = topic[:-4]
                self._temp.append(state_topic)
                state_topic_new = state_topic
                if self._isDeviceSubscription(state_topic):
                    state_topic_new = self._convertToDeviceTopic(state_topic)
                if self.isDeviceTopic(state_topic):
                    state_topic_new = self.getRealTopic(state_topic)
                st = time.ticks_ms()
                if await self._preprocessor(super().subscribe, (state_topic_new, qos), timeout) is False:
                    return False
                await asyncio.sleep_ms(500)
                # gives retained state topic time to be received and processed before
                # unsubscribing and adding /set subscription
                timeout = timeout - (time.ticks_ms() - st) / 1000  # the whole process can't take longer than timeout.
                st = time.ticks_ms()
                await self.unsubscribe(state_topic, None, timeout)
                if state_topic in self._temp:
                    self._temp.remove(state_topic)
                timeout = timeout - (time.ticks_ms() - st) / 1000
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        return await self._preprocessor(super().subscribe, (topic, qos), timeout)

    @staticmethod
    def getDeviceTopic(attrib, is_request=False):
        if is_request:
            attrib += "/set"
        return ".{}".format(attrib)

    @staticmethod
    def isDeviceTopic(topic):
        return topic.startswith(".")

    def getRealTopic(self, device_topic):
        if device_topic.startswith(".") is False:
            raise ValueError("Topic {!s} is no device topic".format(device_topic))
        return "{}/{}/{}".format(self.mqtt_home, self.client_id, device_topic[1:])

    def _execute_sync(self, topic, msg, retained):
        _log.debug("mqtt execution: {!s} {!s} {!s}".format(topic, msg, retained), local_only=True)
        topic = topic.decode()
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        msg = msg.decode()
        try:
            msg = ujson.loads(msg)
        except ValueError:
            pass  # maybe not a json string, no way of knowing
        if topic in self._temp and retained is True:  # checking retained state topic
            topic_subs = topic + "/set"
        else:
            topic_subs = topic
        c = config._components
        loop = asyncio.get_event_loop()
        found = False
        while c is not None:
            if hasattr(c, "_topics") is True:
                t = c._topics  # _topics is dict
                for tt in t:
                    if self.matchesSubscription(topic_subs, tt) is True:
                        loop.create_task(self._execute_callback(t[tt], topic, msg, retained))
                        _log.debug("execute_callback {!s} {!s} {!s}".format(t[tt], topic, msg), local_only=True)
                        found = True
            c = c._next_component
        if found is False:
            _log.warn("Subscribed topic {!s} not found, unsubscribing from server".format(topic))
            self.scheduleUnsubscribe(topic, timeout=10, wait_for_wifi=False)
            # unsubscribe to prevent it from spamming. Could also be still subscribed because unsubscribe timeout out.

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
            _log.error("Error executing {!s}mqtt topic {!r}: {!s}".format("retained " if retained else "", topic, e))

    async def publish(self, topic, msg, qos=0, retain=False, timeout=_DEFAULT_TIMEOUT, wait_for_wifi=True):
        """
        publish a message to mqtt
        :param topic: str
        :param msg: json convertable object
        :param qos: 0 or 1
        :param retain: bool
        :param timeout: seconds, after timeout False will be returned and publish canceled. defaults to 1mo (math.huge)
        :param wait_for_wifi: wait for wifi to be available.
        Depending on application this might not be desired as it could block further processing but
        due to restraint resources and complexity you don't want to launch a new coroutine for each publish.
        :return:
        """
        if wait_for_wifi is False and self.isconnected() is False:
            return False
        if type(msg) == dict or type(msg) == list:
            msg = ujson.dumps(msg)
        elif type(msg) != str:
            msg = str(msg)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        msg = (topic.encode(), msg.encode(), retain, qos)
        gc.collect()
        return await self._preprocessor(super().publish, msg, timeout)

    def schedulePublish(self, topic, msg, qos=0, retain=False, timeout=_DEFAULT_TIMEOUT, wait_for_wifi=True):
        asyncio.get_event_loop().create_task(self.publish(topic, msg, qos, retain, timeout, wait_for_wifi))

    async def _preprocessor(self, coro, msg, timeout):
        st = time.ticks_ms()
        qd = False
        while time.ticks_ms() - st < timeout * 1000:
            if qd is False:
                if self._queue.is_set() is False:
                    self._queue.set((coro, msg))
                    qd = True
            else:
                if self._queue.is_set() is False or self._queue.value()[1] != msg:
                    return True  # processed correctly
            await asyncio.sleep_ms(20)
        return False  # message might still go through eventually if already in processing

    async def _processor(self):
        while True:
            await self._queue
            coro, args = self._queue.value()
            try:
                await coro(*args)
            except Exception as e:
                await _log.asyncLog("error", e)
            finally:
                self._queue.clear()
            # not working with asyncio.cancel here because cancelling a publish could break it in the middle
            # of sending or receiving data which could lead to various problems.
            # Therefore a cancelled task might still go through as cancellation only really works as long as
            # a different request is being processed.
            # However if a timeout is used then the calling method will not expect it to have been gone through
            # and can act accordingly.
