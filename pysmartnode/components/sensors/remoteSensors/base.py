# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-11

"""
example config:
{
    package: .sensors.remoteSensors.base
    component: BaseRemote
    constructor_args: {
        ...: ...                   # args for subclasses
        mqtt_topic: sometopic      # topic of the remote sensor, if None, then the command topic can be used to set a topic to listen to
        # command_topic: sometopic # optional, defaults to <home>/<client-id>/<COMPONENT_NAME><_count>/topic/set
        # stale_time: 900          # optional, defaults to 900, time after which the remote sensor is considered unavailable
    }
}
command_topic is used if mqtt_topic is not given so the mqtt_topic can be set using the command_topic.
If mqtt_topic is given, then command_topic won't be used.
Since other components might depend on this component's topic, setting it through mqtt might
cause problems since the topic won't be stored on startup. You need to wait for network to be
finished so the retained state can be restored. Typically if a component is initialized after
this sensor and the _init_network is called, the topic value should have been received.
"""

# TODO: implement value_template parser?

__updated__ = "2019-10-20"
__version__ = "0.3"

from pysmartnode.utils.component import Component
import gc
import time
from pysmartnode import config
import uasyncio as asyncio

_mqtt = config.getMQTT()
gc.collect()

_count = 0


class BaseRemote(Component):
    def __init__(self, COMPONENT_NAME, VERSION, VALUE_TYPE, mqtt_topic=None, command_topic=None,
                 DICT_TEMPLATE=None, stale_time=900):
        super().__init__(COMPONENT_NAME, VERSION, discover=False)
        # discover: not discovering a remote sensor.

        # This makes it possible to use multiple instances of BaseRemote
        global _count
        self._count = _count
        _count += 1
        # Not including in subclasses to make development easier.
        # might result in names like RemoteTemperature0, RemoteHumidity1, RemoteTemperature2

        self._stale = stale_time
        self._topic = mqtt_topic
        if mqtt_topic is None:
            self._command_topic = command_topic or _mqtt.getDeviceTopic(
                "{!s}{!s}/topic/set".format(COMPONENT_NAME, self._count))
            _mqtt.subscribeSync(self._command_topic, self._changeTopic, self,
                                check_retained_state=True)
        else:
            self._command_topic = None
            _mqtt.subscribeSync(self._topic, self.on_message, self)
        self._value = None
        self._value_time = 0
        self._value_type = VALUE_TYPE
        self._dict_template = DICT_TEMPLATE

    async def _changeTopic(self, topic, msg, retain):
        if retain and self._command_topic is not None:
            await _mqtt.unsubscribe(self._command_topic[:-4], self)
        if self._topic is not None:
            await _mqtt.unsubscribe(self._topic, self)
        self._topic = msg
        _mqtt.subscribeSync(self._topic, self.on_message, self)
        return True

    async def on_message(self, topic, msg, retain):
        if self._dict_template is not None:
            if type(msg) != dict:
                raise TypeError("Was expecting a dictionary, not: {!s}".format(msg))
            if self._dict_template not in msg:
                raise AttributeError(
                    "dict template {!s} not in message {!s}".format(self._dict_template, msg))
            msg = msg[self._dict_template]
        try:
            msg = self._value_type(msg)  # e.g. int, float, str
        except Exception as e:
            raise e
        self._value = msg
        self._value_time = time.ticks_ms()

    def _getValue(self):
        """returns None if value is too old"""
        if time.ticks_diff(time.ticks_ms(), self._value_time) > (self._stale * 1000):
            return None
        return self._value
