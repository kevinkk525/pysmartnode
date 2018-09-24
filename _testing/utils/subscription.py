'''
Created on 18.02.2018

@author: Kevin K�ck
'''

__version__ = "0.2"
__updated__ = "2018-03-09"

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
    from pysmartnode.utils.subscriptionHandlers.subscription import SubscriptionHandler
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
def getObjectDirectly():
    return handler.get("home/235j094s4eg/device2/htu9", 1)


@timeit
def addObjectsList():
    for j in range(0, 3):
        for i in range(0, 10):
            a.append(("home/235j094s4eg/device{!s}/htu{!s}".format(j, i), "func{!s}".format(i)))


@timeit
def getObjectList():
    for i in a:
        if i[0] == "home/235j094s4eg/device3/htu9":
            return i[1]


def speedtest():
    creating()
    gc.collect()
    printMemory("after creation with no Objects")
    addObjects()
    gc.collect()
    printMemory("30 Objects")
    print(getObject())
    gc.collect()
    print(getObjectDirectly())
    gc.collect()
    printMemory("Subscription test done")

    print("Comparison to list")
    global a
    a = []

    gc.collect()
    printMemory("List created")
    addObjectsList()
    gc.collect()
    printMemory("Added 30 objects to list")
    print(getObjectList())
    gc.collect()
    printMemory("List comparison done")


speedtest()
print("Functional test")


def test():
    from pysmartnode.utils.subscriptionHandlers.subscription import SubscriptionHandler
    handler = SubscriptionHandler()
    handler.addObject("home/test/htu", "func1")
    handler.addObject("home/test2/htu", "func2")
    handler.addObject("home/test3/htu2", "func3")
    print(handler.getFunctions("home/test/htu"))
    print(handler.getFunctions("home/test2/htu"))
    print(handler.getFunctions("home/test3/htu2"))
    handler.setFunctions("home/test3/htu2", "func_test")
    print(handler.getFunctions("home/test3/htu2"))
    try:
        print(handler.getFunctions("home/test5/htu2"))
    except Exception as e:
        print(e)
    handler.removeObject("home/test2/htu")
    try:
        print(handler.getFunctions("home/test2/htu"))
    except Exception as e:
        print(e)
    print(handler.getFunctions("home/test3/htu2"))
    handler.addObject("home/1325/ds18", "funcDS")
    print("Multiple subscriptions test")
    handler.addObject("home/1325/ds18", "funcDS2")
    print("ds18", handler.get("home/1325/ds18", 1))
    return handler


test()

print("Test finished")

"""
>>> from _testing.utils import subscription
[RAM] [Start] -336
[RAM] [After import] -992
[RAM] [After handler creation] -32
[RAM] [after creation with no Objects] 0
[Time] Function addObjects: 612.455ms
[RAM] [30 Objects] -3552
[Time] Function getObject:  5.920ms
func9
[Time] Function getObjectDirectly:  5.813ms
func9
[RAM] [Subscription test done] 0
Comparison to list
[RAM] [List created] -32
[Time] Function addObjectsList: 496.705ms
[RAM] [Added 30 objects to list] -2704
[Time] Function getObjectList:  2.223ms
None
[RAM] [List comparison done] 0
Functional test
func1
func2
func3
func_test
Object home/test5/htu2 does not exist
Object home/test2/htu does not exist
func_test
Multiple subscriptions test
ds18 ['funcDS', 'funcDS2']
Test finished
"""
