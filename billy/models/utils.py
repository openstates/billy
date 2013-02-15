import collections

from django.core import urlresolvers


def mongoid_2_url(abbr, _id):
    letter = _id[2]
    viewname = {
        'B': 'bill',
        'C': 'committee',
        'V': 'vote',
        'L': 'legislator_noslug',
    }[letter]
    return urlresolvers.reverse(viewname, args=[abbr, _id])


## {{{ http://code.activestate.com/recipes/276643/ (r1)
class CachedAttribute(object):
    '''Computes attribute value and caches it in instance.

    Example:
        class MyClass(object):
            def myMethod(self):
                # ...
            myMethod = CachedAttribute(myMethod)
    Use "del inst.myMethod" to clear cache.'''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result


class CachedClassAttribute(object):
    '''Computes attribute value and caches it in class.

    Example:
        class MyClass(object):
            def myMethod(cls):
                # ...
            myMethod = CachedClassAttribute(myMethod)
    Use "del MyClass.myMethod" to clear cache.'''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        result = self.method(cls)
        setattr(cls, self.name, result)
        return result


class ReadAliasAttribute(object):
    '''If not explcitly assigned this attribute is an alias for other.

    Example:
        class Document(object):
            title='?'
            shortTitle=ReadAliasAttribute('title')'''

    def __init__(self, name):
        self.name = name

    def __get__(self, inst, cls):
        if inst is None:
            return self
        return getattr(inst, self.name)


class AliasAttribute(ReadAliasAttribute):
    '''This attribute is an alias for other.

    Example:
        class Document(object):
            newAttrName=somevalue
            deprecatedAttrName=AliasAttribute('newAttrName')'''

    def __set__(self, inst, value):
        setattr(inst, self.name, value)

    def __delete__(self, inst):
        delattr(inst, self.name)
## end of http://code.activestate.com/recipes/276643/ }}}

## {{{ http://code.activestate.com/recipes/576694/ (r7)
KEY, PREV, NEXT = range(3)


class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[PREV]
            curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[NEXT] = next
            next[PREV] = prev

    def __iter__(self):
        end = self.end
        curr = end[NEXT]
        while curr is not end:
            yield curr[KEY]
            curr = curr[NEXT]

    def __reversed__(self):
        end = self.end
        curr = end[PREV]
        while curr is not end:
            yield curr[KEY]
            curr = curr[PREV]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = next(reversed(self)) if last else next(iter(self))
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __del__(self):
        self.clear()                    # remove circular references

if __name__ == '__main__':
    print(OrderedSet('abracadaba'))
    print(OrderedSet('simsalabim'))
## end of http://code.activestate.com/recipes/576694/ }}}
