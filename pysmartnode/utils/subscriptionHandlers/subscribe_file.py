# -*- coding: iso-8859-15 -*-
'''
Created on 11.03.2018

@author: Kevin Köck
'''

__version__ = "0.4"
__updated__ = "2018-09-22"

import os
import gc


class SubscriptionHandler:
    def __init__(self):
        # not using structure
        self._subscription_file = "_subscriptions.txt"
        f = open(self._subscription_file, "w")
        f.close()
        self._functions = []  # [(cb1,cb2),(cb1),...]

    def getFunctions(self, identifier, index=False, ignore_error=False, ignore_wildcard=False):
        cbs = None
        i = 0
        with open(self._subscription_file, "r") as f:
            for line in f:
                line = line[:-1]
                gc.collect()
                if identifier == line:
                    cbs = (self._functions[i], i)
                    break
                elif ignore_wildcard is False and self.matchesSubscription(identifier, line):
                    if cbs is None:
                        cbs = (self._functions[i], i)
                i += 1
        if cbs is None:
            if ignore_error is False:
                raise IndexError("Object {!s} does not exist".format(identifier))
            i = None
        if index:
            if cbs is None:
                return None, i
            return cbs
        return cbs[0]

    @staticmethod
    def matchesSubscription(topic, subscription):
        if topic == subscription:
            return True
        if subscription.endswith("/#"):
            lens = len(subscription)
            if topic[:lens - 2] == subscription[:-2]:
                if len(topic) == lens - 2 or topic[lens - 2] == "/":
                    # check if identifier matches subscription or has sublevel
                    # (home/test/# does not listen to home/testing)
                    return True
        return False

    def setFunctions(self, identifier, cbs):
        _, i = self.getFunctions(identifier, index=True)
        if type(cbs) == list:
            self._functions[i] = tuple(cbs)
        else:
            self._functions[i] = cbs

    def addObject(self, identifier, cb):
        _, i = self.getFunctions(identifier, index=True, ignore_error=True, ignore_wildcard=True)
        if i is None:
            if type(cb) == list:
                self._functions.append(tuple(cb))
            else:
                self._functions.append(cb)
            with open(self._subscription_file, "a") as f:
                f.write(identifier)
                f.write("\n")
        else:
            if type(cb) == list or type(cb) == tuple:
                if type(self._functions[i]) == tuple:
                    self._functions[i] = tuple(list(self._functions[i]) +
                                               cb if type(cb) == list else list(cb))
                else:
                    self._functions[i] = tuple([self._functions[i]] +
                                               cb if type(cb) == list else list(cb))
            else:
                if type(self._functions[i]) == tuple:
                    l = list(self._functions[i])
                else:
                    l = [self._functions[i]]
                l.append(cb)
                self._functions[i] = tuple(l)

    def removeObject(self, identifier):
        i = 0
        foundi = None
        with open("_subs_temp.txt", "w") as tmp:
            with open(self._subscription_file, "r") as f:
                for line in f:
                    gc.collect()
                    if line[:-1] == identifier:
                        foundi = i
                    else:
                        tmp.write(line)
                    i += 1
        if foundi is not None:
            self._functions.pop(foundi)
        os.remove(self._subscription_file)
        os.rename("_subs_temp.txt", self._subscription_file)
        gc.collect()

    def __iter__(self, with_path=False):
        # with_path only for compatibility to tree
        with open(self._subscription_file, "r") as f:
            for line in f:
                line = line[:-1]
                gc.collect()
                if with_path:
                    yield None, line
                else:
                    yield line
