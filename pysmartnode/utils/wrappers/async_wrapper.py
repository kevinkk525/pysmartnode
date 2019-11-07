type_gen = type((lambda: (yield))())  # Generator type


def async_wrapper(f):
    """ property not supported, only function and coroutine """

    async def wrap(*args, **kwargs):
        res = f(*args, **kwargs)
        if type(res) == type_gen:
            res = await res
        return res

    return wrap
