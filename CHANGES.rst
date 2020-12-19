Unreleased_
===========

These features will be included in the next release:

Added
-----
- Configure a pre-commit hook for Darker itself

Fixed
-----
- ``<commit>...`` now compares always correctly to the latest common ancestor


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
- The ``--diff`` option will highlight syntax on screen if the ``pygments`` package is
  available.

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

.. _Unreleased: https://github.com/akaihola/darker/compare/1.2.1...HEAD
.. _1.2.1: https://github.com/akaihola/darker/compare/1.2.0...1.2.1
.. _1.2.0: https://github.com/akaihola/darker/compare/1.1.0...1.2.0
.. _1.1.0: https://github.com/akaihola/darker/compare/1.0.0...1.1.0
.. _1.0.0: https://github.com/akaihola/darker/compare/0.2.0...1.0.0
.. _0.2.0: https://github.com/akaihola/darker/compare/0.1.1...0.2.0
.. _0.1.1: https://github.com/akaihola/darker/compare/0.1.0...0.1.1
.. _0.1.0: https://github.com/akaihola/darker/releases/tag/0.1.0
.. _pre-commit: https://pre-commit.com/
.. _#80: https://github.com/akaihola/darker/issues/80
.. _pytest-darker: https://pypi.org/project/pytest-darker/
.. _Black 19.10: https://github.com/psf/black/blob/master/CHANGES.md#1910b0
.. _Black 20.8: https://github.com/psf/black/blob/master/CHANGES.md#208b0
.. _Pylint: https://pypi.org/project/pylint
