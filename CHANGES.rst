Unreleased_
===========

These features will be included in the next release:

Added
-----
- The ``--jobs`` option now specifies how many Darker jobs are used to process files in
  parallel to complete reformatting/linting faster.
- Linters can now be run in the GitHub Action using the ``lint:`` option.
  
Fixed
-----
- Avoid memory leak from using ``@lru_cache`` on a method.


1.4.2_ - 2022-03-12
===================

Added
-----
- Document ``isort``'s requirement to be run in the same environment as
  the modules which are processed.
- Document VSCode and ``--lint``/``-L`` incompatibility in the README.
- Guard against breaking changes in ``isort`` by testing against its ``main``
  branch in the ``test-future`` GitHub Workflow.
- ``release_tools/bump_version.py`` script for incrementing version numbers and
  milestone numbers in various files when releasing.

Fixed
-----
- Fix NixOS builds when ``pytest-darker`` calls ``pylint``. Needed to activate
  the virtualenv.
- Allow more time to pass when checking file modification times in a unit test.
  Windows tests on GitHub are sometimes really slow.


1.4.1_ - 2022-02-17
===================

Added
-----
- Run tests on CI against Black ``main`` branch to get an early warning of
  incompatible changes which would break Darker.
- Determine the commit range to check automatically in the GitHub Action.
- Improve GitHub Action documentation.
- Add Nix CI builds on Linux and macOS.
- Add a YAML linting workflow to the Darker repository.
- Updated Mypy to version 0.931.
- Guard against breaking changes in Black by testing against its ``main`` branch
  in the ``test-future`` GitHub Workflow.

Fixed
-----
- Consider ``.py.tmp`` as files which should be reformatted.
  This enables VSCode Format On Save.
- Use the latest release of Darker instead of 1.3.2 in the GitHub Action.
  

1.4.0_ - 2022-02-08
===================

Added
-----
- Experimental GitHub Actions integration
- Consecutive lines of linter output are now separated by a blank line.
- Highligh linter output if Pygments is installed.
- Allow running Darker on plain directories in addition to Git repositories.

Fixed
-----
- ``regex`` module now always available for unit tests
- Compatibility with NixOS. Keep ``$PATH`` intact so Git can be called.
- Updated tests to pass on new Pygments versions
- Compatibility with Black 22.1
- Removed additional newline at the end of the file with the ``--stdout`` flag
  compared to without.
- Handle isort file skip comment ``#isort:file_skip`` without an exception.
- Fix compatibility with Pygments 2.11.2.

Removed
-------
- Drop support for Python 3.6 which has reached end of life.


1.3.2_ - 2021-10-28
===================

Added
-----
- Linter failures now result in an exit value of 1, regardless of whether ``--check``
  was used or not. This makes linting in Darker compatible with ``pre-commit``.
- Declare Python 3.9 and 3.10 as supported in package metadata
- Run test build in a Python 3.10 environment on GitHub Actions
- Explanation in README about how to use ``args:`` in pre-commit configuration

Fixed
-----
- ``.py.<hash>.tmp`` files from VSCode are now correctly compared to corresponding
  ``.py`` files in earlier revisions of the Git reposiotry
- Honor exclusion patterns from Black configuration when choosing files to reformat.
  This only applies when recursing directories specified on the command line, and only
  affects Black reformatting, not ``isort`` or linters.
- ``--revision rev1...rev2`` now actually applies reformatting and filters linter output
  to only lines modified compared to the common ancestor of ``rev1`` and ``rev2``
- Relative paths are now resolved correctly when using the ``--stdout`` option
- Downgrade to Flake8 version 3.x for Pytest compatibility.
  See `tholo/pytest-flake8#81`__

__ https://github.com/tholo/pytest-flake8/issues/81


1.3.1_ - 2021-10-05
===================

Added
-----
- Empty and all-whitespace files are now reformatted properly
- Darker now allows itself to modify files when called with ``pre-commit -o HEAD``, but
  also emits a warning about this being an experimental feature
- Mention Black's possible new line range formatting support in README
- Darker can now be used in a plain directory tree in addition to Git repositories

