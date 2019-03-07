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
    }
}
"""

__updated__ = "2019-02-22"
__version__ = "0.5"

import gc

from pysmartnode import config
import uasyncio as asyncio

gc.collect()
from pysmartnode import logging


async def __ram(topic, interval):
    await asyncio.sleep(12)
    while True:
        gc.collect()
        logging.getLogger("RAM").info(gc.mem_free(), local_only=True)
        await config.getMQTT().publish(topic, gc.mem_free())
        await asyncio.sleep(interval)


def ram(mqtt_topic=None, interval=600):
    mqtt_topic = mqtt_topic or config.getMQTT().getDeviceTopic("ram_free")
    asyncio.get_event_loop().create_task(__ram(mqtt_topic, interval))
