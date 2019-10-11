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
        mqtt_topic: sometopic      # topic of the remote sensor
        # stale_time: 900          # optional, defaults to 900, time after which the remote sensor is considered unavailable
    }
}
"""

# TODO: implement value_template parser?

__updated__ = "2019-10-11"
__version__ = "0.1"

from pysmartnode.utils.component import Component
import gc
import time

gc.collect()


class BaseRemote(Component):
    def __init__(self, COMPONENT_NAME, VERSION, VALUE_TYPE, mqtt_topic, DICT_TEMPLATE=None,
                 stale_time=900):
        super().__init__(COMPONENT_NAME, VERSION, discover=False)
        # discover: not discovering a remote sensor.

        self._stale = stale_time
        self._topic = mqtt_topic
        self._subscribe(self._topic, self.on_message)
        self._value = None
        self._value_time = 0
        self._value_type = VALUE_TYPE
        self._dict_template = DICT_TEMPLATE

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
