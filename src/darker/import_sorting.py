import logging

try:
    import isort
except ImportError:
    isort = None

logger = logging.getLogger(__name__)


def apply_isort(content: str) -> str:
    isort.check_code(code=content)
    isort_config_kwargs = dict(
        multi_line_output=3,
        include_trailing_comma=True,
        force_grid_wrap=0,
        use_parentheses=True,
        line_length=88,
        quiet=True,
    )
    logger.debug(
        "isort.code(code=..., {})".format(
            ", ".join(f"{k}={v!r}" for k, v in isort_config_kwargs.items())
        )
    )
    result: str = isort.code(code=content, **isort_config_kwargs)
    return result
