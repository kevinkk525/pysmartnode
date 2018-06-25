'''
Created on 10.08.2017

@author: Kevin Köck
'''

__updated__ = "2018-04-16"

import gc
import time

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.networking import wifi
import uasyncio as asyncio

log = logging.getLogger("pysmartnode")
gc.collect()

loop = asyncio.get_event_loop()


async def await_last_log():
    await asyncio.sleep(10)
    import machine
    machine.reset()


print("free ram {!r}".format(gc.mem_free()))
wifi.connect()

if hasattr(config, "USE_SOFTWARE_WATCHDOG") and config.USE_SOFTWARE_WATCHDOG:
    from pysmartnode.components.machine.watchdog import WDT

    wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2)
    config.addComponent("wdt", wdt)

print("Starting uasyncio loop")
if config.DEBUG_STOP_AFTER_EXCEPTION:
    # want to see the exception trace in debug mode
    loop.run_forever()
else:
    # just log the exception and reset the microcontroller
    while True:
        try:
            loop.run_forever()
        except Exception as e:
            time.sleep(5)
            log.critical("Loop error, {!s}".format(e))
            loop.create_task(await_last_log())
loop.close()
