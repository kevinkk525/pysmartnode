# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-09-27

"""
example config:
{
    package: .switches.generic_switch
    component: Switch
    constructor_args: {
        component: "pump"                 # name of the component that will be controlled. (It has to have "on" and "off" implemented)
        modes_enabled: ["safety_off","repeating"]  # list of modes to make available. Available modes: "safety_off","repeating"
        # mqtt_topic_on_time: null     #optional, defaults to <mqtt_home>/<device_id>/Switch<count>/on_time/set
        # mqtt_topic_off_time: null     #optional, defaults to <mqtt_home>/<device_id>/Switch<count>/off_time/set
        # mqtt_topic_mode: null     #optional, defaults to <mqtt_home>/<device_id>/Switch<count>/mode/set ; accepts string of modes_enabled
        # friendly_name_mode: null  # optional, friendly name of sensor showing current mode
    }
}
This is a generic switch class extending the functionality of any switch base class.
For example a pump can be a simple switch component controlling the pump directly while
this class provides all higher features like security shutdown after on_time or a repeating mode
for running every e.g. 30 minutes.

The class automatically only makes modes and options available to Homeassistant that are configured
in modes_enabled.
As Homeassistant only supports sensors and switches to be discovered, every mode will have a switch
to enable the mode.
"""

# TODO: change mode initialization to make default constructor args possible

__updated__ = "2020-03-29"
__version__ = "0.8"

from pysmartnode import config
from pysmartnode import logging
import gc
from pysmartnode.utils.component.switch import Component, ComponentSwitch, DISCOVERY_SWITCH
from uasyncio import Lock

####################
COMPONENT_NAME = "SwitchExtension"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "switch"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)
_unit_index = -1


