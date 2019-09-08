'''
Created on 26.05.2018

@author: Kevin Köck
'''

__updated__ = "2019-08-27"

from pysmartnode import config
import gc
import uasyncio as asyncio
import sys
import time
import machine

if hasattr(config, "WIFI_SLEEP_MODE") and config.WIFI_SLEEP_MODE is not None:
    import esp

    esp.sleep_type(config.WIFI_SLEEP_MODE)  # optionally disable wifi sleep to improve wifi reliability

if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE is True:
    async def _sync():
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
                await asyncio.sleep(18000)  # every 5h
            except Exception as e:
                print("Error syncing time: {!s}, retry in 1s".format(e))
                await asyncio.sleep(1)


    asyncio.get_event_loop().create_task(_sync())
    gc.collect()
