'''
Created on 14.04.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: _testing.mqtt_temp_sensor
    component: MySensor
    constructor_args: {
        # topic: sometopic  #optional, defaults to home/<controller-id>/MySensor
    }
}
"""

__updated__ = "2018-09-28"
__version__ = "0.1"

from pysmartnode import config
from pysmartnode import logging
import gc

####################
# import your library here

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "MySensor"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class MySensor:
    def __init__(self, topic=None):
        topic = topic or _mqtt.getDeviceTopic(_component_name)
        _mqtt.scheduleSubscribe(topic + "/set", self._setTemp)
        self.temp = None

    async def _setTemp(self, topic, msg, retained):
        self.temp = float(msg)
        return True

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, publish=True):
        return self.temp

    ##############################
