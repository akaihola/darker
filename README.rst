=================================================
 Darker – reformat and lint modified Python code
=================================================

|travis-badge|_ |license-badge|_ |pypi-badge|_ |downloads-badge|_ |black-badge|_ |changelog-badge|_

.. |travis-badge| image:: https://travis-ci.com/akaihola/darker.svg?branch=master
.. _travis-badge: https://travis-ci.com/akaihola/darker
.. |license-badge| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
.. _license-badge: https://github.com/akaihola/darker/blob/master/LICENSE.rst
.. |pypi-badge| image:: https://img.shields.io/pypi/v/darker
.. _pypi-badge: https://pypi.org/project/darker/
.. |downloads-badge| image:: https://pepy.tech/badge/darker
.. _downloads-badge: https://pepy.tech/project/darker
.. |black-badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
.. _black-badge: https://github.com/psf/black
.. |changelog-badge| image:: https://img.shields.io/badge/-change%20log-purple
.. _changelog-badge: https://github.com/akaihola/darker/blob/master/CHANGES.rst

What?
=====

This utility reformats and checks Python source code files in a Git repository.
However, it only applies reformatting and reports errors
in regions which have changed in the Git working tree since the last commit.

The reformatters and linters supported are:

- Black_ for code reformatting
- isort_ for sorting imports
- Mypy_ for static type checking
- Pylint_ for generic static checking of code
- Flake8_ for style guide enforcement

*New in version 1.1.0:* Support for Mypy_, Pylint_ and other linters.

.. _black: https://github.com/python/black
.. _isort: https://github.com/timothycrosley/isort
.. _Mypy: https://pypi.org/project/mypy
.. _Pylint: https://pypi.org/project/pylint
.. _Flake8: https://pypi.org/project/flake8

Why?
====

You want to start unifying code style in your project using black_.
Maybe you also like to standardize on how to order your imports,
or do static type checking or other static analysis for your code.

However, instead of formatting the whole code base in one giant commit,
you'd like to only change formatting when you're touching the code for other reasons.

This can also be useful
when contributing to upstream codebases that are not under your complete control.

However, partial formatting is not supported by black_ itself,
for various good reasons, and it won't be implemented either
(`134`__, `142`__, `245`__, `370`__, `511`__, `830`__).

__ https://github.com/python/black/issues/134
__ https://github.com/python/black/issues/142
__ https://github.com/python/black/issues/245
__ https://github.com/python/black/issues/370
__ https://github.com/python/black/issues/511
__ https://github.com/python/black/issues/830

This is where ``darker`` enters the stage.
This tool is for those who want to do partial formatting anyway.

Note that this tool is meant for special situations
when dealing with existing code bases.
You should just use Black_ and isort_ as is when starting a project from scratch.

How?
====

To install, use::

  pip install darker

The ``darker <myfile.py>`` command
reads the original file,
formats it using black_,
combines original and formatted regions based on edits,
and writes back over the original file.

Alternatively, you can invoke the module directly through the ``python`` executable,
which may be preferable depending on your setup.
Use ``python -m darker`` instead of ``darker`` in that case.

By default, ``darker`` just runs Black_ to reformat the code.
You can enable additional features with command line options:

- ``-i`` / ``--isort``: Reorder imports using isort_
- ``-L <linter>`` / ``--lint <linter>``: Run a supported linter:

  - ``-L mypy``: do static type checking using Mypy_
  - ``-L pylint``: analyze code using Pylint_
  - ``-L flake8``: enforce the Python style guide using Flake8_

*New in version 1.1.0:* The ``-L`` / ``--lint`` option.

Example:

.. code-block:: shell

   $ mkdir test && cd test && git init
   Initialized empty Git repository in /tmp/test/.git/
   $ echo "if True: print('hi')\n\nif False: print('there')" | tee test.py
   if True: print('hi')

   if False: print('there')
   $ git add test.py && git commit -m "Initial commit"
   [master (root-commit) a0c7c32] Initial commit
    1 file changed, 3 insertions(+)
    create mode 100644 test.py
   $ echo "if True: print('changed')\n\nif False: print('there')" | tee test.py
   if True: print('changed')

   if False: print('there')
   $ darker test.py && cat test.py
   if True:
       print("changed")

   if False: print('there')

Customizing Black and isort behavior
====================================

Project-specific default options for Black_ and isort_
are read from the project's ``pyproject.toml`` file in the repository root.
isort_ also looks for a few other places for configuration.

For more details, see:

- `Black documentation about pyproject.toml`_
- `isort documentation about config files`_

The following `command line arguments`_ can also be used to modify the defaults:

.. code-block:: shell

     -r REVISION, --revision REVISION
                           Git revision against which to compare the working
                           tree. Tags, branch names, commit hashes, and other
                           expressions like HEAD~5 work here.

     --diff                Don't write the files back, just output a diff for
                           each file on stdout. Highlight syntax on screen if
                           the `pygments` package is available.

     --check               Don't write the files back, just return the status.
                           Return code 0 means nothing would change. Return code
                           1 means some files would be reformatted.

     -i, --isort           Also sort imports using the `isort` package

     -L CMD, --lint CMD    Also run a linter on changed files. CMD can be a name
                           of path of the linter binary, or a full quoted command
                           line
     -c PATH, --config PATH
                           Ask `black` and `isort` to read configuration from PATH.
     -S, --skip-string-normalization
                           Don't normalize string quotes or prefixes
     --no-skip-string-normalization
                           Normalize string quotes or prefixes. This can be used
                           to override `skip_string_normalization = true` from a
                           configuration file.
     -l LINE_LENGTH, --line-length LINE_LENGTH
                           How many characters per line to allow [default: 88]

