# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-28 

# This component will be started automatically to provide basic device statistics.
# You don't need to configure it to be active.

__updated__ = "2019-04-29"
__version__ = "0.2"

import gc

from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component import Component, TIMELAPSE_TYPE
import time

gc.collect()
from pysmartnode import logging

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "STATS"
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
        super().__init__()
        self._interval = config.INTERVAL_SEND_SENSOR

    async def _init(self):
        await super()._init()
        await self.on_reconnect()
        await _mqtt.publish(_mqtt.getDeviceTopic("version"), config.VERSION, 1, True)
        if config.RTC_SYNC_ACTIVE is True:
            for _ in range(5):
                if time.localtime()[0] == 2000:  # not synced
                    await asyncio.sleep(1)
            t = time.localtime()  # polling earlier might not have synced.
            await _mqtt.publish(_mqtt.getDeviceTopic("last_boot"),
                                "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3],
                                                                               t[4],
                                                                               t[5]), 1, True)
        await self._loop()

    async def _loop(self):
        await asyncio.sleep(12)
        while True:
            gc.collect()
            logging.getLogger("RAM").info(gc.mem_free(), local_only=True)
            await config.getMQTT().publish(_mqtt.getDeviceTopic("ram_free"), gc.mem_free())
            await asyncio.sleep(self._interval)

    async def _discovery(self):
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("ram_free"), "ram_free", RAM_TYPE, "RAM free")
        await self._publishDiscovery("binary_sensor", _mqtt.getDeviceTopic("status"), "status", CONN_TYPE, "Status")
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("last_boot"), "last_boot", TIMELAPSE_TYPE,
                                     "Last Boot")
        await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("version"), "sw_version", VERSION_TYPE,
                                     "SW-Version")

    async def on_reconnect(self):
        await _mqtt.publish(_mqtt.getDeviceTopic("status"), "online", 1, True)
