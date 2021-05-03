# Author: Kevin Köck
# Copyright Kevin Köck 2018-2020 Released under the MIT license
# Created on 2018-02-17

__updated__ = "2020-11-04"
__version__ = "6.4"

import gc
import ujson
import time
import uasyncio as asyncio
import os
from pysmartnode import config
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars

if config.MQTT_TYPE:
    from micropython_mqtt_as.mqtt_as_timeout_concurrent import MQTTClient
else:
    from dev.mqtt_iot import MQTTClient  # Currently not working/under development
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
        self._sub_task = None
        self._sub_retained = False
        super().__init__(client_id=self.client_id,
                         server=config.MQTT_HOST,
                         port=config.MQTT_PORT if hasattr(config, "MQTT_PORT") else 1883,
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
        asyncio.create_task(self._connectCaller())
        self.__first_connect = True
        self._connected_task = None
        self._reconnected_subs = []
        self._wifi_task = None
        self._wifi_subs = []
        self.__unsub_tmp = []
        self.__last_disconnect = None  # ticks_ms() of last disconnect
        self.__downtime = 0  # mqtt downtime in seconds
        self.__reconnects = -1  # not counting the first connect
        self.__dropped = 0  # dropped messages due to MQTT_MAX_CONCURRENT_EXECUTIONS
        self.__timedout = 0  # operations that timed out. doesn't mean it's a problem.
        self.__active_cbs = 0  # currently active callbacks due to received messages
        gc.collect()

    def close(self):
        # subclassing close because mqtt_as doesn't provide a callback when connection
        # to mqtt broker is lost, only when wifi connection is lost.
        if self.__last_disconnect is None:
            self.__last_disconnect = time.ticks_ms()
        super().close()

    def getDowntime(self):
        if self.__last_disconnect is None:
            return self.__downtime
        else:
            return (time.ticks_ms() - self.__last_disconnect) / 1000 + self.__downtime

    def getDroppedMessages(self):
        return self.__dropped

    def getTimedOutOperations(self):
        return self.__timedout

    def getLenSubscribtions(self):
        return len(self._subs)

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

    async def disconnect(self):
        """
        Publish last will before disconnecting because it indicates if the device is available.
        """
        if not await self.publish(self._lw_topic, self._lw_msg, self._lw_retain, self._lw_qos,
                                  timeout=5, await_connection=False):
            self.close()
            # force close the socket so last will message will be published by broker
            # if still connected.
        await super().disconnect()

    async def _connectCaller(self):
        import network
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        if platform == "pyboard":
            st = network.WLAN(network.STA_IF)
            st.active(True)
            st.connect(config.WIFI_SSID, config.WIFI_PASSPHRASE)
            await asyncio.sleep(5)
            st.disconnect()  # sadly needed otherwise first connection attempt won't work
        while True:
            try:
                await self.connect()
                return
            except OSError as e:
                _log.error("Error connecting to wifi or mqtt:", e, local_only=True)
                # not connected after trying.. not much we can do without a connection except
                # trying again.
                # Don't like resetting the machine as components could be working without wifi.
                await asyncio.sleep(10)
                continue

    async def _wifiChanged(self, state):
        if self._wifi_task is not None:
            self._wifi_task.cancel()
        self._wifi_task = asyncio.create_task(self._wifi_changed(state))

    async def _wifi_changed(self, state):
        _log.info("WIFI state", state, local_only=True)
        # TODO: change to asyncio.gather() [not on esp8266] as soon as cancelling gather works.
        for cb in self._wifi_subs:
            res = cb(self, state)
            if type(res) == type_gen:
                await res
        self._wifi_task = None

    async def _connected(self, client):
        _log.info("mqtt connected", local_only=True)
        self.__reconnects += 1
        if self.__last_disconnect is not None:
            self.__downtime += (time.ticks_ms() - self.__last_disconnect) / 1000
        self.__last_disconnect = None
        if self._connected_task is not None:
            # processed subscriptions would have to be done again anyway
            self._connected_task.cancel()
        self._connected_task = asyncio.create_task(self._connected_handler(client))

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
                await _log.asyncLog("debug", "Reconnected")
            # subscribe topics because clean session is used. Some components might be added
            # before connection has been made so subscribe on first connect too.
            if self._sub_task is not None:
                self._sub_task.cancel()
            self._sub_task = asyncio.create_task(self._subscribeTopics())
            # TODO: change to asyncio.gather() as soon as cancelling gather works.
            for cb in self._reconnected_subs:
                res = cb(client)
                if type(res) == type_gen:
                    await res
            self._connected_task = None
        except asyncio.CancelledError:
            if self._sub_task is not None:
                self._sub_task.cancel()

    async def _subscribeTopics(self, start: int = 0):
        # TODO: make concurrent for esp32
        # TODO: if state topic gets unsubscribed in callback and connection breaks,
        #  command topic won't be subscribed anymore because it is somehow jumped when
        #  the login topic is subscribed although already unsubscribed...
        _log.debug("_subscribeTopics, start", start, local_only=True)
        if not self.isconnected():
            _log.debug("_subscribeTopics, no connection", local_only=True)
            return
        try:
            for i, sub in enumerate(self._subs):
                # do not iter by range(start,length(_subs)) as _subs could get bigger while itering
                if i < start:
                    continue  # iter until start position reached
                t = sub[0]
                if self.isDeviceTopic(t):
                    t = self.getRealTopic(t)
                if len(sub) == 4:  # requested retained state topic
                    self._sub_retained = True
                    # if coro gets canceled in the process, the state topic will be checked
                    # the next time _subscribeTopic runs after the reconnect
                    _log.debug("_subscribing", t[:-4], local_only=True)
                    if not await super().subscribe(t[:-4], 1, await_connection=False):
                        # state topic
                        _log.debug("Error subscribing, lost connection:", t[:-4], local_only=True)
                        return  # connection loss exits the process
                    ts = time.ticks_ms()  # start timer after successful subscribe otherwise
                    # it might time out before subscribe has even finished.
                    while time.ticks_diff(time.ticks_ms(), ts) < 4000 and self._sub_retained:
                        # wait 4 seconds for answer
                        # TODO: split this into a different task so it doesn't delay subscribing.
                        await asyncio.sleep_ms(100)
                    if self._sub_retained is True:  # no state message received
                        self._subs[i] = sub[:3]
                        self._sub_retained = False
                        _log.debug("Unsubscribing state topic", t[:-4], "in _subsscribeTopics",
                                   local_only=True)
                        if not await super().unsubscribe(t[:-4], await_connection=False):
                            _log.debug("Error unsubscribing state topic, lost conenction:", t[:-4],
                                       local_only=True)
                            return  # connection loss exits the process
                _log.debug("_subscribing", t, local_only=True)
                if not await super().subscribe(t, 1, await_connection=False):
                    _log.debug("Error subscribing, lost connection:", t, local_only=True)
                    return  # connection loss exits the process
                # no timeouts because _subscribeTopics will get canceled when connection is lost
        except asyncio.CancelledError:
            _log.debug("_subscribeTopics cancelled", local_only=True)
        finally:
            # remove pending unsubscribe requests
            for sub in self.__unsub_tmp:
                self._subs.remove(sub)
                self.__unsub_tmp = []
            self._sub_task = None
            _log.debug("_subscribeTopics exited", local_only=True)

    def _convertToDeviceTopic(self, topic):
        t = topic.replace("{!s}/{!s}/".format(self.mqtt_home, self.client_id), "./")
        if t == topic:  # nothing replaced
            raise TypeError("Topic is not a device subscription: {!s}".format(topic))
        return t

    def _isDeviceSubscription(self, topic):
        return topic.startswith("{!s}/{!s}/".format(self.mqtt_home, self.client_id))

    # @micropython.native native emitter on esp8266 not working anymore and not working on pyboard
    @staticmethod
    def matchesSubscription(topic, subscription, ignore_command=False):
        if topic == subscription:
            return True
        mt = memoryview(topic)
        ms = memoryview(subscription)
        if ignore_command is True and subscription.endswith("/set"):
            if mt == ms[:-4]:
                return True
        if subscription.endswith("/#") or subscription.endswith("/+"):
            lens = len(subscription)
            if mt[:lens - 2] == ms[:-2]:
                if subscription.endswith("/#"):
                    if len(topic) == lens - 2 or mt[lens - 2:lens - 1] == b"/":
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
            if ms[:pl + 1] == mt[:pl + 1]:  # equal until /+
                if subscription.endswith("/#"):
                    sub = subscription.replace("/+/", topic[pl:topic.find("/", pl + 1) + 1])
                    return MQTTHandler.matchesSubscription(topic, sub, ignore_command)
                if ignore_command is True:
                    if ms[-5:] == b"+/set" and st == 0:  # st==0 no subtopics
                        return True
                    elif ms[-4:] == b"/set":
                        ed = len(subscription) - 4
                    else:
                        ed = len(subscription)
                else:
                    ed = len(subscription)
                if ms[pl + 3:ed] == mt[st:]:
                    return True
            return False
        return False

    def scheduleUnsubscribe(self, topic=None, component=None):
        asyncio.create_task(self.unsubscribe(topic, component))

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
        _log.debug("unsubscribing topic", topic, "from component", component, local_only=True)
        r = self.__unsub_tmp
        t = []
        for sub in self._subs:
            if topic is None and sub[2] == component:
                if sub not in r:  # already unsubscribed but _subscribeTopics still active
                    r.append(sub)
                    if sub[0] not in t:
                        t.append(sub[0])
            elif sub[0] == topic and (component is None or component == sub[2]):
                if sub not in r:  # already unsubscribed but _subscribeTopics still active
                    r.append(sub)
                    if sub[0] not in t:
                        t.append(sub[0])
        if not r:
            if topic:  # only log if a topic was requested, could be a component removal
                _log.error("Can't unsubscribe, topic not found:", topic, "component", component,
                           local_only=True)
            return False
        s = True
        for sub in t:
            _log.debug("Unsubscribing from broker:", sub, local_only=True)
            if not await super().unsubscribe(self.getRealTopic(sub), await_connection=False):
                _log.error("Error unsubscribing, lost conenction:", sub, local_only=True)
                s = False
        del t
        # unsubscribe from broker but locally have to wait for subscribe to be finished
        # so the subs list doesn't get messed up. _sub_task will remove values on finish.
        if self._sub_task:
            return s
        # remove pending unsubscribe requests
        for sub in r:
            try:
                self._subs.remove(sub)
            except ValueError:
                pass  # already removed by different unsubscribe attempt
        self.__unsub_tmp = []
        return s

    async def subscribe(self, topic, cb, component=None, qos=1, check_retained_state=False,
                        timeout=None, await_connection=True):
        """
        Subscribe a topic
        :param topic: str, either real topic or deviceTopic
        :param cb: callback/coroutine
        :param component: optional component object. Used when unsubscribing a complete component
        :param qos: subscriptions are always qos=1, changing it won't make a difference.
        :param check_retained_state: check the retained state of the state topic of a subscription
        :param timeout: returns after timeout without knowing the succes. Will subscribe anyway.
        :param await_connection: Return if no connection. Will subscribe anyway
        :return: True if subscription is acknowledged, else False (but will subscribe anyway)
        """
        self.subscribeSync(topic, cb, component, qos, check_retained_state)
        return self.awaitSubscriptionsDone(timeout, await_connection)

    def subscribeSync(self, topic, cb, component=None, qos=1, check_retained_state=False):
        _log.debug("Subscribing to topic", topic, "for component", component, "checking retained",
                   check_retained_state, local_only=True)
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        if check_retained_state and topic.endswith("/set"):
            sub = (topic, cb, component, True)
        else:  # if no command_topic then ignore check_retained_state
            sub = (topic, cb, component)
        self._subs.append(sub)
        if self._sub_task is None:
            self._sub_task = asyncio.create_task(self._subscribeTopics(self._subs.index(sub)))

    async def awaitSubscriptionsDone(self, timeout=None, await_connection=True):
        start = time.ticks_ms()
        while timeout is None or time.ticks_diff(time.ticks_ms(), start) < timeout * 1000:
            if not await_connection and not self._isconnected:
                return False
            if self._sub_task is None:
                return True  # all topics subscribed.
            await asyncio.sleep_ms(50)  # can't await task directly because if this task gets
            # cancelled, it will cancel the subscription task.. Could use an Event though.
        return False  # timeout

    @staticmethod
    def getDeviceTopic(attrib, is_request=False):
        return "./{}{}".format(attrib, "/set" if is_request else "")

    @staticmethod
    def isDeviceTopic(topic):
        return topic.startswith("./")

    def getRealTopic(self, device_topic):
        if not device_topic.startswith("./"):
            return device_topic  # no need to raise an error if real topic is passed
        return "{}/{}/{}".format(self.mqtt_home, self.client_id, device_topic[2:])

    def _execute_sync(self, topic, msg, retained):
        _log.debug("mqtt received:", topic, msg, retained, local_only=True)
        # optional safety feature if memory allocation fails on receive of messages.
        # Should actually never happen in a user controlled environment.
        # mqtt_as must support it for code having any effect.
        """ # Not enabled in mqtt_as as typically not needed
        if topic is None or msg is None:
            self.__dropped += 1
            _log.error("Received message that didn't fit into RAM on topic {!s}".format(topic),
                       local_only=True)
            return
        """
        topic = topic.decode()
        msg = msg.decode()
        try:
            msg = ujson.loads(msg)
        except ValueError:
            pass  # maybe not a json string, no way of knowing
        if self._isDeviceSubscription(topic):
            topic = self._convertToDeviceTopic(topic)
        found = False
        for sub in self._subs:
            if self.matchesSubscription(topic, sub[0], ignore_command=len(sub) == 4):
                if config.MQTT_MAX_CONCURRENT_EXECUTIONS != -1:
                    dr = self.__active_cbs >= config.MQTT_MAX_CONCURRENT_EXECUTIONS
                else:
                    dr = 0
                if dr:
                    self.__dropped += 1
                    _log.error("dropping message of topic", topic, "component", sub[2],
                               "too many active cbss:", "{!s}".format(self.__active_cbs),
                               local_only=True)
                else:
                    self.__active_cbs += 1
                    asyncio.create_task(self._execute_callback(sub, topic, msg, retained))
                found = True
        if found is False:
            _log.warn("Subscribed topic", topic,
                      "not found, should solve itself. not yet unsubscribed", local_only=True)

    async def _execute_callback(self, sub, topic, msg, retained):
        _log.debug("execute_callback of", sub[2], ":", topic,
                   msg if type(msg) in (str, int, float) else type(msg), local_only=True)
        if len(sub) == 4 and "/+" not in sub[0]:  # sub can't end with /#/set but /+/set
            # retained state topic received without wildcards (could receive multiple states)
            self._subs[self._subs.index(sub)] = sub[:3]
            self._sub_retained = False
            if self.isDeviceTopic(sub[0]):
                t = self.getRealTopic(sub[0])[:-4]
            else:
                t = sub[0][:-4]
            _log.debug("Unsubscribing state topic", t, "in _exec_cb", local_only=True)
            if not await super().unsubscribe(t, await_connection=False):
                _log.error("Error unsubscribing state topic, lost conenction:", t, local_only=True)
            del t
            gc.collect()
            # unsubscribing before executing to prevent callback to publish to state topic
            if not retained:
                _log.error("Received non retained message when checking retained state topic",
                           topic, ",ignoring message", local_only=True)
                self.__active_cbs -= 1
                return
        _t1 = time.ticks_ms()
        res = None
        try:
            res = sub[1](topic, msg, retained)
            if type(res) == type_gen:
                res = await res
            if not retained and topic.endswith("/set"):
                # if a /set topic is found, send without /set, this is always retained:
                if res:  # Could be any return value
                    if res is True:
                        res = msg  # send original msg back if return is True
                    await self.publish(topic[:-4], res, qos=1, retain=True)
        except Exception as e:
            await _log.asyncLog("error",
                                "Error executing {!s}mqtt topic {!r}: {!s}".format(
                                    "retained " if retained else "", topic, e))
        finally:
            self.__active_cbs -= 1
            _t2 = time.ticks_ms()
            _log.debug("execute_callback of", sub[2], ":", topic,
                       msg if type(msg) in (str, int, float) else type(msg),
                       "took {!s}ms".format(time.ticks_diff(_t2, _t1)), "returned", res,
                       local_only=True)

    async def publish(self, topic, msg, retain=False, qos=1, timeout=None, await_connection=True):
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
        each publish, so if connection becomes unavailable, this returns False immediately.
        :return: True on success, False on timeout or connection loss. No need to raise TimeoutError
        because False already represents timeout error and the difference between connection loss
        and timeout shouldn't matter.
        """
        if (not await_connection and not self.isconnected()) or timeout == 0:
            return False
        if type(msg) == dict or type(msg) == list:
            msg = ujson.dumps(msg)
        elif type(msg) not in (str, bytes):
            msg = str(msg).encode()
        if self.isDeviceTopic(topic):
            topic = self.getRealTopic(topic)
        msg = msg.encode() if type(msg) == str else msg
        # note that msg has to be bytes otherwise mqtt library produces errors when sending
        gc.collect()
        try:
            return await super().publish(topic, msg, retain, qos, timeout=timeout,
                                         await_connection=await_connection)
        except asyncio.TimeoutError:
            self.__timedout += 1
            return False

    def schedulePublish(self, topic, msg, retain=False, qos=0, timeout=None,
                        await_connection=True) -> asyncio.Task:
        return asyncio.create_task(
            self.publish(topic, msg, retain, qos, timeout, await_connection))
