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


async def _receiveConfig():
    await asyncio.sleep(2)
    _log.debug("RAM before import receiveConfig: {!s}".format(gc.mem_free()), local_only=True)
    import pysmartnode.components.machine.remoteConfig
    gc.collect()
    _log.debug("RAM after import receiveConfig: {!s}".format(gc.mem_free()), local_only=True)
    conf = pysmartnode.components.machine.remoteConfig.RemoteConfig()
    gc.collect()
    _log.debug("RAM after creating receiveConfig: {!s}".format(gc.mem_free()), local_only=True)
    while conf.done() is False:
        await asyncio.sleep(1)
    gc.collect()
    _log.debug("RAM before deleting receiveConfig: {!s}".format(gc.mem_free()), local_only=True)
    config.removeComponent(conf)
    del conf
    del pysmartnode.components.machine.remoteConfig
    del sys.modules["pysmartnode.components.machine.remoteConfig"]
    gc.collect()
    _log.debug("RAM after deleting receiveConfig: {!s}".format(gc.mem_free()), local_only=True)


services_started = False


def start_services(client):
    global services_started
    if services_started is False:
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
        if config.MQTT_RECEIVE_CONFIG is True:
            loop.create_task(_receiveConfig())
        else:
            loop.create_task(config._loadComponentsFile())
        services_started = True
        if sys.platform != "linux":
            import network
            s = network.WLAN(network.STA_IF)
            print("Connected, local ip {!r}".format(s.ifconfig()[0]))


def main():
    loop.create_task(_resetReason())
    print("free ram {!r}".format(gc.mem_free()))
    gc.collect()

    if hasattr(config, "USE_SOFTWARE_WATCHDOG") and config.USE_SOFTWARE_WATCHDOG:
        from pysmartnode.components.machine.watchdog import WDT

        wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2)
        config.addNamedComponent("wdt", wdt)

    if hasattr(config, "WIFI_LED") and config.WIFI_LED is not None:
        from pysmartnode.components.machine.wifi_led import WIFILED

        wl = WIFILED(config.WIFI_LED, config.WIFI_LED_ACTIVE_HIGH)
        config.addNamedComponent("wifi_led", wl)

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
