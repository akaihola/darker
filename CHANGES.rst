0.3.0.dev / yyyy-mm-dd
----------------------

- Feature: Add support for black config
- Feature: Add support for ``-l``/``--line-length`` and ``-S``/``--skip-string-normalization``
- Feature: ``--diff`` outputs a diff for each file on standard output
- Feature: Require ``isort`` >= 5.0.1 and be compatible with it.
- Feature: Allow to configure ``isort`` through pyproject.toml


0.2.0 / 2020-03-11
------------------

- Feature: Retry with a larger ``git diff -U<context_lines>`` option after producing a
  re-formatted Python file which fails to result in an identical AST.
- Bugfix: Run `isort` first, and only then do the detailed ``git diff`` for Black.