class BaseMode:
    """
    Base class for all modes and also default mode being just a simple switch
    """

    # def __init__(self,extended_switch, component, component_on, component_off):

    async def on(self, extended_switch, component, component_on, component_off):
        """Turn device on"""
        return await component_on()

    async def off(self, extended_switch, component, component_on, component_off):
        """Turn device off"""
        return await component_off()

    async def toggle(self, extended_switch, component, component_on, component_off):
        if component.state() is True:
            return await self.off(extended_switch, component, component_on, component_off)
        return await self.on(extended_switch, component, component_on, component_off)

    async def activate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been activated"""
        return True  # keeps the current state of the component

    async def deactivate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        return await self.off(extended_switch, component, component_on, component_off)

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        return "None"


Mode = BaseMode()


class Switch(Component):
    def __init__(self, component: ComponentSwitch, modes_enabled: list,
                 mqtt_topic_mode=None, friendly_name_mode=None, discover=True, **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover, **kwargs)
        if type(component) == str:
            self._component = config.getComponent(component)
            if self._component is None:
                raise TypeError("Component {!s} not found".format(component))
        else:
            self._component = component
        if not isinstance(self._component, ComponentSwitch):
            raise TypeError("Component needs to be of instance ComponentSwitch")
        # make this class control the component
        self._component.on_message = self.on_message
        self._component_on = self._component.on
        self._component_off = self._component.off
        self._component.on = self.on
        self._component.off = self.off
        self._component.toggle = self.toggle
        if type(modes_enabled) != list:
            raise TypeError("modes enabled needs to be a list")
        count = self._component._count if hasattr(self._component, "_count") else ""
        _name = self._component._name if hasattr(self._component, "_name") else "{!s}{!s}".format(
            COMPONENT_NAME, count)
        mqtt_topic_mode = mqtt_topic_mode or _mqtt.getDeviceTopic("{!s}/mode".format(_name),
                                                                  is_request=True)
        self._topic_mode = mqtt_topic_mode
        self._frn_mode = friendly_name_mode or "{!s} Mode".format(_name)
        self._mode = Mode  # Mode is default switch behaviour if no mode is enabled
        name = config.getComponentName(self._component)
        if name is None:
            self._log = logging.getLogger("{!s}".format(_name))
        else:
            self._log = logging.getLogger("{!s}_{!s}".format(name, "Switch"))
        del name
        self._mode_lock = Lock()
        gc.collect()
        r = []
        self._modes_enabled = []
        for mode in modes_enabled:
            try:
                mod = __import__(
                    "pysmartnode.components.switches.switch_extension.{}".format(mode), globals(),
                    locals(), [], 0)
            except ImportError as e:
                _log.error("Mode {!s} not available: {!s}".format(mode, e))
                r.append(mode)
                continue
            if hasattr(mod, mode):
                modeobj = getattr(mod, mode)
            else:
                _log.error("Mode {!s} has no class {!r}".format(mode, mode))
                r.append(mode)
                continue
            try:
                modeobj = modeobj(self, self._component, self._component_on, self._component_off)
            except Exception as e:
                _log.error("Error creating mode {!s} object: {!s}".format(mode, e))
                r.append(mode)
                continue
            self._modes_enabled.append(modeobj)
        if len(r) > 0:
            _log.error("Not supported modes found which will be ignored: {!s}".format(r))
        del r

    async def _init_network(self):
        for mode in self._modes_enabled:
            if hasattr(mode, "_init"):
                await mode._init()
        gc.collect()
        await super()._init_network()
        for mode in self._modes_enabled:
            # mode switches don't need to get retained state
            topic = "{!s}/{!s}/set".format(self._topic_mode[:-4], mode)
            _mqtt.subscribeSync(topic, self.changeMode, self)
        # get retained mode state.
        await _mqtt.unsubscribe(self._component._topic, self._component)
        _mqtt.subscribeSync(self._component._topic, self.on_message, self)
        _mqtt.subscribeSync(self._topic_mode, self.changeMode, self, check_retained_state=True)

    async def changeMode(self, topic, msg, retain):
        print("changeMode", topic, msg, retain, self._mode)
        async with self._mode_lock:
            if _mqtt.matchesSubscription(topic, self._topic_mode, ignore_command=True) and retain:
                # for retained state on state topic
                _mode = msg
                await _mqtt.unsubscribe(topic, self)
            elif retain:
                # retained switch states for the different modes don't matter.
                # State is restored by retained mode topic
                return False
            else:
                t = topic.rstrip("/set")
                _mode = t[t.rfind("/") + 1:]
                del t
            if msg in _mqtt.payload_off:
                if str(self._mode) == _mode:
                    _mode = None
                else:
                    raise TypeError("Mode {!s} was not active, can't deactivate".format(_mode))
            _cmode = self._mode
            if _mode == _cmode:
                return True  # already active
            for mode in self._modes_enabled:
                if str(mode) == _mode or _mode is None:
                    if _mode is None:
                        mode = Mode
                    if retain or await self._mode.deactivate(self, self._component,
                                                             self._component_on,
                                                             self._component_off):
                        if self._mode != Mode and retain is False:
                            # don't need to publish the disable of the default switch mode
                            topic = "{!s}/{!s}".format(self._topic_mode[:-4], self._mode)
                            await _mqtt.publish(topic, "OFF", qos=1, retain=True)
                        for modei in self._modes_enabled:
                            if modei != mode:
                                topic = "{!s}/{!s}".format(self._topic_mode[:-4], modei)
                                await _mqtt.publish(topic, "OFF", qos=1, retain=True)
                        if await mode.activate(self, self._component, self._component_on,
                                               self._component_off):
                            self._mode = mode
                            await _mqtt.publish(self._topic_mode[:-4], "{}".format(self._mode),
                                                qos=1, retain=True)
                            if retain:  # will otherwise be published by return True
                                topic = "{!s}/{!s}".format(self._topic_mode[:-4], self._mode)
                                await _mqtt.publish(topic, "ON", qos=1, retain=True)
                            return True
                        else:
                            topic = "{!s}/{!s}".format(self._topic_mode[:-4], mode)
                            await _mqtt.publish(topic, "OFF", qos=1, retain=True)
                            await Mode.activate(self, self._component, self._component_on,
                                                self._component_off)
                            self._mode = Mode
                            raise TypeError(
                                "Unable to activate mode {!s}, falling back to default".format(
                                    _mode))
                    else:
                        raise TypeError("Unable to disable old mode {!s}".format(self._mode))
            raise TypeError("mode {!s} is not supported/enabled".format(_mode))

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if memoryview(topic) == memoryview(self._component._topic)[:-4] and retain is False:
            return False
        if msg in _mqtt.payload_on:
            if self._component.state() is False:
                await self.on()
        elif msg in _mqtt.payload_off:
            if self._component.state() is True:
                await self.off()
        else:
            raise TypeError("Payload {!s} not supported".format(msg))
        return False  # will not publish the requested state to mqtt as already done by on()/off()

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        return await self._mode.on(self, self._component, self._component_on, self._component_off)

    async def off(self):
        """Turn switch off. Can be used by other components to control this component"""
        return await self._mode.off(self, self._component, self._component_on, self._component_off)

    async def toggle(self):
        """Toggle device state. Can be used by other component to control this component"""
        if self._component.state() is True:
            return await self.off()
        else:
            return await self.on()

    def state(self):
        return self._component.state()

    async def _discovery(self, register=True):
        count = self._component._count if hasattr(self._component, "_count") else ""
        for mode in self._modes_enabled:
            name = "{!s}{!s}_{!s}_{!s}".format(COMPONENT_NAME, count, "mode", mode)
            if register:
                await self._publishDiscovery(_COMPONENT_TYPE,
                                             "{!s}/{!s}".format(self._topic_mode[:-4], mode), name,
                                             DISCOVERY_SWITCH,
                                             "{!s} Mode {!s}".format(self._component._frn, mode))
            else:
                await self._deleteDiscovery(_COMPONENT_TYPE, name)
        name = "{!s}{!s}_{!s}".format(COMPONENT_NAME, count, "mode")
        if register:
            await self._publishDiscovery("sensor", self._topic_mode[:-4], name, "", self._frn_mode)
        else:
            await self._deleteDiscovery("sensor", name)
