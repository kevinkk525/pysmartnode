# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-08-19 

__updated__ = "2020-08-20"
__version__ = "0.2"

import ntptime
import time
import machine
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode import config
import gc
from sys import platform


async def sync():
    s = 1
    while True:

        print("Synchronize time from NTP server ...")
        try:
            ntptime.settime()
            gc.collect()
            tm = time.localtime()
            offset = 0
            if config.RTC_DAYLIGHT_SAVINGS:
                # snippet for daylight savings adapted from forum post of user "JumpZero"
                year = time.localtime()[0]  # get current year
                HHMarch = time.mktime((year, 3, (31 - (int(5 * year / 4 + 4)) % 7), 1, 0, 0, 0, 0,
                                       0))  # Time of March change to CEST
                HHOctober = time.mktime((year, 10, (31 - (int(5 * year / 4 + 1)) % 7), 1, 0, 0, 0,
                                         0, 0))  # Time of October change to CET
                now = time.time()
                if now < HHMarch:  # we are before last sunday of march
                    offset = 0  # only timezone change
                elif now < HHOctober:  # we are before last sunday of october
                    offset = 1
                else:  # we are after last sunday of october
                    offset = 0  # only timezone change
            day = tm[2]
            hour = tm[3] + config.RTC_TIMEZONE_OFFSET + offset
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
            await asyncio.sleep(18000 if platform != "esp8266" else 7200)  # every 5h, 2h esp8266
        except Exception as e:
            await logging.getLogger("wifi").asyncLog("error",
                                                     "Error syncing time: {!s}, retry in {!s}s".format(
                                                         e, s), timeout=10)
            await asyncio.sleep(s)
            s += 5
            # should prevent crashes because previous request was not finished and
            # sockets still open (Errno 98 EADDRINUSE). Got killed by WDT after a few minutes.
