"""Example Python source code for testing."""

A_PY = ["import sys", "import os", "print( '{}'.format('42'))", ""]
A_PY_BLACK = ["import sys", "import os", "", 'print("{}".format("42"))', ""]
A_PY_BLACK_ISORT = ["import os", "import sys", "", 'print("{}".format("42"))', ""]
A_PY_BLACK_FLYNT = ["import sys", "import os", "", 'print("42")', ""]
