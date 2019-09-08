'''
Created on 28.10.2017

@author: Kevin Köck
'''

__updated__ = "2019-09-07"
__version__ = "1.5"

import time
import gc
from pysmartnode import config
import sys
import uasyncio as asyncio

if sys.platform != "linux":
    import network

gc.collect()


def connect():
    if sys.platform == "linux":  # nothing to connect or start on linux
        return True
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(config.WIFI_SSID, config.WIFI_PASSPHRASE)  # Connect to an AP
    # TODO: check redundancy as mqtt/communitcation library takes care of this already
    time.sleep(0.1)
    count = 0
    if hasattr(config, "WIFI_LED") is True and config.WIFI_LED is not None:
        from pysmartnode.components.machine.wifi_led import WIFILED
        wifi_led = WIFILED(config.WIFI_LED, config.WIFI_LED_ACTIVE_HIGH)
    else:
        wifi_led = None
    while wifi.isconnected() is False:  # Check for successful connection
        count += 1
        if count % 10 == 0:
            print("Connecting, {!r}".format(count / 10))
        time.sleep(0.1)
        if count >= 100:  # ESP32 sometimes takes a bit longer to connect to wifi, 10s is ok
            print("Error connecting to wifi, resetting device in 2s")
            if wifi_led is not None:
                for _ in range(5):
                    wifi_led.flash(500)
                    time.sleep_ms(500)
            else:
                time.sleep(2)
            import machine
            machine.reset()
    if wifi_led is not None:
        for _ in range(5):
            wifi_led.flash(50)
            time.sleep_ms(50)
    loop = asyncio.get_event_loop()
    loop.create_task(start_services(wifi))
    gc.collect()
    return wifi.isconnected()


async def start_services(wifi):
    while wifi.isconnected() is False:  # Check for successful connection
        await asyncio.sleep_ms(250)
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
    print("Connected, local ip {!r}".format(wifi.ifconfig()[0]))
