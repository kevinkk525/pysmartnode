'''
Created on 26.05.2018

@author: Kevin Köck
'''

__updated__ = "2019-09-29"

from pysmartnode import config
from pysmartnode import logging
import gc
import uasyncio as asyncio
import sys
import time
import machine
from pysmartnode.utils.sys_vars import getDeviceID
import network

try:
    s = network.WLAN(network.STA_IF)
    s.config(dhcp_hostname="{}{}".format("ESP8266_", getDeviceID()))
except Exception as e:
    print(e)  # not important enough to do anything about it

if hasattr(config, "WIFI_SLEEP_MODE") and config.WIFI_SLEEP_MODE is not None:
    import esp

    esp.sleep_type(
        config.WIFI_SLEEP_MODE)  # optionally disable wifi sleep to improve wifi reliability

if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE is True:
    async def _sync():
        s = 1
        while True:
            import ntptime
            print("Synchronize time from NTP server ...")
            try:
                ntptime.settime()
                gc.collect()
                tm = time.localtime()
                tm = tm[0:3] + (0,) + (tm[3] + config.RTC_TIMEZONE_OFFSET,) + tm[4:6] + (0,)
                machine.RTC().datetime(tm)
                del ntptime
                del sys.modules["ntptime"]
                s = 1
                await asyncio.sleep(18000)  # every 5h
            except Exception as e:
                await logging.getLogger("wifi").asyncLog("error",
                                                         "Error syncing time: {!s}, retry in {!s}s".format(
                                                             e, s))
                await asyncio.sleep(s)
                s += 5
                # should prevent crashes because previous request was not finished and
                # sockets still open (Errno 98 EADDRINUSE). Got killed by WDT after a few minutes.


    asyncio.get_event_loop().create_task(_sync())
    gc.collect()
