'''
Created on 11.04.2018

@author: Kevin
'''


def wrapResult(handler, expected, result):
    equals = str(expected) == str(result)
    print(handler, "Success:", equals, "Expected result:", expected, "Result:", result)


from pysmartnode.utils.subscriptionHandlers.tree import Tree
from pysmartnode.utils.subscriptionHandlers.subscribe_file import SubscriptionHandler as SubscriptionHandler_File
from pysmartnode.utils.subscriptionHandlers.subscription import SubscriptionHandler

for handler in [Tree, SubscriptionHandler, SubscriptionHandler_File]:
    print(handler)
    if handler == Tree:
        t = Tree("home", ["Functions"])
    elif handler == SubscriptionHandler:
        t = SubscriptionHandler()
    else:
        t = SubscriptionHandler_File()

    topic = "home/login/#"
    t.addObject(topic, "sendConfig")
    wrapResult(handler, "sendConfig", t.getFunctions("home/login/test"))
    wrapResult(handler, "sendConfig", t.getFunctions("home/login"))

    topic = "home/login"
    t.addObject(topic, "nothing")
    wrapResult(handler, "sendConfig", t.getFunctions("home/login/test"))
    wrapResult(handler, "nothing", t.getFunctions("home/login"))
    if handler == SubscriptionHandler:
        print("This test fails because the wildcard was subscribed first and will be found first")

print("\nTests done\n")
