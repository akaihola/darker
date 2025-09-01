========================================
 Darker – reformat modified Python code
========================================

|build-badge| |license-badge| |pypi-badge| |downloads-badge| |black-badge| |changelog-badge|

.. |build-badge| image:: https://github.com/akaihola/darker/actions/workflows/python-package.yml/badge.svg
   :alt: master branch build status
   :target: https://github.com/akaihola/darker/actions/workflows/python-package.yml?query=branch%3Amaster
.. |license-badge| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :alt: BSD 3 Clause license
   :target: https://github.com/akaihola/darker/blob/master/LICENSE.rst
.. |pypi-badge| image:: https://img.shields.io/pypi/v/darker
   :alt: Latest release on PyPI
   :target: https://pypi.org/project/darker/
.. |downloads-badge| image:: https://pepy.tech/badge/darker
   :alt: Number of downloads
   :target: https://pepy.tech/project/darker
.. |black-badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :alt: Source code formatted using Black
   :target: https://github.com/psf/black
.. |changelog-badge| image:: https://img.shields.io/badge/-change%20log-purple
   :alt: Change log
   :target: https://github.com/akaihola/darker/blob/master/CHANGES.rst
.. |next-milestone| image:: https://img.shields.io/github/milestones/progress/akaihola/darker/25?color=red&label=release%203.0.1
   :alt: Next milestone
   :target: https://github.com/akaihola/darker/milestone/24


What?
=====

This utility reformats Python source code files.
However, when run in a Git repository, it compares an old revision of the source tree
to a newer revision (or the working tree). It then only applies reformatting
in regions which have changed in the Git working tree between the two revisions.

The reformatters supported are:

- Black_ and `the Ruff formatter`_ for code reformatting
- isort_ for sorting imports
- flynt_ for turning old-style format strings to f-strings
- pyupgrade_ for upgrading syntax for newer versions of Python

**NOTE:** Baseline linting support has been moved to the Graylint_ package.

To easily run Darker as a Pytest_ plugin, see pytest-darker_.

To integrate Darker with your IDE or with pre-commit_,
see the relevant sections below in this document.

.. _Black: https://black.readthedocs.io/
.. _the Ruff formatter: https://docs.astral.sh/ruff/formatter/
.. _isort: https://pycqa.github.io/isort/
.. _flynt: https://github.com/ikamensh/flynt
.. _pyupgrade: https://github.com/asottile/pyupgrade
.. _Pytest: https://docs.pytest.org/
.. _pytest-darker: https://pypi.org/project/pytest-darker/

+------------------------------------------------+--------------------------------+
| |you-can-help|                                 | |support|                      |
+================================================+================================+
| We're asking the community kindly for help to  | We have a                      |
| review pull requests for |next-milestone|_ .   | `community support channel`_   |
| If you have a moment to spare, please take a   | on GitHub Discussions. Welcome |
| look at one of them and shoot us a comment!    | to ask for help and advice!    |
+------------------------------------------------+--------------------------------+

*New in version 1.4.0:* Darker can be used in plain directories, not only Git repositories.

.. |you-can-help| image:: https://img.shields.io/badge/-You%20can%20help-green?style=for-the-badge
   :alt: You can help
.. |support| image:: https://img.shields.io/badge/-Support-green?style=for-the-badge
   :alt: Support
.. _#151: https://github.com/akaihola/darker/issues/151
.. _community support channel: https://github.com/akaihola/darker/discussions


Why?
====

You want to start unifying code style in your project
using Black_ or `the Ruff formatter`_.
Maybe you also like to standardize on how to order your imports,
or convert string formatting to use f-strings.

However, instead of formatting the whole code base in one giant commit,
you'd like to only change formatting when you're touching the code for other reasons.

This can also be useful
when contributing to upstream codebases that are not under your complete control.

Partial formatting was not supported by Black_ itself when Darker was originally
created, which is why Darker was developed to provide this functionality.
However, Black has since added the `-\-line-ranges`_ command line option for partial
formatting, which could potentially simplify Darker's implementation.

.. _-\-line-ranges: https://black.readthedocs.io/en/latest/usage_and_configuration/the_basics.html#line-ranges

The ``--range`` option in `the Ruff formatter`_
allows for partial formatting of a single range as well,
but to make use of it,
Darker would need call `the Ruff formatter`_ once for each modified chunk.

However, Black doesn't help in determining which line ranges to format.
This is where ``darker`` enters the stage.
This tool is for those who want to do partial formatting for modified parts of the code.

Note that this tool is meant for special situations
when dealing with existing code bases.
You should just use Black_ or `the Ruff formatter`_, Flynt_ and isort_ as is
when starting a project from scratch.

You may also want to still consider whether reformatting the whole code base in one
commit would make sense in your particular case. You can ignore a reformatting commit
in ``git blame`` using the `blame.ignoreRevsFile`_ config option or ``--ignore-rev`` on
the command line. For a deeper dive into this topic, see `Avoiding ruining git blame`_
in Black documentation, or the article
`Why does Black insist on reformatting my entire project?`_ from `Łukasz Langa`_
(`@ambv`_, the creator of Black). Here's an excerpt:

    "When you make this single reformatting commit, everything that comes after is
    **semantic changes** so your commit history is clean in the sense that it actually
    shows what changed in terms of meaning, not style. There are tools like darker that
    allow you to only reformat lines that were touched since the last commit. However,
    by doing that you forever expose yourself to commits that are a mix of semantic
    changes with stylistic changes, making it much harder to see what changed."

.. _blame.ignoreRevsFile: https://git-scm.com/docs/git-blame/en#Documentation/git-blame.txt---ignore-revs-fileltfilegt
.. _Avoiding ruining git blame: https://black.readthedocs.io/en/stable/guides/introducing_black_to_your_project.html#avoiding-ruining-git-blame
.. _Why does Black insist on reformatting my entire project?: https://lukasz.langa.pl/36380f86-6d28-4a55-962e-91c2c959db7a/
.. _Łukasz Langa: https://lukasz.langa.pl/
.. _@ambv: https://github.com/ambv

How?
====

To install or upgrade, use::

  pip install --upgrade darker~=3.0.0

To also install support for Black_ formatting::

  pip install --upgrade 'darker[black]~=2.1.1'

To install support for all available formatting and analysis tools::

  pip install --upgrade 'darker[color,black,ruff,isort,flynt,pyupgrade]~=2.1.1'

The available optional dependencies are:

- ``color``: Enable syntax highlighting in terminal output using Pygments_
- ``black``: Enable Black_ code formatting (the default formatter)
- ``ruff``: Enable code formatting using `the Ruff formatter`_
- ``isort``: Enable isort_ import sorting
- ``flynt``: Enable flynt_ string formatting conversion
- ``pyupgrade``: Enable pyupgrade_ code upgrades

Or, if you're using Conda_ for package management::

  conda install -c conda-forge darker~=2.1.1 black isort
  conda update -c conda-forge darker

..

    **Note:** It is recommended to use the '``~=``' "`compatible release`_" version
    specifier for Darker.
    See `Guarding against Black, Flynt and isort compatibility breakage`_
    for more information.

*New in version 3.0.0:* Black is no longer installed by default.

The ``darker <myfile.py>`` or ``darker <directory>`` command
reads the original file(s),
formats them using Black_,
combines original and formatted regions based on edits,
and writes back over the original file(s).

Alternatively, you can invoke the module directly through the ``python`` executable,
which may be preferable depending on your setup.
Use ``python -m darker`` instead of ``darker`` in that case.

By default, ``darker`` uses Black_ to reformat the code.
You can choose different formatters or enable additional features
with command line options:

- ``--formatter=black``: Use Black_ for code formatting (the default)
- ``--formatter=ruff``: Use `the Ruff formatter`_ instead of Black_.
- ``--formatter=pyupgrade``: Use pyupgrade_ to upgrade Python syntax
- ``--formatter=none``: Don't run any formatter, only run other enabled tools
- ``-i`` / ``--isort``: Reorder imports using isort_. Note that isort_ must be
  run in the same Python environment as the packages to process, as it imports
  your modules to determine whether they are first or third party modules.
