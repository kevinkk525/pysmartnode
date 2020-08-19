'''
Created on 26.05.2018

@author: Kevin Köck
'''

__updated__ = "2020-03-08"

from pysmartnode import config
import gc
import uasyncio as asyncio
from pysmartnode.utils.sys_vars import getDeviceID
import network

try:
    s = network.WLAN(network.STA_IF)
    s.config(dhcp_hostname="{}{}".format("ESP8266_", getDeviceID()))
except Exception as e:
    print(e)  # not important enough to do anything about it

if config.WIFI_SLEEP_MODE is not None:
    import esp

    esp.sleep_type(config.WIFI_SLEEP_MODE)

if config.RTC_SYNC_ACTIVE:
    from .ntp import sync

    asyncio.create_task(sync())
    gc.collect()
