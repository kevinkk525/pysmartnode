# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-28

COMPONENT_NAME = "I2C"

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

__updated__ = "2020-10-25"
__version__ = "0.5"

import gc

"""
Easy I2C-creation
"""


def SoftI2C(SCL, SDA, FREQ=100000):
    from machine import SoftI2C
    from pysmartnode.components.machine.pin import Pin
    i2c = SoftI2C(scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)
    gc.collect()
    return i2c


I2C = SoftI2C  # compatibility to old code

# Changed to SoftI2C with commit
# https://github.com/micropython/micropython/commit/39d50d129ce428858332523548f0594503d0f45b
