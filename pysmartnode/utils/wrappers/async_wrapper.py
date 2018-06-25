def async_wrapper(f):
    """ property not supported, only function and coroutine """

    async def wrap():
        res = f()
        if str(type(res)) == "<class 'generator'>":
            res = await res
        return res

    return wrap
