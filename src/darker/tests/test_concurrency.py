"""Tests for `darker.concurrency`"""

# pylint: disable=use-dict-literal

from concurrent.futures import Future, ProcessPoolExecutor
from unittest.mock import Mock

import pytest

from darker import concurrency


def test_dummy_executor_submit_success():
    """Function is executed synchronously and future gives the return value"""
    executor = concurrency.DummyExecutor()
    func = Mock(return_value=42)

    future = executor.submit(func, "arg", kwarg="kwarg")

    assert isinstance(future, Future)
    assert future.result() == 42
    func.assert_called_once_with("arg", kwarg="kwarg")


def test_dummy_executor_submit_exception():
    """Future raises the exception from the function"""
    executor = concurrency.DummyExecutor()
    func = Mock(side_effect=ValueError("my-exception"))

    future = executor.submit(func, "arg", kwarg="kwarg")

    assert isinstance(future, Future)
    with pytest.raises(ValueError) as exc:
        assert future.result() == 42
        assert str(exc.value) == "my-exception"


@pytest.mark.kwparametrize(
    dict(max_workers=0, expect=ProcessPoolExecutor),
    dict(max_workers=1, expect=concurrency.DummyExecutor),
    dict(max_workers=2, expect=ProcessPoolExecutor),
    dict(max_workers=42, expect=ProcessPoolExecutor),
)
def test_get_executor(max_workers, expect):
    """A correct executor object is returned based on ``max_workers``"""
    result = concurrency.get_executor(max_workers)

    assert isinstance(result, expect)
