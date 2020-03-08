'''
Created on 26.05.2018

@author: Kevin Köck
'''

__updated__ = "2019-10-26"

from pysmartnode import config
from pysmartnode import logging
import gc
import uasyncio as asyncio
import time
import machine
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
    import ntptime


    async def _sync():
        s = 1
        while True:
            print("Synchronize time from NTP server ...")
            try:
                ntptime.settime()
                gc.collect()
                tm = time.localtime()
                hour = tm[3] + config.RTC_TIMEZONE_OFFSET
                day = tm[2]
                if hour > 24:
                    hour -= 24
                    day += 1
                elif hour < 0:
                    hour += 24
                    day -= 1
                tm = tm[0:2] + (day,) + (0,) + (hour,) + tm[4:6] + (0,)
                machine.RTC().datetime(tm)
                print("Set time to", time.localtime())
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
