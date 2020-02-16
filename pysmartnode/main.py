# Author: Kevin Köck
# Copyright Kevin Köck 2017-2019 Released under the MIT license
# Created on 2017-08-10

__updated__ = "2019-11-11"

import gc

gc.collect()
print(gc.mem_free())

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import sys
import os

if sys.platform != "linux":
    import machine

    rtc = machine.RTC()

_log = logging.getLogger("main")

if config.WEBREPL_ACTIVE:
    try:
        import webrepl_cfg
    except ImportError:
        try:
            with open("webrepl_cfg.py", "w") as f:
                f.write("PASS = %r\n" % config.WEBREPL_PASSWORD)
        except Exception as e:
            _log.critical("Can't start webrepl: {!s}".format(e), local_only=True)
    try:
        import webrepl

        webrepl.start()
    except Exception as e:
        _log.critical("Can't start webrepl: {!s}".format(e))
    # webrepl started here to start it as quickly as possible.

gc.collect()

loop = asyncio.get_event_loop()

print("free ram {!r}".format(gc.mem_free()))
gc.collect()

if hasattr(config, "USE_SOFTWARE_WATCHDOG") and config.USE_SOFTWARE_WATCHDOG:
    from pysmartnode.components.machine.watchdog import WDT

    wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2)
    config.addComponent("wdt", wdt)
    gc.collect()

if config.WIFI_LED is not None:
    from pysmartnode.components.machine.wifi_led import WIFILED

    wl = WIFILED(config.WIFI_LED, config.WIFI_LED_ACTIVE_HIGH)
    config.addComponent("wifi_led", wl)
    gc.collect()

if not config.MQTT_RECEIVE_CONFIG:  # otherwise ignore as config will be received
    try:
        import components
    except ImportError:
        _log.critical("components.py does not exist")
    except Exception as e:
        _log.critical("components.py:", e)
    else:
        gc.collect()
        if hasattr(components, "COMPONENTS") and type(components.COMPONENTS) == dict:
            # load components even if network is unavailable as components
            # might not depend on it
            loop.create_task(config.registerComponent(components.COMPONENTS))


async def _resetReason():
    if sys.platform == "esp8266" and rtc.memory() != b"":
        await _log.asyncLog("critical", "Reset reason:", rtc.memory().decode())
        rtc.memory(b"")
    else:
        if "reset_reason.txt" not in os.listdir():
            return
        with open("reset_reason.txt", "r") as f:
            await _log.asyncLog("critical", "Reset reason:", f.read())
        os.remove("reset_reason.txt")


async def _receiveConfig():
    await asyncio.sleep(2)
    _log.debug("RAM before import receiveConfig:", gc.mem_free(), local_only=True)
    import pysmartnode.components.machine.remoteConfig
    gc.collect()
    _log.debug("RAM after import receiveConfig:", gc.mem_free(), local_only=True)
    conf = pysmartnode.components.machine.remoteConfig.RemoteConfig()
    gc.collect()
    _log.debug("RAM after creating receiveConfig:", gc.mem_free(), local_only=True)
    while not conf.done():
        await asyncio.sleep(1)
    gc.collect()
    _log.debug("RAM before deleting receiveConfig:", gc.mem_free(), local_only=True)
    await conf.removeComponent(conf)  # removes component from Component chain
    del conf
    del pysmartnode.components.machine.remoteConfig
    del sys.modules["pysmartnode.components.machine.remoteConfig"]
    gc.collect()
    _log.debug("RAM after deleting receiveConfig:", gc.mem_free(), local_only=True)


services_started = False


def start_services(state):
    if not state:  # Wifi disconnected
        return
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
        if config.MQTT_RECEIVE_CONFIG:
            loop.create_task(_receiveConfig())
        services_started = True
        if sys.platform != "linux":
            import network
            s = network.WLAN(network.STA_IF)
            print("Connected, local ip {!r}".format(s.ifconfig()[0]))


def main():
    print("free ram {!r}".format(gc.mem_free()))
    gc.collect()
    loop.create_task(_resetReason())
    config.getMQTT().registerWifiCallback(start_services)

    print("Starting uasyncio loop")
    try:
        loop.run_forever()
    except Exception as e:
        try:
            config.getMQTT().close()
        except:
            pass
        if config.DEBUG_STOP_AFTER_EXCEPTION:
            # want to see the exception trace in debug mode
            if config.USE_SOFTWARE_WATCHDOG:
                wdt.deinit()  # so it doesn't reset the board
            raise e
        # just log the exception and reset the microcontroller
        if sys.platform == "esp8266":
            try:
                rtc.memory("{!s}".format(e).encode())
            except Exception as e:
                print(e)
            print("{!s}".format(e).encode())
        else:
            with open("reset_reason.txt", "w") as f:
                f.write(e)
        machine.reset()


main()
