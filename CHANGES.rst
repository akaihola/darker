Unreleased_
===========

These features will be included in the next release:

Added
-----
- CI workflow, enable caching of packages via uv across all actions
- New exit codes 2 for file not found, 3 for invalid command line arguments, 4 for
  missing dependencies and 123 for unknown failures.
- Display exit code in parentheses after error message.
- Do not reformat renamed files.
- The ``--preview`` configuration flag is now supported in the configuration files for
  Darker and Black
- The ``--formatter=black`` option (the default) has been added in preparation for
  future formatters.
- ``--formatter=none`` now skips running Black. This is useful when you only want to run
  Isort or Flynt_.
- Black_ is no longer installed by default. Use ``pip install 'darker[black]'`` to get
  Black support.
- pyupgrade_ is now supported as a formatter plugin. Note that changes from pyupgrade
  are applied on a per-file basis, not only for modified lines as with Black_ and Ruff_.

Removed
-------
- **Backwards incompatible change:** Baseline linting support (``-L``/``--lint`` option)
  has been removed. Use the Graylint_ tool instead.
- In the Darker configuration file under ``[tool.darker]``, the Black configuration
  options ``skip_string_normalization`` and ``skip_magic_trailing_comma`` are no longer
  valid. Use ``[tool.black]`` instead.

Fixed
-----
- Update to Darkgraylib 2.2.0 to fix the configuration dump, the output of
  ``--version``, the Git "dubious ownership" issue, and source code line splitting
  (see below).
- In the configuration dump printed when ``-vv`` verbosity is used, the configuration
  section is now correctly named ``[tool.darker]`` instead of ``[tool.darkgraylib]``.
- Pass Darker version to `~darkgraylib.command_line.make_argument_parser` to make
  ``--version`` display the correct version number.
- Pass full environment to Git to avoid the "dubious ownership" error.
- Work around a `pathlib.Path.resolve` bug in Python 3.9 on Windows.
  The work-around should be removed when Python 3.9 is no longer supported.
- Add missing configuration flag for Flynt_.
- Only split source code lines at Python's universal newlines (LF, CRLF, CR).
- The Darker GitHub action now respects the ``working-directory`` input option.

Internal
--------
- CI workflow to post recent project activity in a discussion. Triggered manually.
- CI "future" test now tests against ``main`` of Darkgraylib_ in addition to Black_,
  Flynt_ and isort_.
- Prevent Pylint from updating beyond version 3.2.7 due to dropped Python 3.8 support.
- Invoking Black is now implemented as a plugin. This allows for easier integration of
  other formatters in the future. There's also a dummy ``none`` formatter plugin.
- Update ``darkgray-dev-tools`` for Pip >= 24.1 compatibility.
- Drop dependency on ``pip`` and ``distutils`` in the weekly CI "future" test. Use
  ``packaging`` instead.
- No need to use `typing.Pattern` instead of `re.Pattern` in Python 3.9+.
- Always use newest artifact upload/download actions from the v4 series in the CI build.
- Use `datetime.datetime.now()`, not ``.utcnow()`` to silence a deprecation warning.
- Suppress logging about Flynt unless Flynt is enabled.


2.1.1_ - 2024-04-16
===================

Added
-----
- In the Darker configuration file under ``[tool.darker]``, the Black configuration
  options ``skip_string_normalization`` and ``skip_magic_trailing_comma`` have been
  deprecated and will be removed in Darker 3.0. A deprecation warning is now displayed
  if they are still used.

Fixed
-----
- A dash (``-``) is now allowed as the single source filename when using the
  ``--stdout`` option. This makes the option compatible with the
  `new Black extension for VSCode`__.
- Badge links in the README on GitHub.
- Handling of relative paths and running from elsewhere than repository root.

__ https://github.com/microsoft/vscode-black-formatter

Internal
-------
- The ``release_tools/update_contributors.py`` script was moved to the
  ``darkgray-dev-tools`` repository.


2.1.0_ - 2024-03-27
===================

Added
-----
- Support for Python 3.12 in the package metadata and the CI build.
- Update to Black 24.2.x and isort 5.13.x in pre-commit configuration.
- Improved "How does it work?" section in the README.
- README section on limitations and work-arounds.

