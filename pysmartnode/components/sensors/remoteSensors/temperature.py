# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-11

"""
example config:
{
    package: .sensors.remoteSensors.temperature
    component: RemoteTemperature
    constructor_args: {
        mqtt_topic: sometopic               # optional, topic of the remote sensor
        # command_topic: sometopic          # optional, defaults to <home>/<client-id>/<COMPONENT_NAME><_count>/topic/set
        # stale_time: 900                   # optional, defaults to 900, time after which the remote sensor is considered unavailable
        # value_template_dict_attr: null    # optional, dictionary attribute if msg is a dictionary in combined sensor readings
    }
}
command_topic is used if mqtt_topic is not given so the mqtt_topic can be set using the command_topic
If mqtt_topic is given, then command_topic won't be used.
"""

__updated__ = "2019-10-16"
__version__ = "0.2"

from .base import BaseRemote

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "RemoteTemperature"
_VAL_T_TEMPERATURE = "{{ value|float }}"


####################


class RemoteTemperature(BaseRemote):
    def __init__(self, mqtt_topic=None, command_topic=None, stale_time=900,
                 value_template_dict_attr=None):
        """
        :param mqtt_topic: topic of remote sensor
        :param command_topic: if mqtt_topic is not given, this topic can be used to set the mqtt_topic
        :param stale_time: after this time the remote sensor is considered dead
        :param value_template_dict_attr: dictionary attribute if value_template uses dictionary.
        """
        super().__init__(COMPONENT_NAME, __version__, float, mqtt_topic, command_topic,
                         DICT_TEMPLATE=value_template_dict_attr, stale_time=stale_time)

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, publish=True, timeout=5):
        return self._getValue()

    def temperatureTemplate(self):
        """Other components like HVAC might need to know the value template of a sensor"""
        if self._dict_template is None:
            return _VAL_T_TEMPERATURE
        else:
            return "{{{{ value_json.{!s} }}}}".format(self._dict_template)

    def temperatureTopic(self):
        return self._topic

    ##############################
