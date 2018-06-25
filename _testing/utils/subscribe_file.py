'''
Created on 11.03.2018

@author: Kevin K�ck
'''

__version__ = "0.2"
__updated__ = "2018-03-11"

import gc
from pysmartnode.utils.wrappers.timeit import timeit

memory = gc.mem_free()
gc.collect()


def printMemory(info=""):
    global memory
    memory_new = gc.mem_free()
    print("[RAM] [{!s}] {!s}".format(info, memory_new - memory))
    memory = memory_new


def creating():
    gc.collect()
    printMemory("Start")
    from pysmartnode.utils.subscriptionHandlers.subscribe_file import SubscriptionHandler
    gc.collect()
    printMemory("After import")
    global handler
    handler = SubscriptionHandler()
    gc.collect()
    printMemory("After handler creation")


@timeit
def addObjects():
    for j in range(0, 3):
        for i in range(0, 10):
            handler.addObject("home/235j094s4eg/device{!s}/htu{!s}".format(j, i), "func{!s}".format(i))


@timeit
def getObject():
    return handler.getFunctions("home/235j094s4eg/device2/htu9")


@timeit
def removeObject(handler):
    handler.removeObject("home/test2/htu")


def speedtest():
    creating()
    gc.collect()
    printMemory("after creation with no Objects")
    addObjects()
    gc.collect()
    printMemory("30 Objects")
    print(getObject())
    gc.collect()
    printMemory("Subscription test done")


speedtest()
print("Functional test")


def test():
    from pysmartnode.utils.subscriptionHandlers.subscribe_file import SubscriptionHandler
    handler = SubscriptionHandler()

    @timeit
    def create():
        handler.addObject("home/test/htu", "func1")
        handler.addObject("home/test2/htu", "func2")
        handler.addObject("home/test3/htu2", "func3")
    create()

    @timeit
    def get():
        print(handler.getFunctions("home/test/htu"))
        print(handler.getFunctions("home/test2/htu"))
        print(handler.getFunctions("home/test3/htu2"))
    get()
    handler.setFunctions("home/test3/htu2", "func_test")
    print(handler.getFunctions("home/test3/htu2"))
    try:
        print(handler.getFunctions("home/test5/htu2"))
    except Exception as e:
        print(e)
    removeObject(handler)
    try:
        print(handler.getFunctions("home/test2/htu"))
    except Exception as e:
        print(e)
    print(handler.getFunctions("home/test3/htu2"))
    handler.addObject("home/1325/ds18", "funcDS")
    handler.addObject("home/1325/#", "funcWildcard")
    print("ds19 (wildcard should trigger)", handler.getFunctions("home/1325/ds19"))
    print("ds19 (wildcard should trigger)", handler.getFunctions("home/1325/ds19/what"))
    print("Multiple subscriptions test")
    handler.addObject("home/1325/ds18", "funcDS2")
    print("ds18", handler.getFunctions("home/1325/ds18"))
    return handler


test()

print("Test finished")


"""
>>> from _testing.utils import subscribe_file
[RAM] [Start] -224
[RAM] [After import] -368
[RAM] [After handler creation] -112
[RAM] [after creation with no Objects] 0
[Time][function] 9279007
[RAM] [30 Objects] -784
[Time][function] 392449
func9
[RAM] [Subscription test done] 0
Functional test
[Time][function] 386079
func1
func2
func3
[Time][function] 84170
func_test
Object home/test5/htu2 does not exist
[Time][function] 417159
Object home/test2/htu does not exist
func_test
ds19 (wildcard should trigger) funcWildcard
ds19 (wildcard should trigger) funcWildcard
Multiple subscriptions test
ds18 ('funcDS', 'funcDS2')
Test finished
"""
