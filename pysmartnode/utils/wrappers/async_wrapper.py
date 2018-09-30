def async_wrapper(f):
    """ property not supported, only function and coroutine """

    async def wrap(*args, **kwargs):
        res = f(*args, **kwargs)
        if str(type(res)) == "<class 'generator'>":
            res = await res
        return res

    return wrap