*New in version 1.0.0:* The ``-c``, ``-S`` and ``-l`` command line options.

*New in version 1.0.0:* isort_ is configured with ``-c`` and ``-l``, too.

*New in version 1.1.0:* The ``-r`` / ``--revision`` command line option.

*New in version 1.1.0:* The ``--diff`` command line option.

*New in version 1.1.0:* The ``--check`` command line option.

*New in version 1.1.0:* The ``--no-skip-string-normalization`` command line option.

*New in version 1.1.0:* The ``-L`` / ``--lint`` command line option.

.. _Black documentation about pyproject.toml: https://black.readthedocs.io/en/stable/pyproject_toml.html
.. _isort documentation about config files: https://timothycrosley.github.io/isort/docs/configuration/config_files/
.. _command line arguments: https://black.readthedocs.io/en/stable/installation_and_usage.html#command-line-options

Editor integration
==================

Many editors have plugins or recipes for integrating black_.
You may be able to adapt them to be used with ``darker``.
See `editor integration`__ in the black_ documentation.

__ https://github.com/psf/black/#editor-integration

PyCharm/IntelliJ IDEA
---------------------

1. Install ``darker``::

     $ pip install darker

2. Locate your ``darker`` installation folder.

   On macOS / Linux / BSD::

     $ which darker
     /usr/local/bin/darker  # possible location

   On Windows::

     $ where darker
     %LocalAppData%\Programs\Python\Python36-32\Scripts\darker.exe  # possible location

3. Open External tools in PyCharm/IntelliJ IDEA

   On macOS:

   ``PyCharm -> Preferences -> Tools -> External Tools``

   On Windows / Linux / BSD:

   ``File -> Settings -> Tools -> External Tools``

4. Click the ``+`` icon to add a new external tool with the following values:

   - Name: Darker
   - Description: Use Black to auto-format regions changed since the last git commit.
   - Program: <install_location_from_step_2>
   - Arguments: ``"$FilePath$"``

   If you need any extra command line arguments
   like the ones which change Black behavior,
   you can add them to the ``Arguments`` field, e.g.::

       --config /home/myself/black.cfg "$FilePath$"

5. Format the currently opened file by selecting ``Tools -> External Tools -> Darker``.

   - Alternatively, you can set a keyboard shortcut by navigating to
     ``Preferences or Settings -> Keymap -> External Tools -> External Tools - Darker``

6. Optionally, run ``darker`` on every file save:

   1. Make sure you have the `File Watcher`__ plugin installed.
   2. Go to ``Preferences or Settings -> Tools -> File Watchers`` and click ``+`` to add
      a new watcher:

      - Name: Darker
      - File type: Python
      - Scope: Project Files
      - Program: <install_location_from_step_2>
      - Arguments: ``$FilePath$``
      - Output paths to refresh: ``$FilePath$``
      - Working directory: ``$ProjectFileDir$``

   3. Uncheck "Auto-save edited files to trigger the watcher"

__ https://plugins.jetbrains.com/plugin/7177-file-watchers

Visual Studio Code
------------------

1. Install ``darker``::

     $ pip install darker

2. Locate your ``darker`` installation folder.

   On macOS / Linux / BSD::

     $ which darker
     /usr/local/bin/darker  # possible location

   On Windows::

     $ where darker
     %LocalAppData%\Programs\Python\Python36-32\Scripts\darker.exe  # possible location

3. Add these configuration options to VS code, ``Cmd-Shift-P``, ``Open Settings (JSON)``::

    "python.formatting.provider": "black",
    "python.formatting.blackPath": "<install_location_from_step_2>",
    "python.formatting.blackArgs": ["--diff"],

You can pass additional arguments to ``darker`` in the ``blackArgs`` option
(e.g. ``["--diff", "--isort"]``), but make sure at least ``--diff`` is included.


How does it work?
=================

Darker takes a ``git diff`` of your Python files,
records which lines of current files have been edited or added since the last commit.
It then runs black_ and notes which chunks of lines were reformatted.
Finally, only those reformatted chunks on which edited lines fall (even partially)
are applied to the edited file.

Also, in case the ``--isort`` option was specified,
isort_ is run on each edited file before applying black_.
Similarly, each linter requested using the `--lint <command>` option is run,
and only linting errors/warnings on modified lines are displayed.


License
=======

BSD. See ``LICENSE.rst``.


Prior art
=========

- black-macchiato__
- darken__ (deprecated in favor of Darker; thanks Carreau__ for inspiration!)

__ https://github.com/wbolster/black-macchiato
__ https://github.com/Carreau/darken
__ https://github.com/Carreau


GitHub stars trend
==================

|stargazers|_

.. |stargazers| image:: https://starchart.cc/akaihola/darker.svg
.. _stargazers: https://starchart.cc/akaihola/darker