Fixed
-----
- Escape pipe symbols (``|``) in the README to avoid RestructuredText rendering issues.
- Compatibility with Flynt 0.78.0 and newer.

Internal
--------
- Mark the Darker package as annotated with type hints.
- Update to ``ioggstream/bandit-report-artifacts@v1.7.4`` in CI.
- Test against Flynt_ ``master`` branch in the CI build.
- Update to Darkgraylib 1.1.1 to get fixes for README formatting.
- ``bump_version.py`` is now in the separate ``darkgray-dev-tools`` repository.
- Skip tests on Python 3.13-dev in Windows and macOS. C extension builds are failing,
  this exclusion is to be removed when Python 3.13 has been removed.
- Bump-version pre-commit hook pattern: ``rev: vX.Y.Z`` instead of ``X.Y.Z``.


2.0.0_ - 2024-03-13
===================

Added
-----
- The command ``darker --config=check-darker.toml`` now runs Flake8_, Mypy_,
  pydocstyle_, Pylint_ and Ruff_ on modified lines in Python files. Those tools are
  included in the ``[test]`` extra.
- The minimum Ruff_ version is now 0.0.292. Its configuration in ``pyproject.toml`` has
  been updated accordingly.
- The contribution guide now gives better instructions for reformatting and linting.

Removed
-------
- Drop support for Python 3.7 which has reached end of life.
- Move linting support to Graylint_ but keep the ``-L``/``--lint`` option for now.

Fixed
-----
- `Black 24.2.0`_ compatibility by using the new `darkgraylib.files.find_project_root`
  instead of the implementation in Black.
- `Black 24.2.1`_ compatibility by detecting the new `black.parsing.ASTSafetyError`
  instead of `AssertionError` when Black>=24.2.1 is in use.
- Work around some situations where Windows errors due to a too long Git command line.

Internal
--------
- Separate GitHub workflow for checking code formatting and import sorting.
- Also check the action, release tools and ``setup.py`` in the build workflows.
- Require Darkgraylib 1.0.x and Graylint 1.0.x.
- Update 3rd party GitHub actions to avoid using deprecated NodeJS versions.
- CI build now shows a diff between output of ``darker --help`` and its output as
  included ``README.rst`` in case the two differ.
- Move code used by both Darker and Graylint_ into the Darkgraylib_ library.
- Don't run pytest-darker_ in the CI build. It's lagging quite a bit behind.
- Make sure NixOS_ builds have good SSL certificates installed.


1.7.3_ - 2024-02-27
===================

Added
-----
- Limit Black_ to versions before 24.2 until the incompatibility is resolved.

Fixed
-----
- Typos in README.
- Fix compatibility with Pygments 2.4.0 and 2.17.2 in unit tests.

Internal
--------
- Stop testing on Python 3.7. Note: dropping support to be done in a separate PR.
- Usage of the Black_ ``gen_python_files(gitignore_dict=...)`` parameter.
- ``show_capture`` option in Pytest configuration.
- Ignore some linter messages by recent versions of linters used in CI builds.
- Update `actions/checkout@v3` to `actions/checkout@v4` in CI builds.


1.7.2_ - 2023-07-12
===================

Added
-----
- Add a ``News`` link on the PyPI page.
- Allow ``-`` as the single source filename when using the ``--stdin-filename`` option.
  This makes the option compatible with Black_.

Fixed
-----
- Revert running ``commit-range`` from the repository itself. This broke the GitHub
  action.
- Python 3.12 compatibility in multi-line string scanning.
- Python 3.12 compatibility for the GitHub Action.
- Use the original repository working directory name as the name of the temporary
  directory for getting the linter baseline. This avoids issues with Mypy_ when there's
  an ``__init__.py`` in the repository root.
- Allow ``--target-version=py312`` since newest Black_ supports it.

Internal
--------
- Upgrade NixOS_ tests to use Python 3.11 on both Linux and macOS.
- Move ``git_repo`` fixture to ``darkgraylib``.
- In CI builds, show a diff of changed ``--help`` output if ``README.rst`` is outdated.
- Upgrade ``install-nix-action`` to version 22 in CI to fix an issue with macOS.
- Allow a comment in milestone titles in the ``bump_version`` script.


1.7.1_ - 2023-03-26
===================

Fixed
-----
- Use ``git worktree`` to create a repository checkout for baseline linting. This avoids
  issues with the previous ``git clone`` and ``git checkout`` based approach.
