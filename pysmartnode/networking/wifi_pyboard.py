from pysmartnode import config
import gc
import uasyncio as asyncio
from pysmartnode.utils.sys_vars import getDeviceID
import network

__updated__ = "2021-05-03"

try:
    s = network.WLAN(network.STA_IF)
    s.config(dhcp_hostname="{}{}".format("PYBOARD_", getDeviceID()))
except Exception as e:
    print(e)  # not important enough to do anything about it

if config.RTC_SYNC_ACTIVE:
    from .ntp import sync

    asyncio.create_task(sync())
    gc.collect()

if hasattr(config, "FTP_ACTIVE") and config.FTP_ACTIVE is True:
    if config.WEBREPL_ACTIVE is True:
        try:
            import _thread
        except:
            import pysmartnode.libraries.ftpserver.uftpd
        else:
            print("FTP-Server active")
            import pysmartnode.libraries.ftpserver.ftp_thread
    else:
        print("FTP-Server active")
        import pysmartnode.libraries.ftpserver.ftp_thread