- ``-f`` / ``--flynt``: Also convert string formatting to use f-strings using the
  ``flynt`` package

If you only want to run isort_ and/or Flynt_ without reformatting code,
use the ``--formatter=none`` option.

*New in version 1.1.0:* The ``-L`` / ``--lint`` option.

*New in version 1.2.2:* Package available in conda-forge_.

*New in version 1.7.0:* The ``-f`` / ``--flynt`` option

*New in version 3.0.0:* Removed the ``-L`` / ``--lint`` functionality and moved it into
the Graylint_ package.

*New in version 3.0.0:* The ``--formatter`` option.

.. _Conda: https://conda.io/
.. _conda-forge: https://conda-forge.org/


Example
=======

This example walks you through a minimal practical use case for Darker.

First, create an empty Git repository:

.. code-block:: shell

   $ mkdir /tmp/test
   $ cd /tmp/test
   $ git init
   Initialized empty Git repository in /tmp/test/.git/

In the root of that directory, create the ill-formatted Python file ``our_file.py``:

.. code-block:: python

   if True: print('hi')
   print()
   if False: print('there')

Commit that file:

.. code-block:: shell

   $ git add our_file.py
   $ git commit -m "Initial commit"
   [master (root-commit) a0c7c32] Initial commit
    1 file changed, 3 insertions(+)
    create mode 100644 our_file.py

Now modify the first line in that file:

.. code-block:: python

   if True: print('CHANGED TEXT')
   print()
   if False: print('there')

You can ask Darker to show the diff for minimal reformatting
which makes edited lines conform to Black rules:

.. code-block:: diff

   $ darker --diff our_file.py
   --- our_file.py
   +++ our_file.py
   @@ -1,3 +1,4 @@
   -if True: print('CHANGED TEXT')
   +if True:
   +    print("CHANGED TEXT")
   print()
   if False: print('there')

Alternatively, Darker can output the full reformatted file
(works only when a single Python file is provided on the command line):

.. code-block:: shell

   $ darker --stdout our_file.py

.. code-block:: python

   if True:
       print("CHANGED TEXT")
   print()
   if False: print('there')

If you omit the ``--diff`` and ``--stdout`` options,
Darker replaces the files listed on the command line
with partially reformatted ones as shown above:

.. code-block:: shell

   $ darker our_file.py

Now the contents of ``our_file.py`` will have changed.
Note that the original ``print()`` and ``if False: ...`` lines have not been reformatted
since they had not been edited!

.. code-block:: python

   if True:
       print("CHANGED TEXT")
   print()
   if False: print('there')

You can also ask Darker to reformat edited lines in all Python files in the repository:

.. code-block:: shell

   $ darker .

Or, if you want to compare to another branch (or, in fact, any commit)
instead of the last commit:

.. code-block:: shell

   $ darker --revision master .


Customizing ``darker``, Black_, `the Ruff formatter`_, isort_, flynt_, and pyupgrade_ behavior
==============================================================================================

``darker`` invokes Black_, isort_, flynt_ and pyupgrade_ internals directly
instead of running their binaries,
so it needs to read and pass configuration options to them explicitly.
Project-specific default options for ``darker`` itself, Black_, isort_ and flynt_
are read from the project's ``pyproject.toml`` file in the repository root.
isort_ does also look for a few other places for configuration.

For pyupgrade_, only ``--target-version`` is converted to ``--py<version>-plus``
and passed to the pyupgrade_ internals. No other options are currently supported.

`The Ruff formatter`_ is invoked as a subprocess,
and it reads its configuration from the usual places,
including the project's ``pyproject.toml`` file.

Options for `the Ruff formatter`_ are read as usual directly by Ruff itself
when Darker invokes it as a subprocess.

Darker does honor exclusion options in Black configuration files when recursing
directories, but the exclusions are only applied to Black reformatting.
Isort is still run on excluded files. Also, individual files explicitly listed on the
command line are still reformatted even if they match exclusion patterns.

For more details, see:

- `Black documentation about pyproject.toml`_
- `Ruff documentation about config files`_
- `isort documentation about config files`_
- `public GitHub repositories which install and run Darker`_
- `flynt documentation about configuration files`_
- `pyupgrade documentation`_

The following `command line arguments`_ can also be used to modify the defaults:

-r REV, --revision REV
       Revisions to compare. The default is ``HEAD..:WORKTREE:`` which compares the
       latest commit to the working tree. Tags, branch names, commit hashes, and other
       expressions like ``HEAD~5`` work here. Also a range like ``main...HEAD`` or
       ``main...`` can be used to compare the best common ancestor. With the magic value
       ``:PRE-COMMIT:``, Darker works in pre-commit compatible mode. Darker expects the
       revision range from the ``PRE_COMMIT_FROM_REF`` and ``PRE_COMMIT_TO_REF``
       environment variables. If those are not found, Darker works against ``HEAD``.
       Also see ``--stdin-filename=`` for the ``:STDIN:`` special value.
--stdin-filename PATH
       The path to the file when passing it through stdin. Useful so Darker can find the
       previous version from Git. Only valid with ``--revision=<rev1>..:STDIN:``
       (``HEAD..:STDIN:`` being the default if ``--stdin-filename`` is enabled).
-c PATH, --config PATH
       Make ``darker``, ``black`` and ``isort`` read configuration from ``PATH``. Note
       that other tools like ``flynt`` won't use this configuration file.
-v, --verbose
       Show steps taken and summarize modifications
-q, --quiet
       Reduce amount of output
--color
       Enable syntax highlighting even for non-terminal output. Overrides the
       environment variable PY_COLORS=0
--no-color
       Disable syntax highlighting even for terminal output. Overrides the environment
       variable PY_COLORS=1
-W WORKERS, --workers WORKERS
       How many parallel workers to allow, or ``0`` for one per core [default: 1]
--diff
       Don't write the files back, just output a diff for each file on stdout. Highlight
       syntax if on a terminal and the ``pygments`` package is available, or if enabled
       by configuration.
-d, --stdout
       Force complete reformatted output to stdout, instead of in-place. Only valid if
       there's just one file to reformat. Highlight syntax if on a terminal and the
       ``pygments`` package is available, or if enabled by configuration.
--check
       Don't write the files back, just return the status. Return code 0 means nothing
       would change. Return code 1 means some files would be reformatted.
-f, --flynt
       Also convert string formatting to use f-strings using the ``flynt`` package
-i, --isort
       Also sort imports using the ``isort`` package
--preview
       In Black, enable potentially disruptive style changes that may be added to Black
       in the future
-L CMD, --lint CMD
       Show information about baseline linting using the Graylint package.
-S, --skip-string-normalization
       Don't normalize string quotes or prefixes
--no-skip-string-normalization
       Normalize string quotes or prefixes. This can be used to override ``skip-string-
       normalization = true`` from a Black configuration file.
--skip-magic-trailing-comma
       Skip adding trailing commas to expressions that are split by comma where each
       element is on its own line. This includes function signatures. This can be used
       to override ``skip-magic-trailing-comma = true`` from a Black configuration file.
-l LENGTH, --line-length LENGTH
       How many characters per line to allow [default: 88]
-t VERSION, --target-version VERSION
       [py33\|py34\|py35\|py36\|py37\|py38\|py39\|py310\|py311\|py312\|py313] Python
       versions that should be supported by Black's output. [default: per-file auto-
       detection]
--formatter FORMATTER
       [black\|none\|pyupgrade\|ruff] Formatter to use for reformatting code. [default:
       black]

To change default values for these options for a given project,
add a ``[tool.darker]`` section to ``pyproject.toml`` in the project's root directory,
or to a different TOML file specified using the ``-c`` / ``--config`` option.