- Disallow Flynt_ version 0.78 and newer to avoid an internal API incompatibility.
- Linting fixes: Use ``stacklevel=2`` in ``warnings.warn()`` calls as suggested by
  Flake8_; skip Bandit check for virtualenv creation in the GitHub Action;
  use ``ignore[method-assign]`` as suggested by Mypy_.
- Configuration options spelled with hyphens in ``pyproject.toml``
  (e.g. ``line-length = 88``) are now supported.
- In debug log output mode, configuration options are now always spelled with hyphens
  instead of underscores.

Internal
--------
- Prefix GitHub milestones with ``Darker`` for clarity since we'll have two additional
  related repositories soon in the same project.
- In CI builds, run the ``commit-range`` action from the current checkout instead of
  pointing to a release tag. This fixes workflows when in a release branch.


1.7.0_ - 2023-02-11
===================

Added
-----
- ``-f`` / ``--flynt`` option for converting old-style format strings to f-strings as
  supported in Python 3.6+.
- Black_'s ``target-version =`` configuration file option and ``-t`` /
  ``--target-version`` command line option
- In ``README.rst``, link to GitHub searches which find public repositories that
  use Darker.
- Linters are now run twice: once for ``rev1`` to get a baseline, and another time for
  ``rev2`` to get the current situation. Old linter messages which fall on unmodified
  lines are hidden, so effectively the user gets new linter messages introduced by
  latest changes, as well as persistent linter messages on modified lines.
- ``--stdin-filename=PATH`` now allows reading contents of a single file from standard
  input. This also makes ``:STDIN:``, a new magic value, the default ``rev2`` for
  ``--revision``.

Fixed
-----
- Pass Git errors to stderr correctly both in raw and encoded subprocess output mode.
- Split and join command lines using ``shlex`` from the Python standard library. This
  deals with quoting correctly.

Internal
--------
- Make unit tests compatible with ``pytest --log-cli-level==DEBUG``.
  Doctests are still incompatible due to
  `pytest#5908 <https://github.com/pytest-dev/pytest/issues/5908>`_.
- Add configuration for ``darglint`` and ``flake8-docstrings``, preparing for enabling
  those linters in CI builds.
- Compatibility of highlighting unit tests with Pygments 2.14.0.
- In the CI test workflow, don't use environment variables to add a Black_ version
  constraint to the ``pip`` command. This fixes the Windows builds.
- Add a work-around for cleaning up temporary directories. Needed for Python 3.7 on
  Windows.
- Configure ``coverage`` to use relative paths in the Darker repository. This enables
  use of ``cov_to_lint.py``
- Satisfy Pylint's ``use-dict-literal`` check in Darker's code base.
- Use ``!r`` to quote values in format strings as suggested by recent Flake8_ versions.


1.6.1_ - 2022-12-28
===================

Added
-----
- Declare Python 3.11 as supported in package metadata.
- Document how to set up a development environment, run tests, run linters and update
  contributors list in ``CONTRIBUTING.rst``.
- Document how to pin reformatter/linter versions in ``pre-commit``.
- Clarify configuration of reformatter/linter tools in README and ``--help``.

Fixed
-----
- Fix compatibility with ``black-22.10.1.dev19+gffaaf48`` and later – an argument was
  replaced in ``black.files.gen_python_files()``.
- GitHub Action example now omits ``revision:`` since the commit range is obtained
  automatically.

Internal
--------
- Pin Black_ to version 22.12.0 in the CI build to ensure consistent formatting of
  Darker's own code base.
- Fix tests to work with Git older than version 2.28.x.
- ``test-bump-version`` workflow will now succeed also in a release branch.


1.6.0_ - 2022-12-19
===================

Fixed
-----
- Fix compatibility with ``black-22.10.1.dev19+gffaaf48`` and later – an argument was
  replaced in ``black.files.gen_python_files()``.

Internal
--------
- Upgrade linters in CI and modify code to satisfy their new requirements.
- Upgrade to ``setup-python@v4`` in all GitHub workflows.
- ``bump_version.py`` now accepts an optional GitHub token with the ``--token=``
  argument. The ``test-bump-version`` workflow uses that, which should help deal with
  GitHub's API rate limiting.
