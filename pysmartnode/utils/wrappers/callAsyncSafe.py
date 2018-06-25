from pysmartnode.config import log


async def callAsyncSafe(func, name, args, kwargs=None):
    kwargs = kwargs or {}
    try:
        await func(*args, **kwargs)
    except Exception as e:
        log.error("Error calling async init function {!r}, error: {!s}".format(name, e))