Fixed
-----
- ``/foo $ darker --diff /bar/my-repo`` now works: the current working directory can be
  in a different part of the directory hierarchy
- An incompatible ``isort`` version now causes a short user-friendly error message
- Improve bisect performance by not recomputing invariant data within bisect loop


1.3.0_ - 2021-09-04
===================

Added
-----
- Support for Black's ``--skip-magic-trailing-comma`` option
- ``darker --diff`` output is now identical to that of ``black --diff``
- The ``-d`` / ``--stdout`` option outputs the reformatted contents of the single Python
  file provided on the command line.
- Terminate with an error if non-existing files or directories are passed on the command
  line. This also improves the error from misquoted parameters like ``"--lint pylint"``.
- Allow Git test case to run slower when checking file timestamps. CI can be slow.
- Fix compatibility with Black >= 21.7b1.dev9
- Show a simple one-line error instead of full traceback on some unexpected failures
- Skip reformatting files set to be excluded by Black in configuration files

Fixed
-----
- Ensure a full revision range ``--revision <COMMIT_A>..<COMMIT_B>`` where
  COMMIT_B is *not* ``:WORKTREE:`` works too.
- Hide fatal error from Git on stderr when ``git show`` doesn't find the file in rev1.
  This isn't fatal from Darker's point of view since it's a newly created file.
- Use forward slash as the path separator when calling Git in Windows. At least
  ``git show`` and ``git cat-file`` fail when using backslashes.


1.2.4_ - 2021-06-27
===================

Added
-----
- Upgrade to and satisfy MyPy 0.910 by adding ``types-toml`` as a test dependency, and
  ``types-dataclasses`` as well if running on Python 3.6.
- Installation instructions in a Conda environment.

Fixed
-----
- Git-related commands in the test suite now ignore the user's ``~/.gitconfig``.
- Now works again even if ``isort`` isn't installed
- AST verification no longer erroneously fails when using ``--isort``
- Historical comparisons like ``darker --diff --revision=v1.0..v1.1`` now actually
  compare the second revision and not the working tree files on disk.
- Ensure identical Black formatting on Unix and Windows by always passing Unix newlines
  to Black


1.2.3_ - 2021-05-02
===================

Added
-----
- A unified ``TextDocument`` class to represent source code file contents
- Move help texts into the separate ``darker.help`` module
- If AST differs with zero context lines, search for the lowest successful number of
  context lines using a binary search to improve performance
- Return an exit value of 1 also if there are failures from any of the linters on
  modified lines
- Run GitHub Actions for the test build also on Windows and macOS

Fixed
-----
- Compatibility with MyPy 0.812
- Keep newline character sequence and text encoding intact when modifying files
- Installation now works on Windows
- Improve compatibility with pre-commit. Fallback to compare against HEAD if
  ``--revision :PRE-COMMIT:`` is set, but ``PRE_COMMIT_FROM_REF`` or
  ``PRE_COMMIT_TO_REF`` are not set.


1.2.2_ - 2020-12-30
===================

Added
-----
- Get revision range from pre-commit_'s ``PRE_COMMIT_FROM_REF`` and
  ``PRE_COMMIT_TO_REF`` environment variables when using the ``--revision :PRE-COMMIT:``
  option
- Configure a pre-commit hook for Darker itself
- Add a Darker package to conda-forge_.

Fixed
-----
- ``<commit>...`` now compares always correctly to the latest common ancestor
- Migrate from Travis CI to GitHub Actions


1.2.1_ - 2020-11-30
===================

Added
-----
- Travis CI now runs Pylint_ on modified lines via pytest-darker_
- Darker can now be used as a pre-commit hook (see pre-commit_)
- Document integration with Vim
- Thank all contributors right in the ``README``
- ``RevisionRange`` class and Git repository test fixture improvements in preparation
  for a larger refactoring coming in `#80`_

Fixed
-----
- Improve example in ``README`` and clarify that path argument can also be a directory


1.2.0_ - 2020-09-09
===================

Added
-----
- Configuration for Darker can now be done in ``pyproject.toml``.
- The formatting of the Darker code base itself is now checked using Darker itself and
  pytest-darker_. Currently the formatting is a mix of `Black 19.10`_ and `Black 20.8`_
  rules, and Travis CI only requires Black 20.8 formatting for lines modified in merge
  requests. In a way, Darker is now eating its own dogfood.
