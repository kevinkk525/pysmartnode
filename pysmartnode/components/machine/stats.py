# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-28 

# This component will be started automatically to provide basic device statistics.
# You don't need to configure it to be active.

__updated__ = "2019-09-29"
__version__ = "0.6"

import gc

from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component import Component, TIMELAPSE_TYPE, DISCOVERY_SENSOR
import time
from sys import platform
from pysmartnode import logging

if platform != "linux":
    import network

gc.collect()

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "STATS"
####################

_mqtt = config.getMQTT()

RAM_TYPE = '"unit_of_meas":"bytes",' \
           '"val_tpl":"{{value|int}}",' \
           '"ic":"mdi:memory",'

CONN_TYPE = '"dev_cla":"connectivity",' \
            '"pl_on":"online",' \
            '"pl_off":"offline",'

VERSION_TYPE = '"ic":"mdi:language-python-text",'


class STATS(Component):
    def __init__(self):
        super().__init__(COMPONENT_NAME, __version__)
        self._interval = config.INTERVAL_SEND_SENSOR

    async def _init_network(self):
        await super()._init_network()
        await _mqtt.publish(_mqtt.getDeviceTopic("version"), config.VERSION, qos=1, retain=True)
        if config.RTC_SYNC_ACTIVE is True:
            for _ in range(5):
                if time.localtime()[0] == 2000:  # not synced
                    await asyncio.sleep(1)
            t = time.localtime()  # polling earlier might not have synced.
            await _mqtt.publish(_mqtt.getDeviceTopic("last_boot"),
                                "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2],
                                                                               t[3],
                                                                               t[4],
                                                                               t[5]), qos=1,
                                retain=True)
        await self._loop()  # can be started here as everything depends on mqtt

    async def _loop(self):
        await asyncio.sleep(20)
        if platform != "linux":
            s = network.WLAN(network.STA_IF)
        else:
            s = None
        while True:
            gc.collect()
            logging.getLogger("RAM").info(gc.mem_free(), local_only=True)
            await config.getMQTT().publish(_mqtt.getDeviceTopic("ram_free"), gc.mem_free(),
                                           timeout=10)
            if s is not None:
                try:
                    await config.getMQTT().publish(_mqtt.getDeviceTopic("rssi"), s.status("rssi"),
                                                   timeout=10)
                except Exception as e:
                    await logging.getLogger("STATS").asyncLog("error",
                                                              "Error checking rssi: {!s}".format(
                                                                  e))
                    s = None
            await asyncio.sleep(self._interval)

    async def _discovery(self):
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("ram_free"), "ram_free",
                                     RAM_TYPE, "RAM free")
        await self._publishDiscovery("binary_sensor", _mqtt.getDeviceTopic("status"), "status",
                                     CONN_TYPE, "Status")
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("last_boot"), "last_boot",
                                     TIMELAPSE_TYPE,
                                     "Last Boot")
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("version"), "sw_version",
                                     VERSION_TYPE,
                                     "SW-Version")
        if platform != "linux":
            sens = DISCOVERY_SENSOR.format("signal_strength",  # device_class
                                           "dB",  # unit_of_measurement
                                           "{{value|int}}")  # value_template
            await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("rssi"), "rssi", sens,
                                         "Signal Strength")
