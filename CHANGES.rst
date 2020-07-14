Unreleased_
===========

These features will be included in the next release:

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

.. _Unreleased: https://github.com/akaihola/darker/compare/0.2.0..HEAD
.. _0.2.0: https://github.com/akaihola/darker/compare/0.1.1..0.2.0
.. _0.1.1: https://github.com/akaihola/darker/compare/0.1.0..0.1.1
.. _0.1.0: https://github.com/akaihola/darker/releases/tag/0.1.0
