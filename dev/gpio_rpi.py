# -*- coding: utf-8 -*-
__version__ = '0.1.0'

import os


class PinState(object):
    """An ultra simple pin-state object.
    Keeps track data related to each pin.
    Args:
        value: the file pointer to set/read value of pin.
        direction: the file pointer to set/read direction of the pin.
    """

    def __init__(self, value, direction):
        self.value = value
        self.direction = direction


path = os.path
pjoin = os.path.join

gpio_root = '/sys/class/gpio'
gpiopath = lambda pin: os.path.join(gpio_root, 'gpio{0}'.format(pin))

_open = dict()
FMODE = 'w+'

IN, OUT = "in", "out"
LOW, HIGH = 0, 1


def _write(f, v):
    print("writing: {}: {}".format(f, v))
    f.write(str(v))
    f.flush()


def _read(f):
    print("Reading: {}".format(f))
    f.seek(0)
    return f.read().strip()


def _verify(function):
    """decorator to ensure pin is properly set up"""

    def wrapped(pin, *args, **kwargs):
        pin = int(pin)
        if pin not in _open:
            ppath = gpiopath(pin)
            if not os.path.exists(ppath):
                print("Creating Pin {0}".format(pin))
                with open(pjoin(gpio_root, 'export'), 'w') as f:
                    _write(f, pin)
            value = open(pjoin(ppath, 'value'), FMODE)
            direction = open(pjoin(ppath, 'direction'), FMODE)
            _open[pin] = PinState(value=value, direction=direction)
        return function(pin, *args, **kwargs)

    return wrapped


def cleanup(pin=None, assert_exists=False):
    """Cleanup the pin by closing and unexporting it.
    Args:
        pin (int, optional): either the pin to clean up or None (default).
            If None, clean up all pins.
        assert_exists: if True, raise a ValueError if the pin was not
            setup. Otherwise, this function is a NOOP.
    """
    if pin is None:
        # Take a list of keys because we will be deleting from _open
        for pin in list(_open):
            cleanup(pin)
        return
    if not isinstance(pin, int):
        raise TypeError("pin must be an int, got: {}".format(pin))

    state = _open.get(pin)
    if state is None:
        if assert_exists:
            raise ValueError("pin {} was not setup".format(pin))
        return
    state.value.close()
    state.direction.close()
    if os.path.exists(gpiopath(pin)):
        print("Unexporting pin {0}".format(pin))
        with open(pjoin(gpio_root, 'unexport'), 'w') as f:
            _write(f, pin)

    del _open[pin]


@_verify
def setup(pin, mode, pullup=None, initial=False):
    '''Setup pin with mode IN or OUT.
    Args:
        pin (int):
        mode (str): use either gpio.OUT or gpio.IN
        pullup (None): rpio compatibility. If anything but None, raises
            value Error
        pullup (bool, optional): Initial pin value. Default is False
    '''
    if pullup is not None:
        raise ValueError("sysfs does not support pullups")

    if mode not in (IN, OUT):
        raise ValueError(mode)

    print("Setup {}: {}".format(pin, mode))
    f = _open[pin].direction
    _write(f, mode)
    if mode == OUT:
        if initial:
            set(pin, 1)
        else:
            set(pin, 0)


# @_verify
def mode(pin):
    '''get the pin mode
    Returns:
        str: "in" or "out"
    '''
    f = _open[pin].direction
    return _read(f)


# @_verify
def read(pin):
    '''read the pin value
    Returns:
        bool: 0 or 1
    '''
    f = _open[pin].value
    out = int(_read(f))
    print("Read {}: {}".format(pin, out))
    return out


# @_verify
def set(pin, value):
    '''set the pin value to 0 or 1'''
    print("Write {}: {}".format(pin, value))
    f = _open[pin].value
    _write(f, value)


input = read
output = set


def setwarnings(value):
    '''exists for rpio compatibility'''
    pass


def setmode(value):
    '''exists for rpio compatibility'''
    pass


BCM = None  # rpio compatibility
