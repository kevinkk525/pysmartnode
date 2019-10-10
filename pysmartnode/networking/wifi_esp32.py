from pysmartnode import config
import gc
import uasyncio as asyncio
import time
import machine
from pysmartnode.utils.sys_vars import getDeviceID
import network
import sys
from pysmartnode import logging

__updated__ = "2019-10-02"

try:
    s = network.WLAN(network.STA_IF)
    s.config(dhcp_hostname="{}{}".format("ESP32_", getDeviceID()))
except Exception as e:
    print(e)  # not important enough to do anything about it

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

if hasattr(config, "FTP_ACTIVE") and config.FTP_ACTIVE is True:
    if hasattr(config, "WEBREPL_ACTIVE") and config.WEBREPL_ACTIVE is True:
        config._log.critical("ftpserver background can't be used with webrepl")
    else:
        print("FTP-Server active")
        import pysmartnode.libraries.ftpserver.ftp_thread
