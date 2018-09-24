'''
Created on 2018-08-17

@author: Kevin Köck
'''

"""
example config:
{
    package: .listeners.switch
    component: Switch
    constructor_args: { 
        pin: D5                 # pin number, name or object
        on_object: led          # optional, object to call a function from when switch is ON
        on_function: blink      # optional, function or coroutine to call from on_object
        mqtt_topic: None        # optional, defaults to <home>/<device-id>/switch
        off_object: None        # optional, object to call a function from when switch is OFF, if not defined then on_function will be called
        off_function: None      # optional
        mqtt_publish: True      # optional, defaults to True; if false will not publish anything to mqtt
        debounce_ms: 50         # optional, defaults to 50ms
    }
}
IMPORTANT: the callback functions defined here will get the arguments None,<switch_state>,False as if they were called by mqtt
topic=None, msg=<button_state> ("ON"/"OFF"), retain=False
Prepare your code for this behaviour.
"""

__updated__ = "2018-08-17"
__version__ = "0.1"

from pysmartnode import config
from pysmartnode import logging
import gc
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.aswitch import Switch
import machine

_mqtt = config.getMQTT()
gc.collect()


def _checkFunction(obj, func):
    if obj is None and func is None:
        return None
    if hasattr(obj, func):
        return getattr(obj, func)
    raise TypeError("Object {!s} does not have function {!s}".format(obj, func))


async def wrapAction(func=None, topic=None, msg=None):
    func = [func] if type(func) != list else func
    for f in func:
        if f is not None:
            res = f(None, msg, False)
            if str(type(res)) == "<class 'generator'>":
                await res
    if topic is not None:
        topic = [topic] if type(topic) != list else topic
        for t in topic:
            await _mqtt.publish(t, msg, retain=True, qos=1)


class Button(Switch):
    def __init__(self, pin, on_object=None, on_function=None, mqtt_topic=None,
                 off_object=None, off_function=None, publish_mqtt=True, debounce_ms=None):
        super().__init__(Pin(pin, machine.Pin.PULL_UP))
        if debounce_ms is not None:
            self.debounce_ms = debounce_ms
        # if both func are None, status will still be published if publish_mqtt=True
        mqtt_topic = mqtt_topic or (_mqtt.getDeviceTopic("Switch") if publish_mqtt else None)
        on_func = _checkFunction(on_object, on_function)
        self.close_func(wrapAction, (on_func, mqtt_topic, "ON"))
        gc.collect()
        off_func = _checkFunction(off_object, off_function)
        if off_func is not None:
            self.open_func(wrapAction, (off_func, mqtt_topic, "OFF"))
        else:
            self.open_func(wrapAction, (on_func, mqtt_topic, "OFF"))
        gc.collect()
