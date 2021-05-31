# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-08-10

__updated__ = "2021-05-31"

import gc

gc.collect()
print(gc.mem_free())

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import sys
import os
import io
import machine

_log = logging.getLogger("main")


def _handle_exception(loop, context):
    s = io.StringIO()
    sys.print_exception(context["exception"], s)
    _log.error(s.getvalue())  # log exception to mqtt too


loop = asyncio.get_event_loop()
loop.set_exception_handler(_handle_exception)

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

print("free ram {!r}".format(gc.mem_free()))
gc.collect()

if config.WATCHDOG_LEVEL:
    from pysmartnode.components.machine.watchdog import WDT

    if config.WATCHDOG_LEVEL == 2:
        wdt = WDT(timeout=10, hard=True)
    else:
        wdt = WDT(timeout=config.MQTT_KEEPALIVE * 2, hard=False)
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
        s = io.StringIO()
        sys.print_exception(e, s)
        _log.critical("components.py:", s.getvalue())
    else:
        gc.collect()
        if hasattr(components, "COMPONENTS") and type(components.COMPONENTS) == dict:
            # load components even if network is unavailable as components
            # might not depend on it
            loop.create_task(config.registerComponent(components.COMPONENTS))


async def _resetReason():
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


def start_services(mqtt, state):
    if not state:  # Wifi disconnected
        return
    global services_started
    if services_started is False:
        if sys.platform == "esp32":
            import pysmartnode.networking.wifi_esp32
            del pysmartnode.networking.wifi_esp32
            del sys.modules["pysmartnode.networking.wifi_esp32"]
        elif sys.platform == "esp8266":
            import pysmartnode.networking.wifi_esp8266
            del pysmartnode.networking.wifi_esp8266
            del sys.modules["pysmartnode.networking.wifi_esp8266"]
        elif sys.platform == "pyboard":
            import pysmartnode.networking.wifi_pyboard
            del pysmartnode.networking.wifi_pyboard
            del sys.modules["pysmartnode.networking.wifi_pyboard"]
        if config.MQTT_RECEIVE_CONFIG:
            loop.create_task(_receiveConfig())
        services_started = True
        if sys.platform != "linux":
            import network
            s = network.WLAN(network.STA_IF)
            print("Connected, local ip {!r}".format(s.ifconfig()[0]))


def _start_loop():
    try:
        loop.run_forever()
    except Exception as e:
        try:
            config.getMQTT().close()
        except:
            pass
        if config.DEBUG_STOP_AFTER_EXCEPTION:
            # should actually never happen that the uasyncio main loop runs into an exception
            if config.WATCHDOG_LEVEL:
                wdt.deinit()  # so it doesn't reset the board
            raise e
        # just log the exception and reset the microcontroller
        with open("reset_reason.txt", "w") as f:
            s = io.StringIO()
            sys.print_exception(e, s)
            f.write(s.getvalue())
        machine.reset()


def main():
    print("free ram {!r}".format(gc.mem_free()))
    gc.collect()
    if sys.platform == "pyboard" and config.PIN3V3_ENABLED:
        machine.Pin(machine.Pin.board.EN_3V3).value(1)
    loop.create_task(_resetReason())
    config.getMQTT().registerWifiCallback(start_services)

    print("Starting uasyncio loop")
    if config.MAIN_LOOP_THREADED:
        import _thread
        _thread.stack_size(8192) # prevent recursion overflow
        _thread.start_new_thread(_start_loop, [])
    else:
        _start_loop()


main()
