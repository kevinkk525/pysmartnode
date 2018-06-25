'''
Created on 30.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.ram
    component: ram
    constructor_args: {
        mqtt_topic: sometopic    #optional, defaults to home/<controller id>/ram_free
        interval: 600              #optional, defaults to 600s
        interval_gc: 10            #optional, defaults to 10s
    }
}
"""

__updated__ = "2018-04-21"
__version__ = "0.3"

import gc

from pysmartnode import config

mqtt = config.getMQTT()
import uasyncio as asyncio

gc.collect()
from pysmartnode import logging

log = logging.getLogger("RAM")


async def __gc(interval):
    while True:
        gc.collect()
        log.info(gc.mem_free(), local_only=True)
        await asyncio.sleep(interval)


async def __ram(topic, interval, interval_gc=10):
    asyncio.get_event_loop().create_task(__gc(interval_gc))
    await asyncio.sleep(12)
    while True:
        gc.collect()
        await mqtt.publish(topic, gc.mem_free())
        await asyncio.sleep(interval)


def ram(mqtt_topic=None, interval=600):
    mqtt_topic = mqtt_topic or mqtt.getDeviceTopic("ram_free")
    asyncio.get_event_loop().create_task(__ram(mqtt_topic, interval))