You should configure invoked tools like Black_, `the Ruff formatter`_, isort_ and flynt_
using their own configuration files.

As an exception, the ``line-length`` and ``target-version`` options in ``[tool.darker]``
can be used to override corresponding options for individual tools.

Note that Black_ honors only the options listed in the below example
when called by ``darker``, because ``darker`` reads the Black configuration
and passes it on when invoking Black_ directly through its Python API.

An example ``pyproject.toml`` configuration file:

.. code-block:: toml

   [tool.darker]
   src = [
       "src/mypackage",
   ]
   revision = "master"
   formatter = "black"
   diff = true
   check = true
   isort = true
   flynt = true
   line-length = 80                  # Passed to isort and Black, override their config
   target-version = ["py312"]        # Passed to Black, overriding its config
   log_level = "INFO"

   [tool.black]
   line-length = 88                  # Overridden by [tool.darker] above
   skip-magic-trailing-comma = false
   skip-string-normalization = false
   target-version = ["py39", "py310", "py311", "py312"]  # Overridden above
   exclude = "test_*\.py"
   extend_exclude = "/generated/"
   force_exclude = ".*\.pyi"
   preview = true                    # Only supported in [tool.black]


   [tool.isort]
   profile = "black"
   known_third_party = ["pytest"]
   line_length = 88                  # Overridden by [tool.darker] above

*New in version 1.0.0:*

- The ``-c``, ``-S`` and ``-l`` command line options.
- isort_ is configured with ``-c`` and ``-l``, too.

*New in version 1.1.0:* The command line options

- ``-r`` / ``--revision``
- ``--diff``
- ``--check``
- ``--no-skip-string-normalization``
- ``-L`` / ``--lint``

*New in version 1.2.0:* Support for

- commit ranges in ``-r`` / ``--revision``.
- a ``[tool.darker]`` section in ``pyproject.toml``.

*New in version 1.2.2:* Support for ``-r :PRE-COMMIT:`` / ``--revision=:PRE_COMMIT:``

*New in version 1.3.0:* The ``--skip-magic-trailing-comma`` and ``-d`` / ``--stdout``
command line options

*New in version 1.5.0:* The ``-W`` / ``--workers``, ``--color`` and ``--no-color``
command line options

*New in version 1.7.0:* The ``-t`` / ``--target-version`` command line option

*New in version 1.7.0:* The ``-f`` / ``--flynt`` command line option

*New in version 3.0.0:* In ``[tool.darker]``, remove the the Black options
``skip_string_normalization`` and ``skip_magic_trailing_comma`` (previously deprecated
in version 2.1.1)

*New in version 3.0.0:* Removed the ``-L`` / ``--lint`` functionality and moved it into
the Graylint_ package. Also removed ``lint =``, ``skip_string_normalization =`` and
``skip_magic_trailing_comma =`` from ``[tool.darker]``.

.. _Black documentation about pyproject.toml: https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file
.. _Ruff documentation about config files: https://docs.astral.sh/ruff/formatter/#configuration
.. _isort documentation about config files: https://timothycrosley.github.io/isort/docs/configuration/config_files/
.. _public GitHub repositories which install and run Darker: https://github.com/search?q=%2Fpip+install+.*darker%2F+path%3A%2F%5E.github%5C%2Fworkflows%5C%2F.*%2F&type=code
.. _flynt documentation about configuration files: https://github.com/ikamensh/flynt#configuration-files
.. _pyupgrade documentation: https://github.com/asottile/pyupgrade/blob/main/README.md
.. _command line arguments: https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#command-line-options

Editor integration
==================

Many editors have plugins or recipes for integrating Black_.
You may be able to adapt them to be used with ``darker``.
See `editor integration`__ in the Black_ documentation.

__ https://github.com/psf/black/#editor-integration

PyCharm/IntelliJ IDEA
---------------------

1. Install ``darker``::

     $ pip install 'darker[black]'

2. Locate your ``darker`` installation folder.

   On macOS / Linux / BSD::

     $ which darker
     /usr/local/bin/darker  # possible location

   On Windows::

     $ where darker
     %LocalAppData%\Programs\Python\Python36-32\Scripts\darker.exe  # possible location

3. Open External tools in PyCharm/IntelliJ IDEA

   - On macOS: ``PyCharm -> Preferences -> Tools -> External Tools``
   - On Windows / Linux / BSD: ``File -> Settings -> Tools -> External Tools``

4. Click the ``+`` icon to add a new external tool with the following values:

   - Name: Darker
   - Description: Use Black to auto-format regions changed since the last git commit.
   - Program: <install_location_from_step_2>
   - Arguments: ``"$FilePath$"``

   If you need any extra command line arguments
   like the ones which change Black behavior,
   you can add them to the ``Arguments`` field, e.g.::

       --config /home/myself/black.cfg "$FilePath$"

5. You can now format the currently opened file by selecting ``Tools -> External Tools -> Darker``
   or right clicking on a file and selecting ``External Tools -> Darker``

6. Optionally, set up a keyboard shortcut at
   ``Preferences or Settings -> Keymap -> External Tools -> External Tools - Darker``

7. Optionally, run ``darker`` on every file save:

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

     $ pip install 'darker[black]'

2. Locate your ``darker`` installation folder.

   On macOS / Linux / BSD::

     $ which darker
     /usr/local/bin/darker  # possible location

   On Windows::

     $ where darker
     %LocalAppData%\Programs\Python\Python36-32\Scripts\darker.exe  # possible location

3. Make sure you have the `VSCode black-formatter extension`__ installed.

__ https://github.com/microsoft/vscode-black-formatter

4. Add these configuration options to VSCode
   (``⌘ Command / Ctrl`` + ``⇧ Shift`` + ``P``
   and select ``Open Settings (JSON)``)::

    "python.editor.defaultFormatter": "ms-python.black-formatter",
    "black-formatter.path": "<install_location_from_step_2>",
    "black-formatter.args": ["-d"],

VSCode will always add ``--diff --quiet`` as arguments to Darker,
but you can also pass additional arguments in the ``black-formatter.args`` option
(e.g. ``["-d", "--isort", "--revision=master..."]``).

Note that VSCode first copies the file to reformat into a temporary
``<filename>.py.<hash>.tmp`` file, then calls Black (or Darker in this case) on that
file, and brings the changes in the modified files back into the editor.
Darker is aware of this behavior, and will correctly compare ``.py.<hash>.tmp`` files
to corresponding ``.py`` files from earlier repository revisions.


Vim
---

Unlike Black_ and many other formatters, ``darker`` needs access to the Git history.
Therefore it does not work properly with classical auto reformat plugins.

You can though ask vim to run ``darker`` on file save with the following in your
``.vimrc``:

.. code-block:: vim

   set autoread
   autocmd BufWritePost *.py silent :!darker %

- ``BufWritePost`` to run ``darker`` *once the file has been saved*,
- ``silent`` to not ask for confirmation each time,
- ``:!`` to run an external command,
- ``%`` for current file name.

Vim should automatically reload the file.

Emacs
-----

You can integrate with Emacs using Steve Purcell's `emacs-reformatter`__ library.

Using `use-package`__:

