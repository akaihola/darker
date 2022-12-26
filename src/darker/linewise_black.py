"""Re-implementation of :func:`black.format_str` as a line generator"""

from typing import Generator, List

from black import decode_bytes, detect_target_versions, get_future_imports
from black.comments import normalize_fmt_off
from black.linegen import LineGenerator, transform_line
from black.lines import EmptyLineTracker, Line
from black.mode import Feature, Mode, supports_feature
from black.parsing import lib2to3_parse


def format_str_to_chunks(  # pylint: disable=too-many-locals
    src_contents: str, *, mode: Mode
) -> Generator[List[str], None, None]:
    """Reformat a string and yield each line of new contents

    This is a re-implementation of :func:`black.format_str` modified to be a generator
    which yields each resulting chunk as a list of lines instead of concatenating them
    into a single string.

    """
    src_node = lib2to3_parse(src_contents.lstrip(), mode.target_versions)
    future_imports = get_future_imports(src_node)
    versions = mode.target_versions or detect_target_versions(src_node)
    normalize_fmt_off(src_node)
    lines = LineGenerator(
        mode=mode,
        remove_u_prefix="unicode_literals" in future_imports
        or supports_feature(versions, Feature.UNICODE_LITERALS),
    )
    elt = EmptyLineTracker(is_pyi=mode.is_pyi)
    empty_line = str(Line(mode=mode))
    empty_line_len = len(empty_line)
    after = 0
    split_line_features = {
        feature
        for feature in {Feature.TRAILING_COMMA_IN_CALL, Feature.TRAILING_COMMA_IN_DEF}
        if supports_feature(versions, feature)
    }
    num_chars = 0
    for current_line in lines.visit(src_node):
        if after:
            yield after * [empty_line]
            num_chars += after * empty_line_len
        before, after = elt.maybe_empty_lines(current_line)
        if before:
            yield before * [empty_line]
            num_chars += before * empty_line_len
        lines = [
            str(line)
            for line in transform_line(
                current_line, mode=mode, features=split_line_features
            )
        ]
        yield lines
        num_chars += sum(len(line) for line in lines)
    if not num_chars:
        normalized_content, _, newline = decode_bytes(src_contents.encode("utf-8"))
        if "\n" in normalized_content:
            yield [newline]
