'''
Created on 26.05.2018

@author: Kevin Köck
'''

from pysmartnode import config
import gc

if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
    import ntptime

    print("Synchronize time from NTP server ...")
    ntptime.settime()
    gc.collect()