- Upgrade CI to use environment files instead of the deprecated ``set-output`` method.
- Fix Safety check in CI.
- Don't do a development install in the ``help-in-readme.yml`` workflow. Something
  broke this recently.


1.5.1_ - 2022-09-11
===================

Fixed
-----
- ``darker --revision=a..b .`` now works since the repository root is now always
  considered to have existed in all historical commits.
- Ignore linter lines which refer to non-Python files or files outside the common root
  of paths on the command line. Fixes a failure when Pylint notifies about obsolete
  options in ``.pylintrc``.
- Fix linter output parsing for full Windows paths which include a drive letter.
- Stricter rules for linter output parsing.

Internal
--------
- Add a CI workflow which verifies that the ``darker --help`` output in ``README.rst``
  is up to date.
- Only run linters, security checks and package builds once in the CI build.
- Small simplification: It doesn't matter whether ``isort`` was run or not, only
  whether changes were made.
- Refactor Black_ and ``isort`` file exclusions into one data structure.
- For linting Darker's own code base, require Pylint 2.6.0 or newer. This avoids the
  need to skip the obsolete ``bad-continuation`` check now removed from Pylint.


1.5.0_ - 2022-04-23
===================

Added
-----
- The ``--workers``/``-W`` option now specifies how many Darker jobs are used to
  process files in parallel to complete reformatting/linting faster.
- Linters can now be installed and run in the GitHub Action using the ``lint:`` option.
- Sort imports only if the range of modified lines overlaps with changes resulting from
  sorting the imports.
- Allow force enabling/disabling of syntax highlighting using the ``color`` option in
  ``pyproject.toml``, the ``PY_COLORS`` and ``NO_COLOR`` environment variables, and the
  ``--color``/``--no-color`` command line options.
- Syntax highlighting is now enabled by default in the GitHub Action.

Fixed
-----
- Avoid memory leak from using ``@lru_cache`` on a method.
- Handle files encoded with an encoding other than UTF-8 without an exception.
- The GitHub Action now handles missing ``revision:`` correctly.
- Darker now reads its own configuration from the file specified using
  ``-c``/``--config``, or in case a directory is specified, from ``pyproject.toml``
  inside that directory.

Internal
--------
- ``pytest>=6.2.0`` now required for the test suite due to type hinting issues.
- Update ``cachix/install-nix-action`` to ``v17`` to fix macOS build error.
- Downgrade Python from 3.10 to 3.9 in the macOS NixOS_ build on GitHub due to a build
  error with Python 3.10.


1.4.2_ - 2022-03-12
===================

Added
-----
- Document ``isort``'s requirement to be run in the same environment as
  the modules which are processed.
- Document VSCode and ``--lint``/``-L`` incompatibility in the README.

Fixed
-----
- Multiline strings are now always reformatted completely even if just a part
  was modified by the user and reformatted by Black_. This prevents the
  "back-and-forth indent" symptom.

Internal
--------
- Guard against breaking changes in ``isort`` by testing against its ``main``
  branch in the ``test-future`` GitHub Workflow.
- ``release_tools/bump_version.py`` script for incrementing version numbers and
  milestone numbers in various files when releasing.
- Fix NixOS_ builds when ``pytest-darker`` calls ``pylint``. Needed to activate
  the virtualenv.
- Allow more time to pass when checking file modification times in a unit test.
  Windows tests on GitHub are sometimes really slow.


1.4.1_ - 2022-02-17
===================

Added
-----
- Determine the commit range to check automatically in the GitHub Action.
- Improve GitHub Action documentation.

Fixed
-----
- Consider ``.py.tmp`` as files which should be reformatted.
  This enables VSCode Format On Save.
- Use the latest release of Darker instead of 1.3.2 in the GitHub Action.

Internal
--------
- Add Nix CI builds on Linux and macOS.
- Add a YAML linting workflow to the Darker repository.
- Updated Mypy_ to version 0.931.
- Guard against breaking changes in Black_ by testing against its ``main`` branch
  in the ``test-future`` GitHub Workflow.


1.4.0_ - 2022-02-08
===================

Added
-----
- Experimental GitHub Actions integration
- Consecutive lines of linter output are now separated by a blank line.
- Highlight linter output if Pygments is installed.
- Allow running Darker on plain directories in addition to Git repositories.

