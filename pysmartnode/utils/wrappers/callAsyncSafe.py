from pysmartnode.config import _log


async def callAsyncSafe(func, name, args, kwargs=None):
    kwargs = kwargs or {}
    try:
        await func(*args, **kwargs)
    except Exception as e:
        _log.error("Error calling async function {!r}, error: {!s}".format(name, e))
