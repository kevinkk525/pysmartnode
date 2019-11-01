# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-28 

# This component will be started automatically to provide basic device statistics.
# You don't need to configure it to be active.

__updated__ = "2019-11-01"
__version__ = "1.3"

import gc

from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component import Component
import time
from sys import platform
from pysmartnode import logging
from pysmartnode.utils import sys_vars

try:
    import os
except:
    import uos as os  # unix port compatibility because of missing weaklinks

if platform != "linux":
    import network

gc.collect()

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "STATS"
####################

_mqtt = config.getMQTT()

STATE_TYPE = '"json_attributes_topic":"~",' \
             '"unit_of_meas":"dBm",' \
             '"val_tpl":"{{value_json.RSSI|int}}",' \
             '"ic":"mdi:information-outline",'


class STATS(Component):
    def __init__(self):
        super().__init__(COMPONENT_NAME, __version__)
        self._interval = config.INTERVAL_SENSOR_PUBLISH
        self._last_boot = None

    async def _init_network(self):
        await super()._init_network()
        await self._publish()
        asyncio.get_event_loop().create_task(self._loop())
        # start loop once network is completely set up because it doesn't have
        # any use otherwise because component only publishes stats.

    async def _publish(self):
        val = {}
        if platform != "linux":
            sta = network.WLAN(network.STA_IF)
        else:
            sta = None
        val["Pysmartnode version"] = config.VERSION
        if config.RTC_SYNC_ACTIVE is True:
            if self._last_boot is None:
                for _ in range(5):
                    if time.localtime()[0] == 2000:  # not synced
                        await asyncio.sleep(1)
                t = time.time()  # polling earlier might not have synced.
                s = round(time.ticks_ms() / 1000)
                self._last_boot = time.localtime(t - s)  # last real boot/reset, not soft reset
            t = self._last_boot
            val["Last boot"] = "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2],
                                                                              t[3], t[4], t[5])
            s = int(time.time() - time.mktime(t))
        else:
            s = time.ticks_ms() / 1000  # approximate uptime depending on accuracy of ticks_ms()
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        val["Uptime"] = '{:d}T{:02d}:{:02d}:{:02d}'.format(d, h, m, s)
        logging.getLogger("RAM").info(gc.mem_free(), local_only=True)
        val["RAM free (bytes)"] = gc.mem_free()
        if sta is not None:
            try:
                val["RSSI"] = sta.status("rssi")
            except Exception as e:
                val["RSSI"] = 0  # platform doesn't support reading rssi
                print(e)
            try:
                val["IPAddress"] = sta.ifconfig()[0]
            except Exception as e:
                print(e)
                pass
        else:
            val["RSSI"] = 0  # can't read rssi on unix port, might not even be connected by WLAN
        try:
            val["Micropython version"] = os.uname().version
        except:
            pass
        s = int(_mqtt.getDowntime())
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        val["MQTT Downtime"] = '{:d}T{:02d}:{:02d}:{:02d}'.format(d, h, m, s)
        val["MQTT Reconnects"] = _mqtt.getReconnects()
        val["MQTT Dropped messages"] = _mqtt.getDroppedMessages()
        val["MQTT Subscriptions"] = _mqtt.getLenSubscribtions()
        if config.DEBUG:
            # only needed for debugging and could be understood wrongly otherwise
            val["MQTT TimedOutOps"] = _mqtt.getTimedOutOperations()
        val["Asyncio waitq"] = "{!s}/{!s}".format(len(asyncio.get_event_loop().waitq),
                                                  config.LEN_ASYNC_QUEUE)
        await _mqtt.publish(_mqtt.getDeviceTopic("status"), val, qos=1, retain=False, timeout=5)
        del val
        gc.collect()
        if config.DEBUG:
            # DEBUG to check RAM/Heap fragmentation
            import micropython
            micropython.mem_info(1)

    async def _loop(self):
        await asyncio.sleep(20)
        while True:
            gc.collect()
            await self._publish()
            await asyncio.sleep(self._interval)

    async def _discovery(self, register=True):
        topic = _mqtt.getRealTopic(_mqtt.getDeviceTopic("status"))
        if register:
            await self._publishDiscovery("sensor", topic, "status", STATE_TYPE,
                                         "Status {!s}".format(
                                             config.DEVICE_NAME or sys_vars.getDeviceID()))
        else:
            await self._deleteDiscovery("sensor", "status")
        gc.collect()
