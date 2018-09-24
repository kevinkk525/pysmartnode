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

__updated__ = "2018-08-31"
__version__ = "0.4"

import gc

from pysmartnode import config
import uasyncio as asyncio

gc.collect()
from pysmartnode import logging


async def __gc(interval):
    while True:
        gc.collect()
        logging.getLogger("RAM").info(gc.mem_free(), local_only=True)
        await asyncio.sleep(interval)


async def __ram(topic, interval, interval_gc=10):
    asyncio.get_event_loop().create_task(__gc(interval_gc))
    await asyncio.sleep(12)
    while True:
        gc.collect()
        await config.getMQTT().publish(topic, gc.mem_free())
        await asyncio.sleep(interval)


def ram(mqtt_topic=None, interval=600):
    mqtt_topic = mqtt_topic or config.getMQTT().getDeviceTopic("ram_free")
    asyncio.get_event_loop().create_task(__ram(mqtt_topic, interval))
