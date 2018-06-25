'''
Created on 21.02.2018

@author: Kevin K�ck
'''

__version__ = "0.3"
__updated__ = "2018-02-24"

import gc
gc.collect()
memory = gc.mem_free()


def printMemory(info=""):
    global memory
    memory_new = gc.mem_free()
    print("[RAM] [{!s}] {!s}".format(info, memory_new - memory))
    memory = memory_new


def functional_testing():
    print("Functioncal test")
    from pysmartnode.utils.subscriptionHandlers.tree import Tree
    tree = Tree("home", ["Functions"])
    tree.addObject("home/1325/htu21d/set", "func1")
    tree.addObject("home/1325/#", "funcWildcard")
    print("home:", tree.get("home", 0))
    print("1325:", tree.get("home/1325", 0))
    print("htu21d:", tree.get("home/1325/htu21d", 0))
    print("set:", tree.get("home/1325/htu21d/set", 0))

    try:
        tree.addObject("test/1325/htu21d/set", "func1")
    except Exception as e:
        print("Exception {!r} is expected".format(e))

    tree.addObject("home/1325/htu21d/test", "funcTest")
    print("home/1325/htu21d/test", tree.get("home/1325/htu21d/test", 0))
    tree.addObject("home/1325/htu21d", "func2")
    print("home/1325/htu21d", tree.get("home/1325/htu21d", 0))
    tree.setFunctions("home/1325/htu21d", "func_new")
    print("home/1325/htu21d", tree.getFunctions("home/1325/htu21d"))
    tree.addObject("home/1325/ds18/set", "funcDSSET")
    tree.addObject("home/1325/ds18", "funcDS")
    print("ds18/set:", tree.get("home/1325/ds18/set", 0))
    print("ds18", tree.get("home/1325/ds18", 0))
    print("\n")
    tree.print()
    print("\n")
    print("ds18", tree.get("home/1325/ds18", 0))
    print("ds19 (wildcard should trigger)", tree.get("home/1325/ds19", 0))
    print("ds18/bla (wildcard should trigger)", tree.get("home/1325/ds18/bla", 0))
    print("Multiple subscriptions test")
    tree.addObject("home/1325/ds18", "funcDS2")
    print("ds18", tree.get("home/1325/ds18", 0))
    print("Removing home/1325")
    tree.removeObject("home/1325")
    try:
        print("home/1325", tree.getFunctions("home/1325"))
    except Exception as e:
        print("Exception {!r} is expected".format(e))


import gc
from pysmartnode.utils.wrappers.timeit import timeit

memory = gc.mem_free()
gc.collect()


def creating():
    gc.collect()
    printMemory("Start")
    from pysmartnode.utils.subscriptionHandlers.tree import Tree
    gc.collect()
    printMemory("After import")
    global handler
    handler = Tree("home", ["Function"])
    gc.collect()
    printMemory("After handler creation")


@timeit
def addObjects():
    for j in range(0, 3):
        for i in range(0, 10):
            handler.addObject("home/235j094s4eg/device{!s}/htu{!s}".format(j, i), "func{!s}".format(i))


@timeit
def getObject():
    return handler.getFunction("home/235j094s4eg/device2/htu9")


@timeit
def getObjectDirectly():
    return handler.get("home/235j094s4eg/device2/htu9", 0)


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
a = []


@timeit
def addObjectsList():
    for j in range(0, 3):
        for i in range(0, 10):
            a.append(("home/235j094s4eg/device{!s}/htu{!s}".format(j, i), "func{!s}".format(i)))


@timeit
def getObjectList():
    for i in a:
        if i[0] == "home/235j094s4eg/device2/htu9":
            return i[1]


gc.collect()
printMemory("List created")
addObjectsList()
gc.collect()
printMemory("Added 30 objects to list")
print(getObjectList())
gc.collect()
printMemory("List comparison done")


functional_testing()

print("Test finished")


"""
>>> from _testing.utils import tree
[RAM] [Start] -192
[RAM] [After import] -720
[RAM] [After handler creation] -384
[RAM] [after creation with no Objects] -32
[Time][addObjects] 957941
[RAM] [30 Objects] -5088
[Time][getObject] 2375
func9
[Time][getObjectDirectly] 2265
func9
[RAM] [Subscription test done] -48
Comparison to list
[RAM] [List created] -128
[Time][addObjectsList] 890893
[RAM] [Added 30 objects to list] -2688
[Time][getObjectList] 1050
func9
[RAM] [List comparison done] 0
Functioncal test
home: None
1325: None
htu21d: None
set: func1
Exception ValueError('Requested object has different root: test',) is expected
home/1325/htu21d/test funcTest
home/1325/htu21d func2
home/1325/htu21d func_new
ds18/set: funcDSSET
ds18 funcDS


Printing Tree:
/home
/home/1325
/home/1325/htu21d
/home/1325/htu21d/set
/home/1325/htu21d/test
/home/1325/#
/home/1325/ds18
/home/1325/ds18/set


ds18 funcDS
ds19 (wildcard should trigger) funcWildcard
ds18/bla (wildcard should trigger) funcWildcard
Multiple subscriptions test
ds18 ['funcDS', 'funcDS2']
Removing home/1325
Exception ValueError('Object home/1325 does not exist',) is expected
Test finished
"""
