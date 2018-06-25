'''
Created on 18.02.2018

@author: Kevin K�ck
'''

import time


def timeit(f):
    def wrap(*args, **kwargs):
        st = time.ticks_us()
        res = f(*args, **kwargs)
        et = time.ticks_us()
        print("[Time][{!s}] {!s}us".format(f.__name__ if hasattr(f, "__name__") else "function", et - st))
        return res

    return wrap


def timeitAsync(f):
    async def wrap(*args, **kwargs):
        st = time.ticks_us()
        res = await f(*args, **kwargs)
        et = time.ticks_us()
        print("[Time][{!s}] {!s}us".format(f.__name__ if hasattr(f, "__name__") else "function", et - st))
        return res

    return wrap
