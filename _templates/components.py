'''
Created on 01.06.2018

@author: Kevin Köck
'''

__version__ = "1.3"
__updated__ = "2019-07-07"

# TODO: update as some methods are not supported or recommended anymore

# Template for using components.py as a local component configuration or a starting point for own scripts

# Adapt dictionary to your needs or use alternatives below,
# _order only needed if one component depends on another being initialized first
COMPONENTS = {
    "_order": ["i2c", "htu", "gpio"],
    "i2c":    {
        "package":          ".machine.i2c",
        "component":        "I2C",
        "constructor_args": ["D6", "D5"]
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

# Alternatively you can register components manually, which saves a lot of RAM as the dict doesn't get loaded into RAM:

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio

loop = asyncio.get_event_loop()
_log = logging.getLogger("components.py")


async def main():
    await asyncio.sleep(2)  # waiting period so RAM can settle and network connect
    try:
        import somemodule
    except Exception as e:
        _log.error("Can't import module, error {!s}".format(e))

    someinstance = somemodule.Someclass(pin=35)
    loop.create_task(someinstance.getTemperatureContinuosly())  # if someinstance doesn't start the method itself

    config.addNamedComponent("mycomponent", someinstance)
    # This is optional, it just puts your component in the dictionary where all registered components are

    ####################################################################################################################


asyncio.get_event_loop().create_task(main())

# this is a real example of a components.py that could be used instead of the COMPONENTS dictionary:
"""
import uasyncio as asyncio

async def main():
    await asyncio.sleep(2)
    from pysmartnode import config
    import machine
    import gc

    await asyncio.sleep_ms(200)
    from pysmartnode.components.machine.pin import Pin

    i2c = machine.I2C(scl=Pin("D6"), sda=Pin("D5"))
    config.addComponent("i2c", i2c)
    gc.collect()

    await asyncio.sleep_ms(200)
    from pysmartnode.components.sensors.htu21d import HTU21D

    gc.collect()
    htu = HTU21D(i2c, 2, 1, -2.0, 10.0)
    gc.collect()

    await asyncio.sleep_ms(200)
    from pysmartnode.components.machine.easyGPIO import GPIO
    gpio = GPIO(discover_pins=["D0","D1","D2"]) # pin names only for esp8266

    gc.collect()


asyncio.get_event_loop().create_task(main())
"""
