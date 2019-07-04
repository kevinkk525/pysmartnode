'''
Created on 01.06.2018

@author: Kevin Köck
'''

__version__ = "1.2"
__updated__ = "2018-10-01"

# Template for using components.py as a local component configuration or a starting point for own scripts

# Adapt dictionary to your needs or use alternatives below,
# _order only needed if one component depends on another being initialized first
COMPONENTS = {
    "_order": ["i2c", "htu"],
    "i2c": {
        "package": ".machine.i2c",
        "component": "I2C",
        "constructor_args": ["D6", "D5"]
    },
    "htu": {
        "package": ".sensors.htu21d",
        "component": "HTU21D",
        "constructor_args": {
            "i2c": "i2c",
            "precision_temp": 2,
            "precision_humid": 1,
            "temp_offset": -2.0,
            "humid_offset": 10.0
        }
    }
}

# Alternatively you can register components manually, which is a lot better as it saves a lot of RAM:

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio

_mqtt = config.getMQTT()
loop = asyncio.get_event_loop()
_log = logging.getLogger("components.py")


async def main():
    await asyncio.sleep(2)  # use this to ensure that everything else is loaded and not needed modules unloaded.
    try:
        import somemodule
    except Exception as e:
        _log.error("Can't import module, error {!s}".format(e))

    someinstance = somemodule.Someclass(pin=35)
    loop.create_task(someinstance.getTemperatureContinuosly())

    from pysmartnode.utils.wrappers.callRegular import callRegular, callRegularPublish

    loop.create_task(callRegular(someinstance.getTemperature, interval=600))
    # This is an alternative if <someinstance> does not provide a coroutine that checks temperature periodically.
    # callRegular() calls a coroutine or function periodically in the given interval.
    # The someinstance function still has to take care of publishing its values.
    # This can be done by using the mqtt.publish coroutine or the mqtt.schedulePublish synchronous function

    loop.create_task(callRegularPublish(someinstance.getTemperature, ".mymodule/temperature",
                                        interval=None, retain=None, qos=None))
    # This function allows you to periodically read a sensor and publish its value to the given
    # mqtt topic without any additional effort. (mqtt topic starting with "." is "<home>/<device-id>/"

    config.addNamedComponent("mycomponent", someinstance)
    # This is optional, it just puts your component in the dictionary where all registered components are


asyncio.get_event_loop().create_task(main())

# this is a real example of a components.py that I used:
"""
import uasyncio as asyncio

async def main():
    await asyncio.sleep(2)
    from pysmartnode import config
    import machine
    import gc

    def __printRAM(start, info=""):
        print(info, "Mem free", gc.mem_free(), "diff:", gc.mem_free() - start)

    gc.collect()
    _mem = gc.mem_free()
    __printRAM(_mem, "start")

    await asyncio.sleep_ms(200)
    from pysmartnode.components.machine.pin import Pin

    gc.collect()
    __printRAM(_mem, "pin imported")

    i2c = machine.I2C(scl=Pin("D6"), sda=Pin("D5"))
    config.addComponent("i2c", i2c)
    gc.collect()
    __printRAM(_mem, "i2c created")

    await asyncio.sleep_ms(200)
    from pysmartnode.components.sensors.htu21d import HTU21D

    gc.collect()
    htu = HTU21D(i2c, 2, 1, -2.0, 10.0)
    gc.collect()
    __printRAM(_mem, "htu created")

    await asyncio.sleep_ms(200)
    from pysmartnode.components.machine.easyGPIO import gpio

    gc.collect()
    await gpio()
    gc.collect()
    __printRAM(_mem, "gpio created")

    await asyncio.sleep_ms(200)
    from pysmartnode.components.machine.ram import ram

    gc.collect()
    ram()
    gc.collect()
    __printRAM(_mem, "ram created")


asyncio.get_event_loop().create_task(main())
"""
