# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-07-13

"""
example config:
{
    package: pysmartnode.custom_components.unix.rfpump
    component: RFPump
    constructor_args: {
        unit_code: "10001"
        unit: "1"
        on_time: 600                        # how long the pump stays on in either mode (security measure in switch mode)
        # repeating_mode: false               # mode false is a simple switch
        # off_time: 1800                      # off-time in repeating mode.
        # expected_execution_time_on: 500  # optional, estimated execution time; allows other coroutines to run during that time
        # expected_execution_time_off: 500 # optional, estimated execution time; allows other coroutines to run during that time
        # iterations: 1                   # optional, number of times the command will be executed
        # iter_delay: 20                  # optional, delay in ms between iterations
        # mqtt_topic: null              #optional, defaults to <mqtt_home>/<device_id>/RF433<count>/set
        # mqtt_topic_on_time: null     #optional, defaults to <mqtt_home>/<device_id>/RF433<count>/on_time/set
        # mqtt_topic_off_time: null     #optional, defaults to <mqtt_home>/<device_id>/RF433<count>/off_time/set
        # mqtt_topic_mode: null     #optional, defaults to <mqtt_home>/<device_id>/RF433<count>/mode/set
        # friendly_name: null       # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_mode: null
    }
}
"""

__updated__ = "2019-07-14"
__version__ = "0.1"

import time
from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.components.unix.rf433switch import RF433, DISCOVERY_SWITCH

####################
COMPONENT_NAME = "RFPump"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "switch"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)

_unit_index = -1


# TODO: remove debug messages

