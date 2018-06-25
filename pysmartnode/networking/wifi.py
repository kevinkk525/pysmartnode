'''
Created on 28.10.2017

@author: Kevin Köck
'''

__updated__ = "2018-05-29"
__version__ = "1.2"

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
    global wifi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(config.WIFI_SSID, config.WIFI_PASSPHRASE)  # Connect to an AP
    time.sleep(0.1)
    count = 0
    while wifi.isconnected() is False:  # Check for successful connection
        count += 1
        if count % 10 == 0:
            print("Connecting, {!r}".format(count / 10))
        time.sleep(0.1)
        if count >= 50:
            print("Error connecting to wifi, resetting device in 2s")
            import machine
            time.sleep(2)
            machine.reset()
    loop = asyncio.get_event_loop()
    loop.create_task(start_services())
    gc.collect()
    return wifi.isconnected()


async def start_services():
    while wifi.isconnected() is False:  # Check for successful connection
        await asyncio.sleep_ms(250)
    if sys.platform == "esp32_LoBo":
        from . import wifi_esp32_lobo
    elif sys.platform == "esp8266":
        from . import wifi_esp8266
    print("Connected, local ip {!r}".format(wifi.ifconfig()[0]))
