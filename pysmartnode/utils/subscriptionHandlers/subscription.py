# -*- coding: iso-8859-15 -*-
'''
Created on 17.02.2018

@author: Kevin Köck
'''

__version__ = "0.2"
__updated__ = "2018-04-11"


class _subscription:
    def __init__(self, values):
        self.values = values
        self.next = None


class SubscriptionHandler:
    def __init__(self, structure=None):
        """
        structure: [] list of names of all attributes to be saved
        identifier not in structure
        """
        self.ifirst = None
        self.__values = 1
        if type(structure) == list:
            self.__values = len(structure) + 1
            for i in range(0, len(structure)):
                setattr(self, "get{!s}".format(structure[i]), self.__wrapper_get(i + 1))
                setattr(self, "set{!s}".format(structure[i]), self.__wrapper_set(i + 1))

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

    def __wrapper_get(self, index):
        def get(identifier):
            return self.get(identifier, index)
        return get

    def __wrapper_set(self, index):
        def set(identifier, value):
            return self.set(identifier, index, value)
        return set

    def __getObject(self, identifier):
        iObject = self.ifirst
        while iObject is not None:
            if iObject.values[0] == identifier:
                return iObject
            iObject = iObject.next
        return None

    def addObject(self, identifier, *args):
        if len(args) + 1 > self.__values:
            raise IndexError("More arguements than structure allows")
        obj = self.__getObject(identifier)
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
            #raise IndexError("Object with identifier already exists")
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
        obj = self.__getObject(identifier)
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
