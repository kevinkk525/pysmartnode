'''
Created on 2018-08-17

@author: Kevin Köck
'''

"""
Unified Pin creation utility. Accepts pin number, name (for esp8266 NodeMCU) and Pin-Object.
This enables developers to use this object instead of checking if they received a pin number, string or object
and even set some default parameters like pull_up as these won't get used if a Pin-Object is received.
But as the machine.Pin can't be subclassed, pull_up has to be used like this: 
from pysmartnode.utils.pin import Pin
import machine

p=Pin("D0", machine.Pin.OUT, machine.Pin.PULL_UP)
"""

__updated__ = "2018-08-31"
__version__ = "0.2"

import machine
from sys import platform
import gc


def Pin(pin, *args, **kwargs):
    try:
        pin = int(pin)
        # just in case it gets a string that should be an integer
    except:
        pass
    if type(pin) == str:
        if platform == "esp8266":
            # generate dictionary on request so no RAM gets reserved all the time
            pins = {"D%i" % p: v for p, v in enumerate((16, 5, 4, 0, 2, 14, 12, 13, 15, 3, 1))}
        else:
            raise TypeError("Platform {!s} does not support string pin names like {!s}".format(platform, pin))
        if pin in pins:
            pin = pins[pin]
        else:
            raise TypeError("Pin name {!r} not found in dictionary".format(type(pin), pin))
        gc.collect()
    elif type(pin) != int:
        # assuming pin object
        return pin
    args = list(args)
    args.insert(0, pin)
    return machine.Pin(*args, **kwargs)
