'''
Created on 28.10.2017

@author: Kevin Köck
'''

_component_name = "I2C"

"""
example config:
{
    package: .machine.i2c
    component: I2C
    constructor_args: {
        SCL: D4
        SDA: 4
        #FREQ: 100000     #optional, defaults to 100000
    }
}

"""

__updated__ = "2018-08-18"
__version__ = "0.4"

import gc

"""
Easy I2C-creation
"""


def I2C(SCL, SDA, FREQ=100000):
    from machine import I2C
    from pysmartnode.components.machine.pin import Pin
    i2c = I2C(scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)
    gc.collect()
    return i2c
