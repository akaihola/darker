"""Concurrency helpers for enhancing the performance of Darker"""

from concurrent.futures import Executor, Future, ProcessPoolExecutor
from typing import Any, Callable, TypeVar

T = TypeVar("T")  # pylint: disable=invalid-name


class DummyExecutor(Executor):
    """Dummy synchronous executor to use with ``--workers=1``

    This makes it easier to write test cases for `darker.__main__.main`.

    """

    # pylint: disable=arguments-differ,unsubscriptable-object,broad-except
    def submit(  # type: ignore[override]
        self, fn: Callable[..., T], *args: Any, **kwargs: Any
    ) -> Future[T]:
        """Submits "a callable to be executed with the given arguments.

        Executes the callable immediately as ``fn(*args, **kwargs)`` and returns a
        `Future` instance representing the execution of the callable.

        :param fn: The callable to call
        :param args: Positional arguments for the callable
        :param kwargs: Keyword arguments for the callable
        :return: A `Future` representing the given call

        """
        future: Future[T] = Future()
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc_info:  # noqa: B036
            future.set_exception(exc_info)
        else:
            future.set_result(result)
        return future


def get_executor(max_workers: int) -> Executor:
    """Return either a dummy executor (if ``max_workers===1`) or a process pool executor

    :param max_workers: The maximum number of processes that can be used to execute the
                        given calls. If ``0`` then as many worker processes will be
                        created as the machine has processors. If ``1``, the dummy
                        executor will be used so calls are executed synchronously.
    :return: A dummy executor or a process pool executor

    """
    return (
        DummyExecutor()
        if max_workers == 1
        else ProcessPoolExecutor(max_workers or None)
    )
