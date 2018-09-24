'''
Created on 18.02.2018

@author: Kevin K�ck
'''

import time


def timeit(f):
    def new_func(*args, **kwargs):
        myname = str(f).split(' ')[1]
        t = time.ticks_us()
        result = f(*args, **kwargs)
        delta = time.ticks_diff(time.ticks_us(), t)
        print('[Time] Function {}: {:6.3f}ms'.format(myname, delta / 1000))
        return result

    return new_func


def timeitAsync(f):
    async def new_func(*args, **kwargs):
        gen = f(*args, **kwargs)
        myname = str(gen).split(' ')[2]
        t = time.ticks_us()
        result = await gen
        delta = time.ticks_diff(time.ticks_us(), t)
        print('[Time] Coroutine {}: {:6.3f}ms'.format(myname, delta / 1000))
        return result

    return new_func
