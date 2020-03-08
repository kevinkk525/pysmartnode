from pysmartnode import config
import gc
import uasyncio as asyncio
import time
import machine
from pysmartnode.utils.sys_vars import getDeviceID
import network
from pysmartnode import logging

__updated__ = "2019-10-26"

try:
    s = network.WLAN(network.STA_IF)
    s.config(dhcp_hostname="{}{}".format("ESP32_", getDeviceID()))
except Exception as e:
    print(e)  # not important enough to do anything about it

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

if hasattr(config, "FTP_ACTIVE") and config.FTP_ACTIVE is True:
    if hasattr(config, "WEBREPL_ACTIVE") and config.WEBREPL_ACTIVE is True:
        config._log.critical("ftpserver background can't be used with webrepl")
    else:
        print("FTP-Server active")
        import pysmartnode.libraries.ftpserver.ftp_thread
