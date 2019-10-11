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
        # mqtt_topic: sometopic  # optional, defaults to home/<controller-id>/<component_name>/<component-count>/set
        # mqtt_topic2: sometopic # optional, defautls to home/sometopic
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-10-11"
__version__ = "1.4"

import uasyncio as asyncio
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH
import gc

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "MyComponent"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "switch"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


# This template is for a very general component.
# It might be better to either use the templates for a specific type of
# component like a sensor or a switch.


class MyComponent(Component):
    def __init__(self, my_value,  # extend or shrink according to your sensor
                 mqtt_topic=None, mqtt_topic2=None,
                 friendly_name=None, discover=True):
        super().__init__(COMPONENT_NAME, __version__, discover=discover)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        # This makes it possible to use multiple instances of MyComponent
        global _count
        self._count = _count
        _count += 1

        # This will generate a topic like: home/31f29s/MyComponent0/set
        self._command_topic = mqtt_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}".format(COMPONENT_NAME, self._count), is_request=True)

        # These calls subscribe the topics (actual subscription process done in _init_network),
        # don't use _mqtt.subscribe.
        self._subscribe(self._command_topic, self.on_message1)
        self._subscribe(mqtt_topic2 or "home/sometopic", self.on_message2)

        self.my_value = my_value

        self._frn = friendly_name  # will default to unique name in discovery if None
        asyncio.get_event_loop().create_task(self._loop())
        gc.collect()

    async def _init_network(self):
        await super()._init_network()
        # NEVER start loops here because it will block the _init_network of all other components!
        # Start a new uasyncio task in __init__() if you need additional loops.
        # This method is only used for subscribing topics, publishing discovery and logging things.
        # It can be used for similar network oriented initializations.

    async def _loop(self):
        while True:
            await asyncio.sleep(5)
            await _mqtt.publish(self._command_topic[:-4], "ON", qos=1)  # publishing to state_topic

    async def _discovery(self):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        component_topic = _mqtt.getDeviceTopic(name)
        # component topic could be something completely user defined.
        # No need to follow the pattern:
        component_topic = self._command_topic[:-4]  # get the state topic of custom component topic
        friendly_name = self._frn  # define a friendly name for the homeassistant gui.
        # Doesn't need to be unique
        await self._publishDiscovery(_COMPONENT_TYPE, component_topic, name, DISCOVERY_SWITCH,
                                     friendly_name)
        del name, component_topic, friendly_name
        gc.collect()

    async def on_message1(self, topic, message, retained):
        """
        MQTTHandler is calling this subscribed async method whenever a message is received for the subscribed topic.
        :param topic: str
        :param message: str/dict/list (json converted)
        :param retained: bool
        :return:
        """
        print("Do something")
        return True  # When returning True, the value of arg "message" will be
        # published to the state topic as a retained message

    async def on_message2(self, topic, message, retained):
        """
        MQTTHandler is calling this subscribed async method whenever a message is received for the subscribed topic.
        :param topic: str
        :param message: str/dict/list (json converted)
        :param retained: bool
        :return:
        """
        print("Do something else")
        return True  # When returning True, the value of arg "message" will be
        # published to the state topic as a retained message