Fixed
-----
- Compatibility with `Black 22.1`_
- Removed additional newline at the end of the file with the ``--stdout`` flag
  compared to without.
- Handle isort file skip comment ``#isort:file_skip`` without an exception.
- Fix compatibility with Pygments 2.11.2.

Removed
-------
- Drop support for Python 3.6 which has reached end of life.

Internal
--------
- ``regex`` module now always available for unit tests
- Compatibility with NixOS_. Keep ``$PATH`` intact so Git can be called.
- Updated tests to pass on new Pygments versions


1.3.2_ - 2021-10-28
===================

Added
-----
- Linter failures now result in an exit value of 1, regardless of whether ``--check``
  was used or not. This makes linting in Darker compatible with ``pre-commit``.
- Declare Python 3.9 and 3.10 as supported in package metadata
- Explanation in README about how to use ``args:`` in pre-commit configuration

Fixed
-----
- ``.py.<hash>.tmp`` files from VSCode are now correctly compared to corresponding
  ``.py`` files in earlier revisions of the Git reposiotry
- Honor exclusion patterns from Black_ configuration when choosing files to reformat.
  This only applies when recursing directories specified on the command line, and only
  affects Black_ reformatting, not ``isort`` or linters.
- ``--revision rev1...rev2`` now actually applies reformatting and filters linter output
  to only lines modified compared to the common ancestor of ``rev1`` and ``rev2``
- Relative paths are now resolved correctly when using the ``--stdout`` option

Internal
--------
- Run test build in a Python 3.10 environment on GitHub Actions
- Downgrade to Flake8_ version 3.x for Pytest compatibility.
  See `tholo/pytest-flake8#81`__

__ https://github.com/tholo/pytest-flake8/issues/81


1.3.1_ - 2021-10-05
===================

Added
-----
- Empty and all-whitespace files are now reformatted properly
- Darker now allows itself to modify files when called with ``pre-commit -o HEAD``, but
  also emits a warning about this being an experimental feature
- Mention Black_'s possible new line range formatting support in README
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
- Support for Black_'s ``--skip-magic-trailing-comma`` option
- ``darker --diff`` output is now identical to that of ``black --diff``
- The ``-d`` / ``--stdout`` option outputs the reformatted contents of the single Python
  file provided on the command line.
- Terminate with an error if non-existing files or directories are passed on the command
  line. This also improves the error from misquoted parameters like ``"--lint pylint"``.
- Fix compatibility with Black_ >= 21.7b1.dev9
- Show a simple one-line error instead of full traceback on some unexpected failures
- Skip reformatting files set to be excluded by Black_ in configuration files

Fixed
-----
- Ensure a full revision range ``--revision <COMMIT_A>..<COMMIT_B>`` where
  COMMIT_B is *not* ``:WORKTREE:`` works too.
- Hide fatal error from Git on stderr when ``git show`` doesn't find the file in rev1.
  This isn't fatal from Darker's point of view since it's a newly created file.
- Use forward slash as the path separator when calling Git in Windows. At least
  ``git show`` and ``git cat-file`` fail when using backslashes.

Internal
--------
- Allow Git test case to run slower when checking file timestamps. CI can be slow.


1.2.4_ - 2021-06-27
===================

Added
-----
- Installation instructions in a Conda environment.

Fixed
-----
- Git-related commands in the test suite now ignore the user's ``~/.gitconfig``.
- Now works again even if ``isort`` isn't installed
- AST verification no longer erroneously fails when using ``--isort``
- Historical comparisons like ``darker --diff --revision=v1.0..v1.1`` now actually
  compare the second revision and not the working tree files on disk.
- Ensure identical Black_ formatting on Unix and Windows by always passing Unix newlines
  to Black_

Internal
--------
- Upgrade to and satisfy Mypy_ 0.910 by adding ``types-toml`` as a test dependency, and
  ``types-dataclasses`` as well if running on Python 3.6.


1.2.3_ - 2021-05-02
===================

Added
-----
- If AST differs with zero context lines, search for the lowest successful number of
  context lines using a binary search to improve performance
- Return an exit value of 1 also if there are failures from any of the linters on
  modified lines

