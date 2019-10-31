# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-31 

"""
example config:
{
    package: .sensors.remoteSensors.base
    component: BaseRemote
    constructor_args: {
        sensor_type: "temperature" # sensor_type of remote sensor
        mqtt_topic: sometopic      # topic of the remote sensor, if None, then the command topic can be used to set a topic to listen to
        # command_topic: sometopic # optional, defaults to <home>/<client-id>/<COMPONENT_NAME><_count>/topic/set
        # value_template: null     # optional, defaults to {{ value }} taking input "as is" (str,float,int). possible is {{ value_json.<sensor_type> }}
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

# TODO: implement support for multiple sensor_types that share one topic in one component

__updated__ = "2019-10-31"
__version__ = "0.1"

import gc
import time
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component.sensor import ComponentSensor

COMPONENT_NAME = "RemoteSensor"

_mqtt = config.getMQTT()
gc.collect()

_count = 0


class RemoteSensor(ComponentSensor):
    def __init__(self, sensor_type, mqtt_topic=None, command_topic=None,
                 value_template=None, stale_time=900):
        # This makes it possible to use multiple instances of BaseRemote
        global _count
        self._count = _count
        _count += 1
        self._value_type = None  # in case of dictionary it will be determined by json
        v = value_template
        if "value_json." in value_template:
            self._dict_tpl = v[v.find("value_json.") + len("value_json."):v.rfind("}}")].strip()
        else:
            self._dict_tpl = None
        if "|" in value_template:
            v = v[v.find("|") + 1:v.rfind("}}")].strip()
            tp = {"float": float, "int": int, "bool": bool, "string": str}
            if v in tp:
                self._value_type = tp[v]
            else:
                raise TypeError("value_template type {!s} not supported".format(v))
        self._log = logging.getLogger("{}_{}{}".format(COMPONENT_NAME, sensor_type, self._count))
        super().__init__(COMPONENT_NAME, __version__, False, -1, -1, None, self._log, False, None)
        self._addSensorType(sensor_type, 2, 0, value_template, "")
        # no unit_of_measurement as only used for mqtt discovery
        self._stale_time = stale_time
        self._topic = mqtt_topic
        if mqtt_topic is None:
            self._command_topic = command_topic or _mqtt.getDeviceTopic(
                "{!s}{!s}/topic/set".format(COMPONENT_NAME, self._count))
            _mqtt.subscribeSync(self._command_topic, self._changeTopic, self,
                                check_retained_state=True)
        else:
            self._command_topic = None
            _mqtt.subscribeSync(self._topic, self.on_message, self)

    async def _read(self):
        # will be called every time sensor is being read because self._intrd==-1
        sensor_type = list(self.sensor_types)[0]
        if time.ticks_diff(time.ticks_ms(), self.getTimestamp(sensor_type)) > self._stale_time:
            await self._setValue(sensor_type, None)  # will publish error message because no value
        # if value isn't stale, do nothing

    async def _changeTopic(self, topic, msg, retain):
        if retain and self._command_topic is not None:
            await _mqtt.unsubscribe(self._command_topic[:-4], self)
        if self._topic is not None:
            await _mqtt.unsubscribe(self._topic, self)
        self._topic = msg
        _mqtt.subscribeSync(self._topic, self.on_message, self)
        return True

    async def on_message(self, topic, msg, retain):
        if self._dict_tpl:
            if type(msg) != dict:
                raise TypeError("Was expecting a dictionary, not: {!s}".format(msg))
            if self._dict_tpl not in msg:
                raise AttributeError(
                    "dict attribute {!s} not in message {!s}".format(self._dict_tpl, msg))
            msg = msg[self._dict_tpl]
        if self._value_type:
            try:
                msg = self._value_type(msg)  # e.g. int, float, str, bool
            except Exception as e:
                raise e
        await self._setValue(list(self.sensor_types)[0], msg)
        # not changing timeout because there should be no error

    async def _publishValues(self, timeout=5):
        pass  # there is no publish for a remote sensor, even if "accidentally" requested

    def _default_name(self):
        # actually not used anywhere because it's only used for generating default topics
        # and discovery messages which are not used by this sensor.
        # The sensor's own command_topic for changing the topic creates its topic indepentently
        return "{}_{}{}".format(COMPONENT_NAME, list(self.sensor_types)[0], self._count)
