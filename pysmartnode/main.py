'''
Created on 10.08.2017

@author: Kevin Köck
'''

__updated__ = "2019-09-10"

import gc

gc.collect()
print(gc.mem_free())

from pysmartnode import config

if hasattr(config, "WEBREPL_ACTIVE") and config.WEBREPL_ACTIVE is True:
    try:
        import webrepl_cfg
    except:
        with open("webrepl_cfg.py", "w") as f:
            f.write("PASS = %r\n" % config.WEBREPL_PASSWORD)
    import webrepl

    webrepl.start()
    # webrepl started here to start it as quickly as possible.

from pysmartnode import logging
import uasyncio as asyncio
import sys
import os

if sys.platform != "linux":
    import machine

    rtc = machine.RTC()

_log = logging.getLogger("pysmartnode")
gc.collect()

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
    elif sys.platform == "linux":
        if "reset_reason.txt" not in os.listdir():
            return
        with open("reset_reason.txt", "r") as f:
            await _log.asyncLog("critical", "Reset reason: {!s}".format(f.read()))
        with open("reset_reason.txt", "w") as f:
            f.write("")
    elif machine.reset_cause() == machine.WDT_RESET:
        await _log.asyncLog("critical", "Reset reason: WDT reset")


services_started = False


def start_services(client):
    global services_started
    if services_started is False:
        import network
        s = network.WLAN(network.STA_IF)
        if sys.platform == "esp32_LoBo":
            import pysmartnode.networking.wifi_esp32_lobo
            del pysmartnode.networking.wifi_esp32_lobo
            del sys.modules["pysmartnode.networking.wifi_esp32_lobo"]
        elif sys.platform == "esp32":
            import pysmartnode.networking.wifi_esp32
            del pysmartnode.networking.wifi_esp32
            del sys.modules["pysmartnode.networking.wifi_esp32"]
        elif sys.platform == "esp8266":
            import pysmartnode.networking.wifi_esp8266
            del pysmartnode.networking.wifi_esp8266
            del sys.modules["pysmartnode.networking.wifi_esp8266"]
        services_started = True
        print("Connected, local ip {!r}".format(s.ifconfig()[0]))


def main():
    loop.create_task(_resetReason())
    print("free ram {!r}".format(gc.mem_free()))
    gc.collect()

    if hasattr(config, "USE_SOFTWARE_WATCHDOG") and config.USE_SOFTWARE_WATCHDOG:
        from pysmartnode.components.machine.watchdog import WDT

        wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2)
        config.addNamedComponent("wdt", wdt)

    if config.MQTT_RECEIVE_CONFIG is False:
        loop.create_task(config._loadComponentsFile())

    config.getMQTT().registerConnectedCallback(start_services)

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
            elif sys.platform == "linux":
                with open("reset_reason.txt", "w") as f:
                    f.write(e)
            else:
                _log.critical("Loop error, {!s}".format(e))
            machine.reset()


main()
