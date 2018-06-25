'''
Created on 28.10.2017

@author: Kevin Köck
'''

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

__updated__ = "2018-06-02"
__version__ = "0.3"

from pysmartnode import config
import gc

"""
I2C-Autoconfiguration
"""


def I2C(SCL, SDA, FREQ=100000):
    from machine import I2C, Pin
    SCL = SCL if type(SCL) != str else config.pins[SCL]
    SDA = SDA if type(SDA) != str else config.pins[SDA]
    i2c = I2C(scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)
    gc.collect()
    return i2c
