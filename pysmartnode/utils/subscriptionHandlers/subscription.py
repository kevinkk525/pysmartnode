# -*- coding: iso-8859-15 -*-
'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "1.3"
__updated__ = "2018-09-22"


# supports wildcards since 1.0

class _subscription:
    def __init__(self, values):
        self.values = values
        self.next = None


class SubscriptionHandler:
    def __init__(self, len_structure=1):
        """
        len_structure: number of attributes to be saved separately.
        identifier does not count to length of structure.
        """
        self.ifirst = None
        self.__values = len_structure + 1

    def get(self, identifier, index):
        if index > self.__values:
            raise IndexError("Index greater than object tuple length")
        if type(identifier) == _subscription:
            obj = identifier
        else:
            obj = self.__getObject(identifier)
        if obj is not None:
            return obj.values[index]
        raise IndexError("Object {!s} does not exist".format(identifier))

    def set(self, identifier, index, value, extend=False):
        if index > self.__values:
            raise IndexError("Index greater than object tuple length")
        if type(identifier) == _subscription:
            obj = identifier
        else:
            obj = self.__getObject(identifier)
        if obj is not None:
            if extend and type(obj.values[index] == list):
                obj.values[index].append(value)
            elif extend:
                raise ValueError("Can only extend a list")
            else:
                values = list(obj.values)
                values[index] = value
                obj.values = tuple(values)
        else:
            raise IndexError("Object {!s} does not exist".format(identifier))

    def getFunctions(self, identifier):
        return self.get(identifier, 1)

    def setFunctions(self, identifier, value):
        return self.set(identifier, 1, value)

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

    def __getObject(self, identifier, get=True):
        iObject = self.ifirst
        while iObject is not None:
            obj_val = iObject.values[0]
            if obj_val == identifier:
                return iObject
            elif get and obj_val.endswith("/#"):
                # check if identifier is found in subscription
                if identifier[:len(obj_val) - 2] == obj_val[:-2]:
                    if len(identifier) == len(obj_val) - 2 or \
                            identifier[len(obj_val) - 2] == "/":
                        # check if identifier matches subscription or has sublevel
                        # (home/test/# does not listen to home/testing)
                        return iObject
            iObject = iObject.next
        return None

    def addObject(self, identifier, *args):
        if len(args) + 1 > self.__values:
            raise IndexError("More arguements than structure allows")
        obj = self.__getObject(identifier, get=False)
        if obj is None:
            attribs = (identifier,) + args
            iObject = self.ifirst
            if iObject is None:
                self.ifirst = _subscription(attribs)
                return
            while iObject.next is not None:
                iObject = iObject.next
            iObject.next = _subscription(attribs)
        else:
            # raise IndexError("Object with identifier already exists")
            self._set(obj, (identifier,) + args)

    def _set(self, obj, values):
        values_obj = list(obj.values or [None] * self.__values)
        for i in range(1, len(values)):
            if values_obj[i] is None:
                values_obj[i] = values[i]
            elif type(values_obj[i]) != list:
                values_obj[i] = [values_obj[i]]
                values_obj[i].append(values[i])
            else:
                values_obj[i].append(values[i])
        obj.values = values_obj

    def removeObject(self, identifier):
        obj = self.__getObject(identifier, get=False)
        if obj == self.ifirst:
            self.ifirst = None
            del obj
            return
        if obj is not None:
            iObject = self.ifirst
            while iObject.next != obj:
                iObject = iObject.next
            iObject.next = obj.next
            del obj

    def print(self):
        for obj in self:
            print(obj)

    def __iter__(self, with_path=False):
        # with_path only for compatibility to tree
        obj = self.ifirst
        while obj is not None:
            if with_path:
                yield obj, obj.values[0]
            else:
                yield obj
            obj = obj.next
