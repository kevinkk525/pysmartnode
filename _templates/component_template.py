'''
Created on 2018-06-22

@author: Kevin Köck
'''

"""
example config for MyComponent:
{
    package: <package_path>
    component: MyComponent
    constructor_args: {
        my_value: "hi there"             
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/<component_name>
    }
}
example config for loopingComponent:
{
    package: <package_path>
    component: loopingComponent
    constructor_args: {
        my_value: "hi there"             
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/<component_name>
    }
}
"""

__updated__ = "2018-08-31"
__version__ = "0.5"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "HTU"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class MyComponent:
    def __init__(self, my_value,  # extend or shrink according to your sensor
                 mqtt_topic=None):
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)
        self.my_value = my_value
        gc.collect()


async def loopingComponent(my_value, mqtt_topic=None):
    mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)
    while True:
        await asyncio.sleep(5)
        await _mqtt.publish(mqtt_topic, my_value)
