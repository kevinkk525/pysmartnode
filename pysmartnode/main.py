'''
Created on 10.08.2017

@author: Kevin Köck
'''

__updated__ = "2018-10-01"

import gc
import time

gc.collect()
print(gc.mem_free())

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import sys
import machine

_log = logging.getLogger("pysmartnode")
gc.collect()
rtc = machine.RTC()

loop = asyncio.get_event_loop()


async def _resetReason():
    # may be empty if eps8266 resets during reboot because of various reasons
    # (e.g. some of mine often keep rebooting 5 times until the start correctly and rtc.memory is empty then)
    if sys.platform == "esp8266" and rtc.memory() != b"":
        await _log.asyncLog("critical", "Reset reason: {!s}".format(rtc.memory().decode()))
        rtc.memory(b"")
    elif sys.platform == "esp32_LoBo" and rtc.read_string() != "":
        await _log.asyncLog("critical", "Reset reason: {!s}".format(rtc.memory()))
        rtc.write_string("")
    elif machine.reset_cause() == machine.WDT_RESET:
        await _log.asyncLog("critical", "Reset reason: WDT reset")


def main():
    loop.create_task(_resetReason())
    print("free ram {!r}".format(gc.mem_free()))
    import pysmartnode.networking.wifi
    pysmartnode.networking.wifi.connect()
    del pysmartnode.networking.wifi
    del sys.modules["pysmartnode.networking.wifi"]
    gc.collect()

    if hasattr(config, "USE_SOFTWARE_WATCHDOG") and config.USE_SOFTWARE_WATCHDOG:
        from pysmartnode.components.machine.watchdog import WDT

        wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2)
        config.addComponent("wdt", wdt)

    if config.MQTT_RECEIVE_CONFIG is False:
        loop.create_task(config.loadComponentsFile())

    print("Starting uasyncio loop")
    if config.DEBUG_STOP_AFTER_EXCEPTION:
        # want to see the exception trace in debug mode
        loop.run_forever()
    else:
        # just log the exception and reset the microcontroller
        try:
            loop.run_forever()
        except Exception as e:
            # may fail due to memory allocation error
            if sys.platform == "esp8266":
                try:
                    rtc.memory("{!s}".format(e).encode())
                except Exception as e:
                    print(e)
                print("{!s}".format(e).encode())
            elif sys.platform == "esp32_LoBo":
                rtc.write_string("{!s}".format(e))
            else:
                _log.critical("Loop error, {!s}".format(e))
            machine.reset()


main()
