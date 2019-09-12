# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-08 

"""
Example configuration:
{
    package: .machine.button
    component: Button
    constructor_args:
    {
      pin: 0
      # pull: null
      pressed_component: testswitch
      # pressed_method: "on"
      # released_component: testswitch
      # released_method: "off"
      # double_pressed_component: testswitch
      # double_pressed_method: "on"
      long_pressed_component: machine
      long_pressed_method: reset
    }
}

{
    package: .machine.button
    component: ToggleButton
    constructor_args:
    {
      pin: 0
      # pull: null
      pressed_component: testswitch
      # double_pressed_component: testswitch
      # double_pressed_method: "on"
      long_pressed_component: machine
      long_pressed_method: reset
    }
}
Careful: when having double press or long press active, rapid successive button activations
can lead to uasyncio queue overflow and crash the device.
This is due to how aswitch from Peter Hinch works.
"""

__updated__ = "2019-09-10"
__version__ = "0.2"

from pysmartnode import logging
from pysmartnode.utils.aswitch import Pushbutton
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.event import Event
import machine
import uasyncio as asyncio

loaded_components = {"machine": machine}  # so that button actions can be from these classes, e.g. machine.reset()

_component_name = "Button"

_log = logging.getLogger("button")


class Button(Pushbutton):
    def __init__(self, pin, pull=None, pressed_component=None, pressed_method="on",
                 released_component=None, released_method="off",
                 double_pressed_component=None, double_pressed_method="on",
                 long_pressed_component=None, long_pressed_method="on"):
        """
        :param pin: pin number or name
        :param pull: None for no pullup or pull_down, otherwise value of pull configuration
        :param pressed_component: component name of component to be turned on when button pressed
        :param pressed_method: string of the method of the component that is to be called
        :param released_component: component name of component to be turned on when button released
        :param released_method: string of the method of the component that is to be called
        :param double_pressed_component: component name of component to be turned on when button double pressed
        :param double_pressed_method: string of the method of the component that is to be called
        :param long_pressed_component: component name of component to be turned on when button long pressed
        :param long_pressed_method: string of the method of the component that is to be called
        """
        for comp in (pressed_component, released_component,
                     double_pressed_component, long_pressed_component):
            if type(comp) == str and comp not in loaded_components:
                raise TypeError("Component {!s} could not be found".format(comp))
        if type(pressed_component) == str:
            pressed_component = loaded_components[pressed_component]
        if type(released_component) == str:
            released_component = loaded_components[released_component]
        if type(double_pressed_component) == str:
            double_pressed_component = loaded_components[double_pressed_component]
        if type(long_pressed_component) == str:
            long_pressed_component = loaded_components[long_pressed_component]
        pin = Pin(pin, machine.Pin.IN, pull)
        super().__init__(pin, suppress=False)
        if pressed_component is not None:
            self.press_func(getattr(pressed_component, pressed_method))
        if released_component is not None:
            self.release_func(getattr(released_component, released_method))
        if double_pressed_component is not None:
            self.double_func(getattr(double_pressed_component, double_pressed_method))
        if long_pressed_component is not None:
            self.long_func(getattr(long_pressed_component, long_pressed_method))


class ToggleButton(Button):
    def __init__(self, pin, pull=None, pressed_component=None,
                 double_pressed_component=None, double_pressed_method="on",
                 long_pressed_component=None, long_pressed_method="on"):
        """
        Basic functionality for push is to toggle a device. Double press and long press are
        just extended functionality.
        :param pin: pin number or name
        :param pull: None for no pullup or pull_down, otherwise value of pull configuration
        :param pressed_component: component name of component to be turned on when button pressed
        :param double_pressed_component: component name of component to be turned on when button double pressed
        :param double_pressed_method: string of the method of the component that is to be called
        :param long_pressed_component: component name of component to be turned on when button long pressed
        :param long_pressed_method: string of the method of the component that is to be called
        """
        self._component = pressed_component
        self._event = Event()
        # Synchronous method _event.set() to prevent queue overflows from pressing button too often
        # Can still happen if double_press or long_press events are used due to the created coroutines
        # in aswitch.py
        super().__init__(pin, pull, self._event, "set",
                         None, "off",
                         double_pressed_component, double_pressed_method,
                         long_pressed_component, long_pressed_method)
        asyncio.get_event_loop().create_task(self._watcher())

    async def _watcher(self):
        while True:
            await self._event
            self._event.clear()
            await self._component.toggle()