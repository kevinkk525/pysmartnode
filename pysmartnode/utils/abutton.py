# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Based on Peter Hinch's aswitch.py. Useable as a drop-in replacement.
# Queue overflow issue in Peter Hinch's aswitch fixed by now so this code
# only provides an alternative with less RAM usage.
# Created on 2019-10-19 

__updated__ = "2019-10-19"
__version__ = "0.1"

import uasyncio as asyncio
import time

type_gen = type((lambda: (yield))())  # Generator type


# If a callback is passed, run it and return.
# If a coro is passed initiate it and return.
# coros are passed by name i.e. not using function call syntax.
def launch(func, tup_args):
    res = func(*tup_args)
    if isinstance(res, type_gen):
        loop = asyncio.get_event_loop()
        loop.create_task(res)


class Pushbutton:
    debounce_ms = 50
    long_press_ms = 1000
    double_click_ms = 400

    def __init__(self, pin, suppress=False):
        self.pin = pin
        self._supp = suppress  # don't call release func after long press
        self._tf = None  # pressed function
        self._ff = None  # released function
        self._df = None  # double pressed function
        self._lf = None  # long pressed function
        self.sense = pin.value()  # Convert from electrical to logical value
        self.state = self.rawstate()  # Initial state
        loop = asyncio.get_event_loop()
        loop.create_task(self.buttoncheck())  # Thread runs forever

    def press_func(self, func, args=()):
        self._tf = func
        self._ta = args

    def release_func(self, func, args=()):
        self._ff = func
        self._fa = args

    def double_func(self, func, args=()):
        self._df = func
        self._da = args

    def long_func(self, func, args=()):
        self._lf = func
        self._la = args

    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self.pin.value() ^ self.sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self.state

    async def buttoncheck(self):
        t_change = None
        supp = False
        clicks = 0
        lpr = False  # long press ran
        ####
        # local functions for performance improvements
        deb = self.debounce_ms
        dcms = self.double_click_ms
        lpms = self.long_press_ms
        raw = self.rawstate
        ticks_diff = time.ticks_diff
        ticks_ms = time.ticks_ms
        #
        while True:
            state = raw()
            if state is False and self.state is False and self._supp and \
                    ticks_diff(ticks_ms(), t_change) > dcms and clicks > 0 and self._ff:
                clicks = 0
                launch(self._ff, self._fa)
            elif state is True and self.state is True:
                if clicks > 0 and ticks_diff(ticks_ms(), t_change) > dcms:
                    # double click timeout
                    clicks = 0
                if self._lf and lpr is False:  # check long press
                    if ticks_diff(ticks_ms(), t_change) >= lpms:
                        lpr = True
                        clicks = 0
                        if self._supp is True:
                            supp = True
                        launch(self._lf, self._la)
            elif state != self.state:  # state changed
                lpr = False
                self.state = state
                if state is True:  # Button pressed: launch pressed func
                    if ticks_diff(ticks_ms(), t_change) > dcms:
                        clicks = 0
                    if self._df:
                        clicks += 1
                    if clicks == 2:  # double click
                        clicks = 0
                        if self._supp is True:
                            supp = True
                        launch(self._df, self._da)
                    elif self._tf:
                        launch(self._tf, self._ta)
                else:  # Button released. launch release func
                    if supp is True:
                        supp = False
                    elif clicks and self._supp > 0:
                        pass
                    elif self._ff:  # not after a long press with suppress
                        launch(self._ff, self._fa)
                t_change = ticks_ms()
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(deb)
