import uasyncio as asyncio
from pysmartnode import config
from pysmartnode.utils.wrappers.callAsyncSafe import callAsyncSafe as _callAsyncSafe


async def callRegular(func, interval=None):
    interval = interval or config.INTERVAL_SEND_SENSOR
    while True:
        if type(func) == type(_callAsyncSafe):
            await func()
        else:
            func()
        await asyncio.sleep(interval)


async def callRegularPublish(func, topic, interval=None, retain=None, qos=None):
    interval = interval or config.INTERVAL_SEND_SENSOR
    mqtt = config.getMQTT()
    while True:
        if type(func) == type(_callAsyncSafe):
            res = await func()
        else:
            res = func()
        await mqtt.publish(topic, res, retain, qos)
        await asyncio.sleep(interval)
