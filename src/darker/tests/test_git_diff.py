from darker.git_diff import get_edit_linenums
from darker.tests.example_3_lines import CHANGE_SECOND_LINE


def test_get_edited_line_numbers():
    result = list(get_edit_linenums(CHANGE_SECOND_LINE.encode('ascii')))
    assert result == [1]
