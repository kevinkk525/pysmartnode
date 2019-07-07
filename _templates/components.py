'''
Created on 01.06.2018

@author: Kevin Köck
'''

__version__ = "1.3"
__updated__ = "2019-07-07"

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
    #
    # WARNING: The following are helper functions only used with modules that are not built on top of utils/component.py
    #          as a base class and therefore also don't support home-assistant mqtt discovery and mqtt subscriptions.
    #          These are non-standard workarounds. It is better to re-implement those libraries properly.
    #          However if it is a sensor and mqtt discovery and mqtt subscriptions are not needed, this could be useful.
    #
    ####################################################################################################################

    from pysmartnode.utils.wrappers.callRegular import callRegular, callRegularPublish

    loop.create_task(callRegular(someinstance.getTemperature, interval=600))
    # This is an alternative if <someinstance> does not provide a coroutine that checks temperature periodically.
    # callRegular() calls a coroutine or function periodically in the given interval.
    # The someinstance function still has to take care of publishing its values.
    # This can be done by using the mqtt.publish coroutine or the mqtt.schedulePublish synchronous function

    loop.create_task(callRegularPublish(someinstance.getTemperature, ".mymodule/temperature",
                                        interval=None, retain=None, qos=None))
    # This function allows you to periodically read a sensor and publish its value to the given
    # mqtt topic without any additional effort. (mqtt topic starting with "." is "<home>/<device-id>/").
    # Interval None defaults to pysmartnode.config.INTERVAL_SEND_SENSOR

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
