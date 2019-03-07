'''
Created on 2018-08-17

@author: Kevin Köck
'''

"""
example config:
{
    package: .listeners.button
    component: Button
    constructor_args: { 
        pin: D5                     # pin number, name or object
        press_object: led           # optional, object to call a function from when pressing button
        press_function: blink       # optional, function or coroutine to call from press_object when pushing button
        press_topic: None           # optional, defaults to <home>/<device-id>/button, used if push_function is defined or topic changed
        release_object: None        # optional, object to call a function from when releasing button
        release_function: None      # optional, like push
        release_topic: None         # optional, will publish to all topics that were given on other events (where "ON" will be published)
        double_press_object: None   # optional, like push only on double press
        double_press_func: None     # optional, like push
        double_press_topic: None    # optional, defaults to <home>/<device-id>/button
        long_press_object: None     # optional, like push only on long press
        long_press_func: None       # optional, like push
        long_press_topic: None      # optional, defaults to <home>/<device-id>/button
        mqtt_publish: True          # optional, defaults to True; if false will not publish anything to mqtt; manually defining topic will publish that only
        debounce_ms: 50             # optional, defaults to 50ms
        long_press_ms: 1000         # optional, defaults to 1000ms
        double_click_ms: 400        # optional, defaults to 400ms
    }
}
IMPORTANT: the callback functions defined here will get the arguments None,<button_state>,False as if they were called by mqtt
topic=None, msg=<button_state> ("ON"/"OFF"), retain=False
This also means that all functions defined will also be called on release of the button with button_state "OFF".
Prepare your code for this behaviour.
"""

__updated__ = "2018-08-17"
__version__ = "0.1"

from pysmartnode import config
from pysmartnode import logging
import gc
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.aswitch import Pushbutton
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
            await _mqtt.publish(t, msg, qos=1, retain=True)


class Button(Pushbutton):
    def __init__(self, pin, press_object=None, press_function=None, press_topic=None,
                 release_object=None, release_function=None, release_topic=None,
                 double_press_object=None, double_press_function=None, double_press_topic=None,
                 long_press_object=None, long_press_function=None, long_press_topic=None,
                 publish_mqtt=True, debounce_ms=None, long_press_ms=None, double_click_ms=None):
        super().__init__(Pin(pin, machine.Pin.PULL_UP))
        if debounce_ms is not None:
            self.debounce_ms = debounce_ms
        if long_press_ms is not None:
            self.long_press_ms = long_press_ms
        if double_click_ms is not None:
            self.double_click_ms = double_click_ms
        r_func = _checkFunction(release_object, release_function)
        r_func = [r_func] if r_func is not None else []
        r_topic = [release_topic] if release_topic is not None else []
        self.release_func(wrapAction, (r_func, r_topic, "OFF"))
        gc.collect()
        p_func = _checkFunction(press_object, press_function)
        press_topic = press_topic or (_mqtt.getDeviceTopic("Button") if publish_mqtt else None)
        if p_func is not None:
            self.press_func(wrapAction, (p_func, press_topic, "ON"))
            if p_func not in r_func:
                r_func.append(p_func)
            if publish_mqtt and press_topic not in r_topic:
                r_topic.append(press_topic)
        gc.collect()
        d_func = _checkFunction(double_press_object, double_press_function)
        if d_func is not None:
            double_press_topic = double_press_topic or (_mqtt.getDeviceTopic("Button") if publish_mqtt else None)
            self.double_func(wrapAction, (d_func, double_press_topic, "ON"))
            if d_func not in r_func:
                r_func.append(d_func)
            if publish_mqtt and double_press_topic not in r_topic:
                r_topic.append(double_press_topic)
        gc.collect()
        l_func = _checkFunction(long_press_object, long_press_function)
        if l_func is not None:
            long_press_topic = long_press_topic or (_mqtt.getDeviceTopic("Button") if publish_mqtt else None)
            self.long_func(wrapAction, (l_func, long_press_topic, "ON"))
            if l_func not in r_func:
                r_func.append(l_func)
            if publish_mqtt and long_press_topic not in r_topic:
                r_topic.append(long_press_topic)
        gc.collect()
        # handle cases where no functions are given
        if publish_mqtt and p_func is None and r_func is None and d_func is None and l_func is None:
            # if no functions are given but mqtt should publish, add press_topic to release topics to get correct button state published
            if press_topic not in r_topic:
                r_topic.append(press_topic)
        if publish_mqtt and p_func is None and r_func is None and d_func is None and l_func is None:
            # if no functions are given but mqtt should publish, listen to press events
            self.press_func(wrapAction, (p_func, press_topic, "ON"))
