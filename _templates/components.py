'''
Created on 01.06.2018

@author: Kevin Köck
'''

__version__ = "1.1"
__updated__ = "2018-08-31"

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

# Alternatively you can register components manually:

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio

_mqtt = config.getMQTT()
loop = asyncio.get_event_loop()
_log = logging.getLogger("components.py")

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


config.addComponent("mycomponent", someinstance)
# This is optional, it just puts your component in the dictionary where all registered components are


# The 3rd way is to just use this module to start whatever code you like
# and use the mqtt instance to subscribe/publish

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio

_mqtt = config.getMQTT()
loop = asyncio.get_event_loop()
_log = logging.getLogger("components.py")

# do whatever you want (don't do long blocking calls or start a synchronous endless loop)