class RFPump(RF433):
    def __init__(self, unit_code, unit, on_time, repeating_mode=False, off_time=None,
                 expected_execution_time_on=500, expected_execution_time_off=500,
                 iterations=1, iter_delay=10, mqtt_topic=None, mqtt_topic_on_time=None,
                 mqtt_topic_off_time=None, mqtt_topic_mode=None, friendly_name=None,
                 friendly_name_mode=None):
        if repeating_mode is True and off_time is None:
            raise TypeError('Mode "repeating" requires off_time')
        super().__init__(unit_code, unit, expected_execution_time_on, expected_execution_time_off,
                         iterations, iter_delay, mqtt_topic, friendly_name)
        del self._topics[self._topic]
        self._repeating_mode = repeating_mode
        self._off_time = off_time or on_time
        self._on_time = on_time
        # This makes it possible to use multiple instances of Pump, _count of rf433 switch will be incremented too
        global _unit_index
        self._count = _count
        _unit_index += 1
        self._topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}{!s}".format(COMPONENT_NAME, self._count),
                                                         is_request=True)
        self._log = _log

        self._off_coro = None
        mqtt_topic_on_time = mqtt_topic_on_time or _mqtt.getDeviceTopic(
            "{!s}{!s}/on_time".format(COMPONENT_NAME, self._count), is_request=True)
        mqtt_topic_off_time = mqtt_topic_off_time or _mqtt.getDeviceTopic(
            "{!s}{!s}/off_time".format(COMPONENT_NAME, self._count), is_request=True)
        mqtt_topic_mode = mqtt_topic_mode or _mqtt.getDeviceTopic(
            "{!s}{!s}/mode".format(COMPONENT_NAME, self._count), is_request=True)
        self._subscribe(self._topic, self.on_message)
        self._subscribe(mqtt_topic_on_time, self.changeOnTime)
        self._subscribe(mqtt_topic_off_time, self.changeOffTime)
        self._subscribe(mqtt_topic_mode, self.changeMode)
        self._topic_mode = mqtt_topic_mode
        self._frn = friendly_name or "RFPump"
        self._frn_mode = friendly_name_mode or "Pump Repeating Mode"

    async def _init(self):
        await self._c_off.execute()  # shut pump off at the start. If retained state is ON it will be activated anyway.
        await super()._init()
        # mode, on_time, off_time currently not published as it is only not in mqtt until the first change is requested
        await asyncio.sleep(4)  # get retained states going if available
        if self._repeating_mode is True and self._off_coro is None:
            self._off_coro = self._repeating()
            asyncio.get_event_loop().create_task(self._off_coro)

    def changeOnTime(self, topic, msg, retain):
        self._on_time = int(msg)
        return True

    def changeOffTime(self, topic, msg, retain):
        self._off_time = int(msg)
        return True

    async def changeMode(self, topic, msg, retain):
        print("changeMode", topic, msg, retain, self._repeating_mode)
        if msg not in _mqtt.payload_on and msg not in _mqtt.payload_off:
            raise ValueError("unsupported payload {!r}".format(msg))
        if msg in _mqtt.payload_on:
            if self._repeating_mode is True:
                # already on
                return True
            elif self._repeating_mode is False:
                await super().on_message(self._topic, "OFF", retain)
                self._off_coro = self._repeating()
                asyncio.get_event_loop().create_task(self._off_coro)
        elif msg in _mqtt.payload_off:
            if self._off_coro is not None:
                asyncio.cancel(self._off_coro)  # will shut down pump
                self._off_coro = None
            if self._repeating_mode is True:
                return True
            elif self._repeating_mode is False:
                await super().on_message(self._topic, "OFF", retain)
                return True
        return True

    async def _wait_off(self):
        print("wait_off started")
        st = time.ticks_ms()
        try:
            while time.ticks_ms() - st < self._on_time * 1000:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self._log.debug("_wait_off canceled", local_only=True)
            print("wait_off canceled")
            return
        except Exception as e:
            await self._log.asyncLog("error", "wait_off error: {!s}".format(e))
            return False
        finally:
            print("wait_off exited")
        await super().on_message(self._topic, "OFF", False)

    async def _repeating(self):
        print("repeating started")
        self._repeating_mode = True
        try:
            while True:
                st = time.ticks_ms()
                await super().on_message(self._topic, "ON", False)
                while time.ticks_ms() - st < self._on_time * 1000:
                    await asyncio.sleep(1)
                await super().on_message(self._topic, "OFF", False)
                st = time.ticks_ms()
                while time.ticks_ms() - st < self._off_time * 1000:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("repeating canceled")
            self._log.debug("_repeating canceled", local_only=True)
        except Exception as e:
            await self._log.asyncLog("error", "_repeating error: {!s}".format(e))
        finally:
            await super().on_message(self._topic, "OFF", False)
            self._repeating_mode = False
            print("repeating exited")

    async def on_message(self, topic, msg, retain):
        """
        Changes the state of the pump.
        In switch mode a safety shutdown coro will be started.
        In repeating mode only the state of the pump gets changed.
        """
        print("on_message", topic, msg, retain, self._repeating_mode)
        if retain is True:
            await asyncio.sleep(2)  # so that other retained message about on_time,off_time and mode get processed first
        if self._repeating_mode is False:
            if self._off_coro is not None:
                asyncio.cancel(self._off_coro)
        if msg in _mqtt.payload_on:
            if (await super().on_message(topic, msg, retain)) is True:
                if self._repeating_mode is False:
                    self._off_coro = self._wait_off()
                    asyncio.get_event_loop().create_task(self._off_coro)
        elif msg in _mqtt.payload_off:
            if (await super().on_message(topic, msg, retain)) is False:
                if self._repeating_mode is False:
                    self._off_coro = self._wait_off()
                    asyncio.get_event_loop().create_task(self._off_coro)  # try again
        else:
            await _log.asyncLog("error", "unsupported payload: {!s}".format(msg))
            return False
        return True

    async def _discovery(self):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic but we have the command topic stored.
        name = "{!s}{!s}_{!s}".format(COMPONENT_NAME, self._count, "Repeating_mode")
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic_mode[:-4], name, DISCOVERY_SWITCH, self._frn_mode)

    # async def on/off will switch the current state of the pump in on_message
