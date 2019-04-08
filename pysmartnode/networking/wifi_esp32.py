from pysmartnode import config
import gc
import uasyncio as asyncio
import time
import machine

if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE is True:
    async def _sync():
        import ntptime
        while True:
            print("Synchronize time from NTP server ...")
            try:
                ntptime.settime()
                gc.collect()
                tm = time.localtime()
                tm = tm[0:3] + (0,) + (tm[3] + config.RTC_TIMEZONE_OFFSET,) + tm[4:6] + (0,)
                machine.RTC().datetime(tm)
                await asyncio.sleep(18000)  # every 5h
            except Exception as e:
                print("Error syncing time: {!s}, retry in 1s".format(e))
                await asyncio.sleep(1)


    asyncio.get_event_loop().create_task(_sync())
    gc.collect()

if hasattr(config, "FTP_ACTIVE") and config.FTP_ACTIVE is True:
    print("FTP-Server active")
    import pysmartnode.libraries.ftpserver.ftp_thread
