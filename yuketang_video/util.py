from collections.abc import Awaitable, Coroutine
from contextlib import AbstractAsyncContextManager
from typing import Callable


def wrap_with_async_ctx[**P, R](
    ctx: AbstractAsyncContextManager,
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Coroutine[None, None, R]]:
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        async with ctx:
            return await func(*args, **kwargs)

    return wrapped
