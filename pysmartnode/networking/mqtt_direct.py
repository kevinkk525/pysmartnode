'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "3.7"
__updated__ = "2019-07-02"

import gc
import json

gc.collect()

from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars

if platform == "esp8266" and config.MQTT_MINIMAL_VERSION is True:
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

type_gen = type((lambda: (yield))())  # Generator type


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
                         port=1883,
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
        asyncio.get_event_loop().create_task(self.connect())
        self.__receive_config = receive_config
        # True=receive config, None=config received
        self._awaiting_config = False
        self._temp = []  # temporary storage for retained state topics
        gc.collect()

    @staticmethod
    async def _wifiChanged(state):
        if config.DEBUG:
            _log.info("WIFI state {!s}".format(state), local_only=True)

    async def _connected(self, client):
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
            if hasattr(c, "on_reconnect") is True:
                await c.on_reconnect()
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
        if subscription.endswith("/#"):
            lens = len(subscription)
            if topic[:lens - 2] == subscription[:-2]:
                if len(topic) == lens - 2 or topic[lens - 2] == "/":
                    # check if identifier matches subscription or has sublevel
                    # (home/test/# does not listen to home/testing)
                    return True
        if ignore_command is True and subscription.endswith("/set"):
            if topic == subscription[:-4]:
                return True
        return False

    async def unsubscribe(self, topic=None, component=None):
        if topic is None and component is None:
            raise TypeError("No topic and no component, can't unsubscribe")
        _log.debug("unsubscribing topic {!s} from component {}".format(topic, component), local_only=True)
        if component is not None and topic is None:
            topic = component._topics if hasattr(component, "_topics") else [None]
            # removing all topics from component in iteration below
        topic = [topic] if type(topic) == str else topic
        for t in topic:
            if self.isDeviceTopic(t):
                t = self.getRealTopic(t)
            found = False
            c = config._components
            while c is not None:
                if hasattr(c, "_topics") is True:
                    if c != component:
                        ts = c._topics
                        for tc in ts:
                            if self.isDeviceTopic(tc):
                                tc = self.getRealTopic(tc)
                                if self.matchesSubscription(t, tc) is True:
                                    found = True
                                    break
                    else:  # remove topic from component topic dict
                        del c._topics[t]
                        c._topics = t
                c = c._next_component
            if found is False:
                await super().unsubscribe(t)  # no component is still subscribed to topic

    def scheduleSubscribe(self, topic, qos=0, check_retained_state_topic=True):
        asyncio.get_event_loop().create_task(self.subscribe(topic, qos, check_retained_state_topic))

    async def subscribe(self, topic, qos=1, check_retained_state_topic=True):
        _log.debug("Subscribing to topic {}".format(topic), local_only=True)
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
                await super().subscribe(state_topic_new, qos)
                await asyncio.sleep_ms(500)
                # gives retained state topic time to be received and processed before
                # unsubscribing and adding /set subscription
                await self.unsubscribe(state_topic, None)
                if state_topic in self._temp:
                    self._temp.remove(state_topic)
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        await super().subscribe(topic, qos)

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
            msg = json.loads(msg)
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
            print("execute_sync, c", c)  # DEBUG
            if hasattr(c, "_topics") is True:
                t = c._topics  # _topics is dict
                for tt in t:
                    if self.matchesSubscription(topic_subs, tt) is True:
                        loop.create_task(self._execute_callback(t[tt], topic, msg, retained))
                        _log.debug("execute_callback {!s} {!s} {!s}".format(t[tt], topic, msg), local_only=True)
                        found = True
            c = c._next_component
        if found is False:
            _log.warn("Subscribed topic {!s} not found".format(topic))

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

    async def publish(self, topic, msg, qos=0, retain=False):
        if type(msg) == dict or type(msg) == list:
            msg = json.dumps(msg)
        elif type(msg) != str:
            msg = str(msg)
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        await super().publish(topic.encode(), msg.encode(), retain, qos)
        gc.collect()

    def schedulePublish(self, topic, msg, qos=0, retain=False):
        asyncio.get_event_loop().create_task(self.publish(topic, msg, qos, retain))
