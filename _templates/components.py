'''
Created on 01.06.2018

@author: Kevin Köck
'''

__version__ = "2.0"
__updated__ = "2019-10-20"

# Template for using components.py as a local component configuration

# Adapt dictionary to your needs or use alternatives below,
COMPONENTS = {
    "_order": ["i2c", "htu", "gpio"],
    "i2c":    {
        "package":          ".machine.i2c",
        "component":        "I2C",
        "constructor_args": {
            "SCL": "D6",
            "SDA": "D5"
        }
    },
    "htu":    {
        "package":          ".sensors.htu21d",
        "component":        "HTU21D",
        "constructor_args": {
            "i2c":             "i2c",
            "precision_temp":  2,
            "precision_humid": 1,
            "temp_offset":     -2.0,
            "humid_offset":    10.0
        }
    },
    "gpio":   {
        "package":          ".machine.easyGPIO",
        "component":        "GPIO",
        "constructor_args": {
            "discover_pins": ["D0", "D1", "D2"]
        }
    }
}

# Alternatively or additionally you can register components manually,
# which saves a lot of RAM as no dict doesn't get loaded into RAM.
# This example provides the same configuration as the COMPONENT dict above:

from pysmartnode import config
import gc

gc.collect()
from pysmartnode.components.machine.i2c import I2C

gc.collect()  # It's important to call gc.collect() to keep the RAM fragmentation to a minimum
from pysmartnode.components.sensors.htu21d import HTU21D

gc.collect()
from pysmartnode.components.machine.easyGPIO import GPIO

gc.collect()

i2c = I2C(SCL="D6", SDA="D5")
config.addComponent("i2c", i2c)
gc.collect()
htu = HTU21D(i2c, precision_temp=2, precision_humid=1, temp_offset=-2.0, humid_offset=10.0)
config.addComponent("htu", htu)
gc.collect()
gpio = GPIO(discover_pins=["D0", "D1", "D2"])
config.addComponent("gpio", gpio)  # This is optional, it just puts
# your component in the dictionary where all registered components are.