Fixed
-----
- Keep newline character sequence and text encoding intact when modifying files
- Installation now works on Windows
- Improve compatibility with pre-commit. Fallback to compare against HEAD if
  ``--revision :PRE-COMMIT:`` is set, but ``PRE_COMMIT_FROM_REF`` or
  ``PRE_COMMIT_TO_REF`` are not set.

Internal
--------
- A unified ``TextDocument`` class to represent source code file contents
- Move help texts into the separate ``darker.help`` module
- Run GitHub Actions for the test build also on Windows and macOS
- Compatibility with Mypy_ 0.812


1.2.2_ - 2020-12-30
===================

Added
-----
- Get revision range from pre-commit_'s ``PRE_COMMIT_FROM_REF`` and
  ``PRE_COMMIT_TO_REF`` environment variables when using the ``--revision :PRE-COMMIT:``
  option
- Add a Darker package to conda-forge_.

Fixed
-----
- ``<commit>...`` now compares always correctly to the latest common ancestor

Internal
--------
- Configure a pre-commit hook for Darker itself
- Migrate from Travis CI to GitHub Actions


1.2.1_ - 2020-11-30
===================

Added
-----
- Darker can now be used as a pre-commit hook (see pre-commit_)
- Document integration with Vim
- Thank all contributors right in the ``README``

Fixed
-----
- Improve example in ``README`` and clarify that path argument can also be a directory

Internal
--------
- Travis CI now runs Pylint_ on modified lines via pytest-darker_
- ``RevisionRange`` class and Git repository test fixture improvements in preparation
  for a larger refactoring coming in `#80`_


1.2.0_ - 2020-09-09
===================

Added
-----
- Configuration for Darker can now be done in ``pyproject.toml``.
- Support commit ranges for ``-r``/``--revision``. Useful for comparing to the best
  common ancestor, e.g. ``master...``.

Internal
--------
- The formatting of the Darker code base itself is now checked using Darker itself and
  pytest-darker_. Currently the formatting is a mix of `Black 19.10`_ and `Black 20.8`_
  rules, and Travis CI only requires Black 20.8 formatting for lines modified in merge
  requests. In a way, Darker is now eating its own dogfood.
- Configure Flake8_ verification for Darker's own source code


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
- Support for Black_ config
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
- Run `isort` first, and only then do the detailed ``git diff`` for Black_


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

.. _Unreleased: https://github.com/akaihola/darker/compare/2.1.0...HEAD
.. _2.1.0: https://github.com/akaihola/darker/compare/2.0.0...2.1.0
.. _2.0.0: https://github.com/akaihola/darker/compare/1.7.3...2.0.0
.. _1.7.3: https://github.com/akaihola/darker/compare/1.7.2...1.7.3
.. _1.7.2: https://github.com/akaihola/darker/compare/1.7.1...1.7.2
.. _1.7.1: https://github.com/akaihola/darker/compare/1.7.0...1.7.1
.. _1.7.0: https://github.com/akaihola/darker/compare/1.6.1...1.7.0
.. _1.6.1: https://github.com/akaihola/darker/compare/1.6.0...1.6.1
.. _1.6.0: https://github.com/akaihola/darker/compare/1.5.1...1.6.0
.. _1.5.1: https://github.com/akaihola/darker/compare/1.5.0...1.5.1
.. _1.5.0: https://github.com/akaihola/darker/compare/1.4.2...1.5.0
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
.. _Black 22.1: https://github.com/psf/black/blob/main/CHANGES.md#2210
.. _Black 24.2.0: https://github.com/psf/black/blob/master/CHANGES.md#2420
.. _Black 24.2.1: https://github.com/psf/black/blob/master/CHANGES.md#2421
.. _Pylint: https://pypi.org/project/pylint
.. _pygments: https://pypi.org/project/Pygments/
.. _Darkgraylib: https://pypi.org/project/darkgraylib/
.. _Flake8: https://flake8.pycqa.org/
.. _Flynt: https://pypi.org/project/flynt/
.. _Graylint: https://pypi.org/project/graylint/
.. _Mypy: https://www.mypy-lang.org/
.. _pydocstyle: http://www.pydocstyle.org/
.. _Ruff: https://astral.sh/ruff
.. _Black: https://black.readthedocs.io/
.. _isort: https://pycqa.github.io/isort/
.. _NixOS: https://nixos.org/
.. _pyupgrade: https://pypi.org/project/pyupgrade/