- Support commit ranges for ``-r``/``--revision``. Useful for comparing to the best
  common ancestor, e.g. ``master...``.
- Configure Flake8 verification for Darker's own source code


1.1.0_ - 2020-08-15
===================

Added
-----
- ``-L``/``--lint`` option for running a linter for modified lines.
- ``--check`` returns ``1`` from the process but leaves files untouched if any file
  would require reformatting
- Untracked Python files – e.g. those added recently – are now also reformatted
- ``-r <rev>`` / ``--revision <rev>`` can be used to specify the Git revision to compare
  against when finding out modified lines. Defaults to ``HEAD`` as before.
- ``--no-skip-string-normalization`` flag to override
  ``skip_string_normalization = true`` from a configuration file
- The ``--diff`` and ``--lint`` options will highlight syntax on screen if the
  pygments_ package is available.

Fixed
-----
- Paths from ``--diff`` are now relative to current working directory, similar to output
  from ``black --diff``, and blank lines after the lines markers (``@@ ... @@``) have
  been removed.


1.0.0_ - 2020-07-15
===================

Added
-----
- Support for black config
- Support for ``-l``/``--line-length`` and ``-S``/``--skip-string-normalization``
- ``--diff`` outputs a diff for each file on standard output
- Require ``isort`` >= 5.0.1 and be compatible with it
- Allow to configure ``isort`` through ``pyproject.toml``


0.2.0_ - 2020-03-11
===================

Added
-----
- Retry with a larger ``git diff -U<context_lines>`` option after producing a
  re-formatted Python file which fails to result in an identical AST

Fixed
-----
- Run `isort` first, and only then do the detailed ``git diff`` for Black


0.1.1_ - 2020-02-17
===================

Fixed
-----
- logic for choosing original/formatted chunks


0.1.0_ - 2020-02-17
===================

Added
-----
- Initial implementation

.. _Unreleased: https://github.com/akaihola/darker/compare/1.4.2...HEAD
.. _1.4.2: https://github.com/akaihola/darker/compare/1.4.1...1.4.2
.. _1.4.1: https://github.com/akaihola/darker/compare/1.4.0...1.4.1
.. _1.4.0: https://github.com/akaihola/darker/compare/1.3.2...1.4.0
.. _1.3.2: https://github.com/akaihola/darker/compare/1.3.1...1.3.2
.. _1.3.1: https://github.com/akaihola/darker/compare/1.3.0...1.3.1
.. _1.3.0: https://github.com/akaihola/darker/compare/1.2.4...1.3.0
.. _1.2.4: https://github.com/akaihola/darker/compare/1.2.3...1.2.4
.. _1.2.3: https://github.com/akaihola/darker/compare/1.2.2...1.2.3
.. _1.2.2: https://github.com/akaihola/darker/compare/1.2.1...1.2.2
.. _1.2.1: https://github.com/akaihola/darker/compare/1.2.0...1.2.1
.. _1.2.0: https://github.com/akaihola/darker/compare/1.1.0...1.2.0
.. _1.1.0: https://github.com/akaihola/darker/compare/1.0.0...1.1.0
.. _1.0.0: https://github.com/akaihola/darker/compare/0.2.0...1.0.0
.. _0.2.0: https://github.com/akaihola/darker/compare/0.1.1...0.2.0
.. _0.1.1: https://github.com/akaihola/darker/compare/0.1.0...0.1.1
.. _0.1.0: https://github.com/akaihola/darker/releases/tag/0.1.0
.. _pre-commit: https://pre-commit.com/
.. _conda-forge: https://conda-forge.org/
.. _#80: https://github.com/akaihola/darker/issues/80
.. _pytest-darker: https://pypi.org/project/pytest-darker/
.. _Black 19.10: https://github.com/psf/black/blob/master/CHANGES.md#1910b0
.. _Black 20.8: https://github.com/psf/black/blob/master/CHANGES.md#208b0
.. _Pylint: https://pypi.org/project/pylint
.. _pygments: https://pypi.org/project/Pygments/
