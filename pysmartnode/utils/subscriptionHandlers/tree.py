# -*- coding: iso-8859-15 -*-
'''
Created on 20.02.2018

@author: Kevin Köck
'''

__version__ = "0.4"
__updated__ = "2018-04-13"
DEBUG = False


class _Branch:
    def __init__(self, identifier, values=None):
        if DEBUG:
            print("_Branch: ident {!s}, values {!s}".format(identifier, values))
        self.values = values
        self.identifier = identifier
        self.branches = []

    def __str__(self):
        return self.identifier


class Tree:
    def __init__(self, root, structure=None, delimiter=None, wildcard_char=None):
        """
        structure: [] list of names of all attributes to be saved
        identifier not in structure
        """
        self.tree = _Branch(root)
        self.__values = 1
        self._delimiter = delimiter or "/"
        self._wildcard_char = wildcard_char or "#"
        if type(structure) == list:
            self.__values = len(structure)
            for i in range(0, len(structure)):
                setattr(self, "get{!s}".format(structure[i]), self.__wrapper_get(i))
                setattr(self, "set{!s}".format(structure[i]), self.__wrapper_set(i))
        if DEBUG:
            print("Tree, root {!s}, #values {!s}, structure: {!s}".format(
                root, self.__values, structure))

    def get(self, identifier, index):
        if index > self.__values:
            raise IndexError("Index greater than object tuple length")
        if type(identifier) == _Branch:
            obj = identifier
        else:
            obj = self.__getaddObject(identifier)
        if obj is not None:
            if obj.values is None:
                return None
            return obj.values[index]
        raise IndexError("Object {!s} does not exist".format(identifier))

    def set(self, identifier, index, value, extend=False):
        if index > self.__values:
            raise IndexError("Index greater than object tuple length")
        if type(identifier) == _Branch:
            obj = identifier
        else:
            obj = self.__getaddObject(identifier)
        if obj is not None:
            if obj.values is None:
                obj.values = (None,) * self.__values
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

    def __getaddObject(self, identifier, return_last_available=False, add=False, values=None,
                       return_parent=False):
        iObject = self.tree
        parent = None
        branches = identifier.split(self._delimiter)
        wildcard = None
        if iObject.identifier != branches[0]:
            raise ValueError("Requested object has different root: {!s}".format(branches[0]))
        elif len(branches) == 1:
            if return_parent:
                return iObject, None
            return iObject
        for iBranch in range(1, len(branches)):
            found = False
            for br in iObject.branches:
                if br.identifier == branches[iBranch]:
                    parent = iObject
                    iObject = br
                    if iBranch == len(branches) - 1 and iObject.values is None and add == False:
                        # if object has no values, check for wildcard subscription
                        try:
                            iObject, parent = self.__getaddObject(
                                identifier + "/" + self._wildcard_char, return_last_available,
                                add=False, return_parent=True)
                        except IndexError:
                            pass
                    found = True
                    # break
                elif br.identifier == self._wildcard_char:
                    wildcard = br
            if found:
                if iBranch == len(branches) - 1:
                    if add:
                        # if object exists, values are appended
                        self._set(iObject, values)
                    if return_parent:
                        return iObject, parent
                    return iObject
            elif return_last_available:
                return iObject
            else:
                if add:
                    if iBranch == len(branches) - 1:
                        parent = iObject
                        iObject = self._addObject(branches[iBranch], values, iObject)
                        if return_parent:
                            return iObject, parent
                        return iObject
                    else:
                        parent = iObject
                        iObject = self._addObject(branches[iBranch], None, iObject)
                    if iBranch == len(branches):
                        if return_parent:
                            return iObject, parent
                        return True
                else:
                    if wildcard is not None:
                        if return_parent:
                            return wildcard, parent
                        return wildcard
                    if return_parent:
                        return None, parent
                    return None

    def _addObject(self, branch, values, parent):
        nbranch = _Branch(branch, values)
        parent.branches.append(nbranch)
        return nbranch

    def _set(self, obj, values):
        values_obj = list(obj.values or [None] * self.__values)
        for i in range(0, len(values)):
            if values_obj[i] is None:
                values_obj[i] = values[i]
            elif type(values_obj[i]) != list:
                values_obj[i] = [values_obj[i]]
                values_obj[i].append(values[i])
            else:
                values_obj[i].append(values[i])
        obj.values = values_obj

    def addObject(self, identifier, *args):
        res = self.__getaddObject(identifier, add=True, values=args)
        if res is None:
            raise IndexError("Object already exists")

    def removeObject(self, identifier):
        if type(identifier) == _Branch:
            iObject = identifier
            parent = None
        else:
            iObject, parent = self.__getaddObject(identifier, return_parent=True)
            if iObject is None:
                raise IndexError("Object {!s} does not exist".format(identifier))
        for branch in iObject.branches:
            self.removeObject(branch)
        if parent:
            del parent.branches[parent.branches.index(iObject)]
        if DEBUG:
            print("Tree, removing {!s}".format(iObject))
        del iObject

    def print(self):
        for obj in self:
            print(obj)

    def __iter__(self, obj=None, path="", with_path=False):
        iObject = obj or self.tree
        path += "/{!s}".format(iObject)
        if with_path:
            yield iObject, path
        else:
            yield iObject
        for br in iObject.branches:
            yield from self.__iter__(br, path, with_path)
