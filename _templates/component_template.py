# Author: Kevin Köck
# Copyright Kevin Köck 2018 Released under the MIT license
# Created on 2018-06-22

"""
example config for MyComponent:
{
    package: <package_path>
    component: MyComponent
    constructor_args: {
        my_value: "hi there"             
        # mqtt_topic: sometopic  # optional, defaults to home/<controller-id>/<component_name>/<component-count>/set
        # mqtt_topic2: sometopic # optional, defautls to home/sometopic
        # friendly_name: null    # optional, friendly name shown in homeassistant gui with mqtt discovery
        # discover: true         # optional, if false no discovery message for homeassistant will be sent.
    }
}
"""

__updated__ = "2019-11-15"
__version__ = "1.9"

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

_unit_index = -1


# This template is for a very general component.
# It might be better to either use the templates for a specific type of
# component like a sensor or a switch.


class MyComponent(Component):
    def __init__(self, my_value,  # extend or shrink according to your sensor
                 mqtt_topic=None, mqtt_topic2=None,
                 friendly_name=None, discover=True):
        # This makes it possible to use multiple instances of MyComponent
        # It is needed for every default value for mqtt.
        # Initialize before super()__init__(...) to not pass the wrong value.
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover=discover)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        # This will generate a topic like: home/31f29s/MyComponent0/set
        self._command_topic = mqtt_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}".format(COMPONENT_NAME, self._count), is_request=True)

        # These calls subscribe the topics.
        _mqtt.subscribeSync(self._command_topic, self.on_message1, self, check_retained_state=True)
        # check_retained_state will subscribe to the state topic (home/31f29s/MyComponent0)
        # first, so the original state of the device can be restored.
        # The state topic will then be unsubscribed and the requested command topic subscribed.
        _mqtt.subscribeSync(mqtt_topic2 or "home/sometopic", self.on_message2, self)

        self.my_value = my_value

        self._frn = friendly_name  # will default to unique name in discovery if None

        self._loop_task = asyncio.create_task(self._loop())
        # the component might get removed in which case it should be able to locate and stop
        # any running loops it created (otherwise the component will create Exceptions and
        # won't be able to be fully removed from RAM)
        gc.collect()

    async def _init_network(self):
        await super()._init_network()
        # All _init_network methods of every component will be called after each other.
        # Therefore every _init_network of previously registered components will have
        # run when this one is running.

        # NEVER start loops here because it will block the _init_network of all other components!
        # Start a new uasyncio task in __init__() if you need additional loops.
        # This method is only used for subscribing topics, publishing discovery and logging.
        # It can be used for similar network oriented initializations.

    async def _loop(self):
        # A loop should either only do network oriented tasks or only
        # non-network oriented tasks to ensure that the device works
        # even when the network is unavailable. A compromise could be
        # to use network oriented tasks with timeouts if those delays
        # aren't a problem for the device functionality.
        while True:
            await asyncio.sleep(5)
            await _mqtt.publish(self._command_topic[:-4], "ON", qos=1)  # publishing to state_topic

    async def _remove(self):
        """Will be called if the component gets removed"""
        # Cancel any loops/asyncio coroutines started by the component
        self._loop_task.cancel()
        await super()._remove()

    async def _discovery(self, register=True):
        """
        Send discovery messages
        :param register: if True send discovery message, if False send empty discovery message
        to remove the component from homeassistant.
        :return:
        """
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        component_topic = _mqtt.getDeviceTopic(name)
        # component topic could be something completely user defined.
        # No need to follow the pattern:
        component_topic = self._command_topic[:-4]  # get the state topic of custom component topic
        friendly_name = self._frn  # define a friendly name for the homeassistant gui.
        # Doesn't need to be unique
        if register:
            await self._publishDiscovery(_COMPONENT_TYPE, component_topic, name, DISCOVERY_SWITCH,
                                         friendly_name)
        else:
            await self._deleteDiscovery(_COMPONENT_TYPE, name)
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
