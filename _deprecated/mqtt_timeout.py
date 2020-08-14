# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-03-31 

__updated__ = "2020-04-01"
__version__ = "0.2"

from micropython_mqtt_as.mqtt_as import MQTTClient as _MQTTClient
import uasyncio as asyncio
import time


# doesn't work with new version of uasyncio

class MQTTClient(_MQTTClient):
    _ops_tasks = [None, None]  # publish and (un)sub operations, can be concurrent

    async def _operationTimeout(self, coro, *args, i):
        try:
            await coro(*args)
        except asyncio.CancelledError:
            raise  # in case the calling function need to handle Cancellation too
        finally:
            self._ops_tasks[i] = None

    async def _preprocessor(self, coroutine, *args, timeout=None, await_connection=True):
        task = None
        start = time.ticks_ms()
        i = 0 if len(args) == 4 else 1  # 0: publish, 1:(un)sub
        try:
            while timeout is None or time.ticks_diff(time.ticks_ms(), start) < timeout * 1000:
                if not await_connection and not self._isconnected:
                    return False
                if self._ops_tasks[i] is task is None:
                    task = asyncio.create_task(self._operationTimeout(coroutine, *args, i=i))
                    self._ops_tasks[i] = task
                elif task:
                    if self._ops_tasks[i] is not task:
                        return True  # published
                await asyncio.sleep_ms(20)
            self.dprint("timeout on", "(un)sub" if i else "publish", args)
            raise asyncio.TimeoutError
        except asyncio.CancelledError:
            raise  # the caller should be cancelled too
        finally:
            if task and self._ops_tasks[i] is task:
                async with self.lock:
                    task.cancel()

    async def publish(self, topic, msg, retain=False, qos=0, timeout=None, await_connection=True):
        if not await_connection and not self._isconnected:
            return False
        return await self._preprocessor(super().publish, topic, msg, retain, qos,
                                        timeout=timeout, await_connection=await_connection)

    async def subscribe(self, topic, qos=0, timeout=None, await_connection=True):
        if not await_connection and not self._isconnected:
            return False
        return await self._preprocessor(super().unsubscribe, topic, timeout=timeout,
                                        await_connection=False)

    async def unsubscribe(self, topic, timeout=None, await_connection=True):
        if not await_connection and not self._isconnected:
            return False
        return await self._preprocessor(super().unsubscribe, topic, timeout=timeout,
                                        await_connection=await_connection)