.. code-block:: emacs-lisp

    (use-package reformatter
      :hook ((python-mode . darker-reformat-on-save-mode))
      :config
      (reformatter-define darker-reformat
        :program "darker"
        :stdin nil
        :stdout nil
        :args (list "-q" input-file))


This will automatically reformat the buffer on save.

You have multiple functions available to launch it manually:

- darker-reformat
- darker-reformat-region
- darker-reformat-buffer

__ https://github.com/purcell/emacs-reformatter
__ https://github.com/jwiegley/use-package

Using as a pre-commit hook
==========================

*New in version 1.2.1*

To use Darker locally as a Git pre-commit hook for a Python project,
do the following:

1. Install pre-commit_ in your environment
   (see `pre-commit Installation`_ for details).

2. Create a base pre-commit configuration::

       pre-commit sample-config >.pre-commit-config.yaml

3. Append to the created ``.pre-commit-config.yaml`` the following lines:

   .. code-block:: yaml

      - repo: https://github.com/akaihola/darker
        rev: v3.0.0
        hooks:
          - id: darker

4. install the Git hook scripts and update to the newest version::

       pre-commit install
       pre-commit autoupdate

When auto-updating, care is being taken to protect you from possible incompatibilities
introduced by Black updates.
See `Guarding against Black, Flynt and isort compatibility breakage`_
for more information.

If you'd prefer to not update but keep a stable pre-commit setup, you can pin Black and
other reformatter tools you use to known compatible versions, for example:

.. code-block:: yaml

   - repo: https://github.com/akaihola/darker
     rev: v3.0.0
     hooks:
       - id: darker
         args:
           - --isort
         additional_dependencies:
           - black==22.12.0
           - isort==5.11.4

.. _pre-commit: https://pre-commit.com/
.. _pre-commit Installation: https://pre-commit.com/#installation


Using arguments
---------------

You can provide arguments, such as disabling Darker or enabling isort,
by specifying ``args``.
Note the absence of Black and the inclusion of the isort Python package
under ``additional_dependencies``:

.. code-block:: yaml

   - repo: https://github.com/akaihola/darker
     rev: v3.0.0
     hooks:
       - id: darker
         args:
           - --formatter=none
           - --isort
         additional_dependencies:
           - isort~=5.9


GitHub Actions integration
==========================

You can use Darker within a GitHub Actions workflow
without setting your own Python environment.
Great for enforcing that modifications and additions to your code
match the Black_ code style.

Compatibility
-------------

This action is known to support all GitHub-hosted runner OSes. In addition, only
published versions of Darker are supported (i.e. whatever is available on PyPI).
You can `search workflows in public GitHub repositories`_ to see how Darker is being
used.

.. _search workflows in public GitHub repositories: https://github.com/search?q=%22uses%3A+akaihola%2Fdarker%22+path%3A%2F%5E.github%5C%2Fworkflows%5C%2F.*%2F&type=code

Usage
-----

Create a file named ``.github/workflows/darker.yml`` inside your repository with:

.. code-block:: yaml

   name: Reformat

   on: [push, pull_request]

   jobs:
     reformat:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0 
         - uses: actions/setup-python@v5
         - uses: akaihola/darker@3.0.0
           with:
             options: "--check --diff --isort --color"
             src: "./src"
             version: "~=3.0.0"

There needs to be a working Python environment, set up using ``actions/setup-python``
in the above example. Darker will be installed in an isolated virtualenv to prevent
conflicts with other workflows.

``"uses:"`` specifies which Darker release to get the GitHub Action definition from.
We recommend to pin this to a specific release.
``"version:"`` specifies which version of Darker to run in the GitHub Action.
It defaults to the same version as in ``"uses:"``,
but you can force it to use a different version as well.
Darker versions available from PyPI are supported, as well as commit SHAs or branch
names, prefixed with an ``@`` symbol (e.g. ``version: "@master"``).

The ``revision: "master..."`` (or ``"main..."``) option instructs Darker
to compare the current branch to the branching point from main branch
when determining which source code lines have been changed.
If omitted, the Darker GitHub Action will determine the commit range automatically.

``"src:"`` defines the root directory to run Darker for.
This is typically the source tree, but you can use ``"."`` (the default)
to also reformat Python files like ``"setup.py"`` in the root of the whole repository.

You can also configure other arguments passed to Darker via ``"options:"``.
It defaults to ``"--check --diff --color"``.
You can e.g. add ``"--isort"`` to sort imports, or ``"--verbose"`` for debug logging.

*New in version 1.1.0:*
GitHub Actions integration. Modeled after how Black_ does it,
thanks to Black authors for the example!

*New in version 1.4.1:*
The ``revision:`` option, with smart default value if omitted.

*New in version 1.5.0:*
The ``lint:`` option.

*New in version 3.0.0:*
Removed the ``lint:`` option and moved it into the GitHub action
of the Graylint_ package.

*New in version 3.0.0:*
Black is now explicitly installed when running the action.


Syntax highlighting
===================

Darker automatically enables syntax highlighting for the ``--diff`` and
``-d``/``--stdout`` options if it's running on a terminal and the
Pygments_ package is installed.

You can force enable syntax highlighting on non-terminal output using

- the ``color = true`` option in the ``[tool.darker]`` section of ``pyproject.toml`` of
  your Python project's root directory,
- the ``PY_COLORS=1`` environment variable, and
- the ``--color`` command line option for ``darker``.
  
You can force disable syntax highlighting on terminal output using

- the ``color = false`` option in ``pyproject.toml``,
- the ``PY_COLORS=0`` environment variable, and
- the ``--no-color`` command line option.

In the above lists, latter configuration methods override earlier ones, so the command
line options always take highest precedence.

.. _Pygments: https://pypi.org/project/Pygments/


Guarding against Black, Flynt and isort compatibility breakage
==============================================================

Darker accesses some Black_, Flynt_ and isort_ internals
which don't belong to their public APIs.
Darker is thus subject to becoming incompatible with future versions of those tools.

To protect users against such breakage, we test Darker daily against
the `Black main branch`_, `Flynt master branch`_ and `isort main branch`_,
and strive to proactively fix any potential incompatibilities through this process.
If a commit to those branches introduces an incompatibility with Darker,
we will release a first patch version for Darker
that prevents upgrading the corresponding tool
and a second patch version that fixes the incompatibility. A hypothetical example:

1. Darker 9.0.0; Black 35.12.0
   -> OK
2. Darker 9.0.0; Black ``main`` (after 35.12.0)
   -> ERROR on CI test-future_ workflow
3. Darker 9.0.1 released, with constraint ``Black<=35.12.0``
   -> OK
4. Black 36.1.0 released, but Darker 9.0.1 prevents upgrade; Black 35.12.0
   -> OK
5. Darker 9.0.2 released with a compatibility fix, constraint removed; Black 36.1.0
   -> OK

If a Black release introduces an incompatibility before the second Darker patch version
that fixes it, the first Darker patch version will downgrade Black to the latest
compatible version:

1. Darker 9.0.0; Black 35.12.0
   -> OK
2. Darker 9.0.0; Black 36.1.0
   -> ERROR
3. Darker 9.0.1, constraint ``Black<=35.12.0``; downgrades to Black 35.12.0
   -> OK
4. Darker 9.0.2 released with a compatibility fix, constraint removed; Black 36.1.0
   -> OK

To be completely safe, you can pin both Darker and Black to known good versions, but
this may prevent you from receiving improvements in Black. 

It is recommended to use the '``~=``' "`compatible release`_" version specifier for
Darker to ensure you have the latest version before the next major release that may
cause compatibility issues. 

See issue `#382`_ and PR `#430`_ for more information.

.. _compatible release: https://peps.python.org/pep-0440/#compatible-release
.. _Black main branch: https://github.com/psf/black/commits/main
.. _Flynt master branch: https://github.com/ikamensh/flynt/commits/master
.. _isort main branch: https://github.com/PyCQA/isort/commits/main
.. _test-future: https://github.com/akaihola/darker/blob/master/.github/workflows/test-future.yml
.. _#382: https://github.com/akaihola/darker/issues/382
.. _#430: https://github.com/akaihola/darker/issues/430


How does it work?
=================

To apply Black reformatting and to modernize format strings on changed lines,
Darker does the following:

- take a ``git diff`` of Python files between ``REV1`` and ``REV2`` as specified using
  the ``--revision=REV1..REV2`` option
- record current line numbers of lines edited or added between those revisions
- run flynt_ on edited and added files (if Flynt is enabled by the user)
- run Black_ or `the Ruff formatter`_ on edited and added files
- compare before and after reformat, noting each continuous chunk of reformatted lines
- discard reformatted chunks on which no edited/added line falls on
- keep reformatted chunks on which some edited/added lines fall on

To sort imports when the ``--isort`` option was specified, Darker proceeds like this:

- run isort_ on each edited and added file before applying Black_
- only if any of the edited or added lines falls between the first and last line
  modified by isort_, are those modifications kept
- if all lines between the first and last line modified by isort_ were unchanged between
  the revisions, discard import sorting modifications for that file


Limitations and work-arounds
=============================

Although Black has added support for partial formatting with the `--line-ranges` command
line option, and `the Ruff formatter`_ accepts a single line range for ``--range``,
Darker lets Black or Ruff reformat complete files.
Darker then accepts or rejects chunks of contiguous lines touched by Black or Ruff,
depending on whether any of the lines in a chunk were edited or added
between the two revisions.

Due to the nature of this algorithm,
Darker is often unable to minimize the number of changes made by reformatters
as carefully as a developer could do by hand.
Also, depending on what kind of changes were made to the code,
diff results may lead to Darker applying reformatting in an invalid way.
Fortunately, Darker always checks that the result of reformatting
converts to the same AST as the original code.
If that's not the case, Darker expands the chunk until it finds a valid reformatting.
As a result, a much larger block of code may be reformatted than necessary.

The most reasonable work-around to these limitations
is to review the changes made by Darker before committing them to the repository
and unstaging any changes that are not desired.


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


Interesting code formatting and analysis projects to watch
==========================================================

The following projects are related to Black_ or Darker in some way or another.
Some of them we might want to integrate to be part of a Darker run.

- blacken-docs__ – Run Black_ on Python code blocks in documentation files
- blackdoc__ – Run Black_ on documentation code snippets
- velin__ – Reformat docstrings that follow the numpydoc__ convention
- diff-cov-lint__ – Pylint and coverage reports for git diff only
- xenon__ – Monitor code complexity
- pyupgrade__ – Upgrade syntax for newer versions of the language (see `#51`_)
- yapf_ – Google's Python formatter
- yapf_diff__ – apply yapf_ or other formatters to modified lines only

__ https://github.com/asottile/blacken-docs
__ https://github.com/keewis/blackdoc
__ https://github.com/Carreau/velin
__ https://pypi.org/project/numpydoc
__ https://gitlab.com/sVerentsov/diff-cov-lint
__ https://github.com/rubik/xenon
__ https://github.com/asottile/pyupgrade
__ https://github.com/google/yapf/blob/main/yapf/third_party/yapf_diff/yapf_diff.py
.. _yapf: https://github.com/google/yapf
.. _#51: https://github.com/akaihola/darker/pull/51
.. _Graylint: https://github.com/akaihola/graylint


Contributors ✨
===============

Thanks goes to these wonderful people (`emoji key`_):

.. raw:: html

   <!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section
        This is automatically generated. Please update `contributors.yaml` and
        see `CONTRIBUTING.rst` for how to re-generate this table. -->
   <table>
     <tr>
       <td align="center">
         <a href="https://github.com/wnoise">
           <img src="https://avatars.githubusercontent.com/u/9107?v=3" width="100px;" alt="@wnoise" />
           <br />
           <sub>
             <b>Aaron Denney</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awnoise&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/agandra">
           <img src="https://avatars.githubusercontent.com/u/1072647?v=3" width="100px;" alt="@agandra" />
           <br />
           <sub>
             <b>Aditya Gandra</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aagandra&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/kedhammar">
           <img src="https://avatars.githubusercontent.com/u/89784800?v=3" width="100px;" alt="@kedhammar" />
           <br />
           <sub>
             <b>Alfred Kedhammar</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Akedhammar&type=discussions" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Akedhammar&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/aljazerzen">
           <img src="https://avatars.githubusercontent.com/u/11072061?v=3" width="100px;" alt="@aljazerzen" />
           <br />
           <sub>
             <b>Aljaž Mur Eržen</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aaljazerzen&type=commits" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/akaihola">
           <img src="https://avatars.githubusercontent.com/u/13725?v=3" width="100px;" alt="@akaihola" />
           <br />
           <sub>
             <b>Antti Kaihola</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+akaihola" title="Answering Questions">💬</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aakaihola&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aakaihola&type=commits" title="Documentation">📖</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Aakaihola&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aakaihola&type=commits" title="Maintenance">🚧</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aakaihola&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aakaihola&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aakaihola&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aakaihola&type=issues" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Aakaihola&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/artel1992">
           <img src="https://avatars.githubusercontent.com/u/25362233?v=3" width="100px;" alt="@artel1992" />
           <br />
           <sub>
             <b>Artem Uk</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aartel1992&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aartel1992&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Ashblaze">
           <img src="https://avatars.githubusercontent.com/u/25725925?v=3" width="100px;" alt="@Ashblaze" />
           <br />
           <sub>
             <b>Ashblaze</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3AAshblaze&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/levouh">
           <img src="https://avatars.githubusercontent.com/u/31262046?v=3" width="100px;" alt="@levouh" />
           <br />
           <sub>
             <b>August Masquelier</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Alevouh&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Alevouh&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/AckslD">
           <img src="https://avatars.githubusercontent.com/u/23341710?v=3" width="100px;" alt="@AckslD" />
           <br />
           <sub>
             <b>Axel Dahlberg</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AAckslD&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AAckslD&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/baod-rate">
           <img src="https://avatars.githubusercontent.com/u/6306455?v=3" width="100px;" alt="@baod-rate" />
           <br />
           <sub>
             <b>Bao</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Abaod-rate&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/baodrate">
           <img src="https://avatars.githubusercontent.com/u/6306455?v=3" width="100px;" alt="@baodrate" />
           <br />
           <sub>
             <b>Bao</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Abaodrate&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Abaodrate&type=issues" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Abaodrate&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/qubidt">
           <img src="https://avatars.githubusercontent.com/u/6306455?v=3" width="100px;" alt="@qubidt" />
           <br />
           <sub>
             <b>Bao</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aqubidt&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/falkben">
           <img src="https://avatars.githubusercontent.com/u/653031?v=3" width="100px;" alt="@falkben" />
           <br />
           <sub>
             <b>Ben Falk</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Afalkben&type=pullrequests" title="Documentation">📖</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Afalkben&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/brtkwr">
           <img src="https://avatars.githubusercontent.com/u/2181426?v=3" width="100px;" alt="@brtkwr" />
           <br />
           <sub>
             <b>Bharat</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Abrtkwr&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/brtknr">
           <img src="https://avatars.githubusercontent.com/u/2181426?v=3" width="100px;" alt="@brtknr" />
           <br />
           <sub>
             <b>Bharat Kunwar</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Abrtknr&type=pullrequests" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/bdperkin">
           <img src="https://avatars.githubusercontent.com/u/3385145?v=3" width="100px;" alt="@bdperkin" />
           <br />
           <sub>
             <b>Brandon Perkins</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Abdperkin&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/brettcannon">
           <img src="https://avatars.githubusercontent.com/u/54418?v=3" width="100px;" alt="@brettcannon" />
           <br />
           <sub>
             <b>Brett Cannon</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Abrettcannon&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/casio">
           <img src="https://avatars.githubusercontent.com/u/29784?v=3" width="100px;" alt="@casio" />
           <br />
           <sub>
             <b>Carsten Kraus</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Acasio&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/mrfroggg">
           <img src="https://avatars.githubusercontent.com/u/35123233?v=3" width="100px;" alt="@mrfroggg" />
           <br />
           <sub>
             <b>Cedric</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Amrfroggg&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/chmouel">
           <img src="https://avatars.githubusercontent.com/u/98980?v=3" width="100px;" alt="@chmouel" />
           <br />
           <sub>
             <b>Chmouel Boudjnah</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Achmouel&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Achmouel&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/cclauss">
           <img src="https://avatars.githubusercontent.com/u/3709715?v=3" width="100px;" alt="@cclauss" />
           <br />
           <sub>
             <b>Christian Clauss</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Acclauss&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/chrisdecker1201">
           <img src="https://avatars.githubusercontent.com/u/20707614?v=3" width="100px;" alt="@chrisdecker1201" />
           <br />
           <sub>
             <b>Christian Decker</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Achrisdecker1201&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Achrisdecker1201&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/KangOl">
           <img src="https://avatars.githubusercontent.com/u/38731?v=3" width="100px;" alt="@KangOl" />
           <br />
           <sub>
             <b>Christophe Simonis</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AKangOl&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/CorreyL">
           <img src="https://avatars.githubusercontent.com/u/16601729?v=3" width="100px;" alt="@CorreyL" />
           <br />
           <sub>
             <b>Correy Lim</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACorreyL&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACorreyL&type=commits" title="Documentation">📖</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3ACorreyL&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ACorreyL&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/dkeraudren">
           <img src="https://avatars.githubusercontent.com/u/82873215?v=3" width="100px;" alt="@dkeraudren" />
           <br />
           <sub>
             <b>Damien Keraudren</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Adkeraudren&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/fizbin">
           <img src="https://avatars.githubusercontent.com/u/4110350?v=3" width="100px;" alt="@fizbin" />
           <br />
           <sub>
             <b>Daniel Martin</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Afizbin&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/DavidCDreher">
           <img src="https://avatars.githubusercontent.com/u/47252106?v=3" width="100px;" alt="@DavidCDreher" />
           <br />
           <sub>
             <b>David Dreher</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ADavidCDreher&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/shangxiao">
           <img src="https://avatars.githubusercontent.com/u/1845938?v=3" width="100px;" alt="@shangxiao" />
           <br />
           <sub>
             <b>David Sanders</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ashangxiao&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ashangxiao&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/dhrvjha">
           <img src="https://avatars.githubusercontent.com/u/43818577?v=3" width="100px;" alt="@dhrvjha" />
           <br />
           <sub>
             <b>Dhruv Kumar Jha</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Adhrvjha&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Adhrvjha&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/dshemetov">
           <img src="https://avatars.githubusercontent.com/u/1810426?v=3" width="100px;" alt="@dshemetov" />
           <br />
           <sub>
             <b>Dmitry Shemetov</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Adshemetov&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Adshemetov&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/k-dominik">
           <img src="https://avatars.githubusercontent.com/u/24434157?v=3" width="100px;" alt="@k-dominik" />
           <br />
           <sub>
             <b>Dominik Kutra</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ak-dominik&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Ak-dominik&type=discussions" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ak-dominik&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/virtuald">
           <img src="https://avatars.githubusercontent.com/u/567900?v=3" width="100px;" alt="@virtuald" />
           <br />
           <sub>
             <b>Dustin Spicuzza</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Avirtuald&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/DylanYoung">
           <img src="https://avatars.githubusercontent.com/u/5795220?v=3" width="100px;" alt="@DylanYoung" />
           <br />
           <sub>
             <b>DylanYoung</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ADylanYoung&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ADylanYoung&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/phitoduck">
           <img src="https://avatars.githubusercontent.com/u/32227767?v=3" width="100px;" alt="@phitoduck" />
           <br />
           <sub>
             <b>Eric Riddoch</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aphitoduck&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Eyobkibret15">
           <img src="https://avatars.githubusercontent.com/u/64076953?v=3" width="100px;" alt="@Eyobkibret15" />
           <br />
           <sub>
             <b>Eyob Kibret</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3AEyobkibret15&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/felixvd">
           <img src="https://avatars.githubusercontent.com/u/4535737?v=3" width="100px;" alt="@felixvd" />
           <br />
           <sub>
             <b>Felix von Drigalski</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Afelixvd&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Afelixvd&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Afelixvd&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Afelixvd&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/philipgian">
           <img src="https://avatars.githubusercontent.com/u/6884633?v=3" width="100px;" alt="@philipgian" />
           <br />
           <sub>
             <b>Filippos Giannakos</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aphilipgian&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/foxwhite25">
           <img src="https://avatars.githubusercontent.com/u/39846845?v=3" width="100px;" alt="@foxwhite25" />
           <br />
           <sub>
             <b>Fox_white</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+foxwhite25" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Garfounkel">
           <img src="https://avatars.githubusercontent.com/u/10576004?v=3" width="100px;" alt="@Garfounkel" />
           <br />
           <sub>
             <b>Garfounkel</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AGarfounkel&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/gdiscry">
           <img src="https://avatars.githubusercontent.com/u/476823?v=3" width="100px;" alt="@gdiscry" />
           <br />
           <sub>
             <b>Georges Discry</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Agdiscry&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/gergelypolonkai">
           <img src="https://avatars.githubusercontent.com/u/264485?v=3" width="100px;" alt="@gergelypolonkai" />
           <br />
           <sub>
             <b>Gergely Polonkai</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Agergelypolonkai&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/muggenhor">
           <img src="https://avatars.githubusercontent.com/u/484066?v=3" width="100px;" alt="@muggenhor" />
           <br />
           <sub>
             <b>Giel van Schijndel</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amuggenhor&type=commits" title="Code">💻</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/haohu321">
           <img src="https://avatars.githubusercontent.com/u/25491828?v=3" width="100px;" alt="@haohu321" />
           <br />
           <sub>
             <b>Hao Hu</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ahaohu321&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ahaohu321&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/jabesq">
           <img src="https://avatars.githubusercontent.com/u/12049794?v=3" width="100px;" alt="@jabesq" />
           <br />
           <sub>
             <b>Hugo Dupras</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajabesq&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajabesq&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/hugovk">
           <img src="https://avatars.githubusercontent.com/u/1324225?v=3" width="100px;" alt="@hugovk" />
           <br />
           <sub>
             <b>Hugo van Kemenade</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ahugovk&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ahugovk&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ahugovk&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ahugovk&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/irynahryshanovich">
           <img src="https://avatars.githubusercontent.com/u/62266480?v=3" width="100px;" alt="@irynahryshanovich" />
           <br />
           <sub>
             <b>Iryna</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Airynahryshanovich&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/yajo">
           <img src="https://avatars.githubusercontent.com/u/973709?v=3" width="100px;" alt="@yajo" />
           <br />
           <sub>
             <b>Jairo Llopis</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ayajo&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/DeinAlptraum">
           <img src="https://avatars.githubusercontent.com/u/51118500?v=3" width="100px;" alt="@DeinAlptraum" />
           <br />
           <sub>
             <b>Jannick Kremer</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ADeinAlptraum&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3ADeinAlptraum&type=discussions" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/jasleen19">
           <img src="https://avatars.githubusercontent.com/u/30443449?v=3" width="100px;" alt="@jasleen19" />
           <br />
           <sub>
             <b>Jasleen Kaur</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajasleen19&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Ajasleen19&type=pullrequests" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/jedie">
           <img src="https://avatars.githubusercontent.com/u/71315?v=3" width="100px;" alt="@jedie" />
           <br />
           <sub>
             <b>Jens Diemer</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajedie&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ajedie&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajedie&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/jenshnielsen">
           <img src="https://avatars.githubusercontent.com/u/548266?v=3" width="100px;" alt="@jenshnielsen" />
           <br />
           <sub>
             <b>Jens Hedegaard Nielsen</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+jenshnielsen" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/jvacek">
           <img src="https://avatars.githubusercontent.com/u/1302278?v=3" width="100px;" alt="@jvacek" />
           <br />
           <sub>
             <b>Jonas Vacek</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+jvacek" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ajvacek&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ajvacek&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/wkentaro">
           <img src="https://avatars.githubusercontent.com/u/4310419?v=3" width="100px;" alt="@wkentaro" />
           <br />
           <sub>
             <b>Kentaro Wada</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awkentaro&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awkentaro&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/Asuskf">
           <img src="https://avatars.githubusercontent.com/u/36687747?v=3" width="100px;" alt="@Asuskf" />
           <br />
           <sub>
             <b>Kevin David</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3AAsuskf&type=discussions" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Krischtopp">
           <img src="https://avatars.githubusercontent.com/u/56152637?v=3" width="100px;" alt="@Krischtopp" />
           <br />
           <sub>
             <b>Krischtopp</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AKrischtopp&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/leotrs">
           <img src="https://avatars.githubusercontent.com/u/1096704?v=3" width="100px;" alt="@leotrs" />
           <br />
           <sub>
             <b>Leo Torres</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aleotrs&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/magnunm">
           <img src="https://avatars.githubusercontent.com/u/45951302?v=3" width="100px;" alt="@magnunm" />
           <br />
           <sub>
             <b>Magnus N. Malmquist</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amagnunm&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/markddavidoff">
           <img src="https://avatars.githubusercontent.com/u/1360543?v=3" width="100px;" alt="@markddavidoff" />
           <br />
           <sub>
             <b>Mark Davidoff</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amarkddavidoff&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/dwt">
           <img src="https://avatars.githubusercontent.com/u/57199?v=3" width="100px;" alt="@dwt" />
           <br />
           <sub>
             <b>Martin Häcker</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Adwt&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/matclayton">
           <img src="https://avatars.githubusercontent.com/u/126218?v=3" width="100px;" alt="@matclayton" />
           <br />
           <sub>
             <b>Mat Clayton</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amatclayton&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Carreau">
           <img src="https://avatars.githubusercontent.com/u/335567?v=3" width="100px;" alt="@Carreau" />
           <br />
           <sub>
             <b>Matthias Bussonnier</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACarreau&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACarreau&type=commits" title="Documentation">📖</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3ACarreau&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACarreau&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ACarreau&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ACarreau&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ACarreau&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/MatthijsBurgh">
           <img src="https://avatars.githubusercontent.com/u/18014833?v=3" width="100px;" alt="@MatthijsBurgh" />
           <br />
           <sub>
             <b>Matthijs van der Burgh</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AMatthijsBurgh&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AMatthijsBurgh&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AMatthijsBurgh&type=issues" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AMatthijsBurgh&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/minrk">
           <img src="https://avatars.githubusercontent.com/u/151929?v=3" width="100px;" alt="@minrk" />
           <br />
           <sub>
             <b>Min RK</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aconda-forge%2Fdarker-feedstock+involves%3Aminrk&type=issues" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/my-tien">
           <img src="https://avatars.githubusercontent.com/u/3898364?v=3" width="100px;" alt="@my-tien" />
           <br />
           <sub>
             <b>My-Tien Nguyen</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amy-tien&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Mystic-Mirage">
           <img src="https://avatars.githubusercontent.com/u/1079805?v=3" width="100px;" alt="@Mystic-Mirage" />
           <br />
           <sub>
             <b>Mystic-Mirage</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AMystic-Mirage&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AMystic-Mirage&type=commits" title="Documentation">📖</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3AMystic-Mirage&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AMystic-Mirage&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/njhuffman">
           <img src="https://avatars.githubusercontent.com/u/66969728?v=3" width="100px;" alt="@njhuffman" />
           <br />
           <sub>
             <b>Nathan Huffman</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Anjhuffman&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Anjhuffman&type=commits" title="Code">💻</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/wasdee">
           <img src="https://avatars.githubusercontent.com/u/8089231?v=3" width="100px;" alt="@wasdee" />
           <br />
           <sub>
             <b>Nutchanon Ninyawee</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awasdee&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Awasdee&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Pacu2">
           <img src="https://avatars.githubusercontent.com/u/21290461?v=3" width="100px;" alt="@Pacu2" />
           <br />
           <sub>
             <b>Pacu2</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3APacu2&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3APacu2&type=pullrequests" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/PatrickJordanCongenica">
           <img src="https://avatars.githubusercontent.com/u/85236670?v=3" width="100px;" alt="@PatrickJordanCongenica" />
           <br />
           <sub>
             <b>Patrick Jordan</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3APatrickJordanCongenica&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/ivanov">
           <img src="https://avatars.githubusercontent.com/u/118211?v=3" width="100px;" alt="@ivanov" />
           <br />
           <sub>
             <b>Paul Ivanov</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aivanov&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aivanov&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Aivanov&type=pullrequests" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/gesslerpd">
           <img src="https://avatars.githubusercontent.com/u/11217948?v=3" width="100px;" alt="@gesslerpd" />
           <br />
           <sub>
             <b>Peter Gessler</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Agesslerpd&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Agesslerpd&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/flying-sheep">
           <img src="https://avatars.githubusercontent.com/u/291575?v=3" width="100px;" alt="@flying-sheep" />
           <br />
           <sub>
             <b>Philipp A.</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aflying-sheep&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/RishiKumarRay">
           <img src="https://avatars.githubusercontent.com/u/87641376?v=3" width="100px;" alt="@RishiKumarRay" />
           <br />
           <sub>
             <b>Rishi Kumar Ray</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+RishiKumarRay" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/ioggstream">
           <img src="https://avatars.githubusercontent.com/u/1140844?v=3" width="100px;" alt="@ioggstream" />
           <br />
           <sub>
             <b>Roberto Polli</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aioggstream&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/roniemartinez">
           <img src="https://avatars.githubusercontent.com/u/2573537?v=3" width="100px;" alt="@roniemartinez" />
           <br />
           <sub>
             <b>Ronie Martinez</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aroniemartinez&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/rossbar">
           <img src="https://avatars.githubusercontent.com/u/1268991?v=3" width="100px;" alt="@rossbar" />
           <br />
           <sub>
             <b>Ross Barnowski</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Arossbar&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/sgaist">
           <img src="https://avatars.githubusercontent.com/u/898010?v=3" width="100px;" alt="@sgaist" />
           <br />
           <sub>
             <b>Samuel Gaist</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Asgaist&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Asgaist&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/seweissman">
           <img src="https://avatars.githubusercontent.com/u/3342741?v=3" width="100px;" alt="@seweissman" />
           <br />
           <sub>
             <b>Sarah</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aseweissman&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aseweissman&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/sherbie">
           <img src="https://avatars.githubusercontent.com/u/15087653?v=3" width="100px;" alt="@sherbie" />
           <br />
           <sub>
             <b>Sean Hammond</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Asherbie&type=pullrequests" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/hauntsaninja">
           <img src="https://avatars.githubusercontent.com/u/12621235?v=3" width="100px;" alt="@hauntsaninja" />
           <br />
           <sub>
             <b>Shantanu</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ahauntsaninja&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/simgunz">
           <img src="https://avatars.githubusercontent.com/u/466270?v=3" width="100px;" alt="@simgunz" />
           <br />
           <sub>
             <b>Simone Gaiarin</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Asimgunz&type=issues" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Asimgunz&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/soxofaan">
           <img src="https://avatars.githubusercontent.com/u/44946?v=3" width="100px;" alt="@soxofaan" />
           <br />
           <sub>
             <b>Stefaan Lippens</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Asoxofaan&type=pullrequests" title="Documentation">📖</a>
       </td>
       <td align="center">
         <a href="https://github.com/strzonnek">
           <img src="https://avatars.githubusercontent.com/u/80001458?v=3" width="100px;" alt="@strzonnek" />
           <br />
           <sub>
             <b>Stephan Trzonnek</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Astrzonnek&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Svenito">
           <img src="https://avatars.githubusercontent.com/u/31278?v=3" width="100px;" alt="@Svenito" />
           <br />
           <sub>
             <b>Sven Steinbauer</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ASvenito&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3ASvenito&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ASvenito&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ASvenito&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/tkolleh">
           <img src="https://avatars.githubusercontent.com/u/3095197?v=3" width="100px;" alt="@tkolleh" />
           <br />
           <sub>
             <b>TJ Kolleh</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atkolleh&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/talhajunaidd">
           <img src="https://avatars.githubusercontent.com/u/6547611?v=3" width="100px;" alt="@talhajunaidd" />
           <br />
           <sub>
             <b>Talha Juanid</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atalhajunaidd&type=commits" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Atalhajunaidd&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Atalhajunaidd&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/guettli">
           <img src="https://avatars.githubusercontent.com/u/414336?v=3" width="100px;" alt="@guettli" />
           <br />
           <sub>
             <b>Thomas Güttler</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aguettli&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aguettli&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/tehunter">
           <img src="https://avatars.githubusercontent.com/u/7980666?v=3" width="100px;" alt="@tehunter" />
           <br />
           <sub>
             <b>Thomas H</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atehunter&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atehunter&type=pullrequests" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/Timple">
           <img src="https://avatars.githubusercontent.com/u/5036851?v=3" width="100px;" alt="@Timple" />
           <br />
           <sub>
             <b>Tim Clephas</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ATimple&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3ATimple&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/tobiasdiez">
           <img src="https://avatars.githubusercontent.com/u/5037600?v=3" width="100px;" alt="@tobiasdiez" />
           <br />
           <sub>
             <b>Tobias Diez</b>
           </sub>
         </a>
         <br />
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/tapted">
           <img src="https://avatars.githubusercontent.com/u/1721312?v=3" width="100px;" alt="@tapted" />
           <br />
           <sub>
             <b>Trent Apted</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atapted&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/tgross35">
           <img src="https://avatars.githubusercontent.com/u/13724985?v=3" width="100px;" alt="@tgross35" />
           <br />
           <sub>
             <b>Trevor Gross</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Atgross35&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/victorcui96">
           <img src="https://avatars.githubusercontent.com/u/14048976?v=3" width="100px;" alt="@victorcui96" />
           <br />
           <sub>
             <b>Victor Cui</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Avictorcui96&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/yoursvivek">
           <img src="https://avatars.githubusercontent.com/u/163296?v=3" width="100px;" alt="@yoursvivek" />
           <br />
           <sub>
             <b>Vivek Kushwaha</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ayoursvivek&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ayoursvivek&type=commits" title="Documentation">📖</a>
       </td>
       <td align="center">
         <a href="https://github.com/Hainguyen1210">
           <img src="https://avatars.githubusercontent.com/u/15359217?v=3" width="100px;" alt="@Hainguyen1210" />
           <br />
           <sub>
             <b>Will</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3AHainguyen1210&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/wjdp">
           <img src="https://avatars.githubusercontent.com/u/1690934?v=3" width="100px;" alt="@wjdp" />
           <br />
           <sub>
             <b>Will Pimblett</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awjdp&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awjdp&type=pullrequests" title="Documentation">📖</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Will-Ruddick">
           <img src="https://avatars.githubusercontent.com/u/65230899?v=3" width="100px;" alt="@Will-Ruddick" />
           <br />
           <sub>
             <b>Will-Ruddick</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AWill-Ruddick&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/wpnbos">
           <img src="https://avatars.githubusercontent.com/u/33165624?v=3" width="100px;" alt="@wpnbos" />
           <br />
           <sub>
             <b>William Bos</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Awpnbos&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/anakinxc">
           <img src="https://avatars.githubusercontent.com/u/103552181?v=3" width="100px;" alt="@anakinxc" />
           <br />
           <sub>
             <b>Yancheng Zheng</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aanakinxc&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/zachnorton4C">
           <img src="https://avatars.githubusercontent.com/u/49661202?v=3" width="100px;" alt="@zachnorton4C" />
           <br />
           <sub>
             <b>Zach Norton</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Azachnorton4C&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/zmeir">
           <img src="https://avatars.githubusercontent.com/u/33152084?v=3" width="100px;" alt="@zmeir" />
           <br />
           <sub>
             <b>Zohar Meir</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Azmeir&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Azmeir&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Azmeir&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/clintonsteiner">
           <img src="https://avatars.githubusercontent.com/u/47841949?v=3" width="100px;" alt="@clintonsteiner" />
           <br />
           <sub>
             <b>csteiner</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aclintonsteiner&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aclintonsteiner&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aclintonsteiner&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aclintonsteiner&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/deadkex">
           <img src="https://avatars.githubusercontent.com/u/59506422?v=3" width="100px;" alt="@deadkex" />
           <br />
           <sub>
             <b>deadkex</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Adeadkex&type=discussions" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Adeadkex&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/dsmanl">
           <img src="https://avatars.githubusercontent.com/u/67360039?v=3" width="100px;" alt="@dsmanl" />
           <br />
           <sub>
             <b>dsmanl</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Adsmanl&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/leej3">
           <img src="https://avatars.githubusercontent.com/u/5418152?v=3" width="100px;" alt="@leej3" />
           <br />
           <sub>
             <b>john lee</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aleej3&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/jsuit">
           <img src="https://avatars.githubusercontent.com/u/1467906?v=3" width="100px;" alt="@jsuit" />
           <br />
           <sub>
             <b>jsuit</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+involves%3Ajsuit&type=discussions" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/martinRenou">
           <img src="https://avatars.githubusercontent.com/u/21197331?v=3" width="100px;" alt="@martinRenou" />
           <br />
           <sub>
             <b>martinRenou</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aconda-forge%2Fstaged-recipes+akaihola%2Fdarker+involves%3AmartinRenou&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3AmartinRenou&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AmartinRenou&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3AmartinRenou&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/mayk0gan">
           <img src="https://avatars.githubusercontent.com/u/96263702?v=3" width="100px;" alt="@mayk0gan" />
           <br />
           <sub>
             <b>mayk0gan</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Amayk0gan&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/okuuva">
           <img src="https://avatars.githubusercontent.com/u/2804020?v=3" width="100px;" alt="@okuuva" />
           <br />
           <sub>
             <b>okuuva</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aokuuva&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aokuuva&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aokuuva&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Aokuuva&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/overratedpro">
           <img src="https://avatars.githubusercontent.com/u/1379994?v=3" width="100px;" alt="@overratedpro" />
           <br />
           <sub>
             <b>overratedpro</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aoverratedpro&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/ranelpadon">
           <img src="https://avatars.githubusercontent.com/u/4292088?v=3" width="100px;" alt="@ranelpadon" />
           <br />
           <sub>
             <b>ranelpadon</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Aranelpadon&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/samoylovfp">
           <img src="https://avatars.githubusercontent.com/u/17025459?v=3" width="100px;" alt="@samoylovfp" />
           <br />
           <sub>
             <b>samoylovfp</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+reviewed-by%3Asamoylovfp&type=pullrequests" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Asamoylovfp&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/simonf-dev">
           <img src="https://avatars.githubusercontent.com/u/52134089?v=3" width="100px;" alt="@simonf-dev" />
           <br />
           <sub>
             <b>sfoucek</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Asimonf-dev&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Asimonf-dev&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/shane-kearns">
           <img src="https://avatars.githubusercontent.com/u/10816132?v=3" width="100px;" alt="@shane-kearns" />
           <br />
           <sub>
             <b>shane-kearns</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Ashane-kearns&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ashane-kearns&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Ashane-kearns&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/rogalski">
           <img src="https://avatars.githubusercontent.com/u/9485217?v=3" width="100px;" alt="@rogalski" />
           <br />
           <sub>
             <b>Łukasz Rogalski</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Arogalski&type=pullrequests" title="Code">💻</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+author%3Arogalski&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/search?q=repo%3Aakaihola%2Fdarker+commenter%3Arogalski&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
   </table>   <!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the all-contributors_ specification.
Contributions of any kind are welcome!

.. _README.rst: https://github.com/akaihola/darker/blob/master/README.rst
.. _emoji key: https://allcontributors.org/docs/en/emoji-key
.. _all-contributors: https://allcontributors.org


GitHub stars trend
==================

|stargazers|_

.. |stargazers| image:: https://starchart.cc/akaihola/darker.svg
.. _stargazers: https://starchart.cc/akaihola/darker
