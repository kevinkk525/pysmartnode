'''
Created on 20.03.2018

@author: Kevin Köck
'''

from pysmartnode import config
import machine
import network
import time

if hasattr(config, "RTC_SYNC_ACTIVE") and config.RTC_SYNC_ACTIVE:
    rtc = machine.RTC()
    print("Synchronize time from NTP server ...")
    rtc.ntp_sync(server=config.RTC_SERVER, update_period=36000, tz=config.RTC_TIMEZONE)  # update every 10h
    tmo = 100
    while not rtc.synced():
        time.sleep_ms(100)
        tmo -= 1
        if tmo == 0:
            break
if config.MDNS_ACTIVE:
    print("Activating mDNS")
    mdns = network.mDNS()
    mdns.start(config.MDNS_HOSTNAME, config.MDNS_DESCRIPTION)
if config.FTP_ACTIVE:
    print("FTP-Server active")
    network.ftp.start()
    if config.MDNS_ACTIVE:
        mdns.addService('_ftp', '_tcp', 21, "MicroPython", {
            "board": "ESP32", "service": "mPy FTP File transfer", "passive": "True"})
if config.TELNET_ACTIVE:
    print("Telnet active")
    network.telnet.start()
    if config.MDNS_ACTIVE:
        mdns.addService('_telnet', '_tcp', 23, "MicroPython", {
            "board": "ESP32", "service": "mPy Telnet REPL"})
