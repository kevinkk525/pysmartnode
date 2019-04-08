'''
Created on 28.10.2017

@author: Kevin Köck
'''

__updated__ = "2018-09-18"
__version__ = "1.3"

import time
import gc
from pysmartnode import config
import network
import sys
import uasyncio as asyncio

gc.collect()


def connect():
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(config.WIFI_SSID, config.WIFI_PASSPHRASE)  # Connect to an AP
    # TODO: check redundancy as mqtt/communitcation library takes care of this already
    time.sleep(0.1)
    count = 0
    while wifi.isconnected() is False:  # Check for successful connection
        count += 1
        if count % 10 == 0:
            print("Connecting, {!r}".format(count / 10))
        time.sleep(0.1)
        if count >= 100:  # ESP32 sometimes takes a bit longer to connect to wifi, 10s is ok
            print("Error connecting to wifi, resetting device in 2s")
            import machine
            time.sleep(2)
            machine.reset()
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
