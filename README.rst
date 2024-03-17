=================================================
 Darker – reformat and lint modified Python code
=================================================

|build-badge|_ |license-badge|_ |pypi-badge|_ |downloads-badge|_ |black-badge|_ |changelog-badge|_

.. |build-badge| image:: https://github.com/akaihola/darker/actions/workflows/python-package.yml/badge.svg
   :alt: master branch build status
.. _build-badge: https://github.com/akaihola/darker/actions/workflows/python-package.yml?query=branch%3Amaster
.. |license-badge| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :alt: BSD 3 Clause license
.. _license-badge: https://github.com/akaihola/darker/blob/master/LICENSE.rst
.. |pypi-badge| image:: https://img.shields.io/pypi/v/darker
   :alt: Latest release on PyPI
.. _pypi-badge: https://pypi.org/project/darker/
.. |downloads-badge| image:: https://pepy.tech/badge/darker
   :alt: Number of downloads
.. _downloads-badge: https://pepy.tech/project/darker
.. |black-badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :alt: Source code formatted using Black
.. _black-badge: https://github.com/psf/black
.. |changelog-badge| image:: https://img.shields.io/badge/-change%20log-purple
   :alt: Change log
.. _changelog-badge: https://github.com/akaihola/darker/blob/master/CHANGES.rst
.. |next-milestone| image:: https://img.shields.io/github/milestones/progress/akaihola/darker/24?color=red&label=release%202.1.1
   :alt: Next milestone
.. _next-milestone: https://github.com/akaihola/darker/milestone/24


What?
=====

This utility reformats and checks Python source code files.
However, when run in a Git repository, it compares an old revision of the source tree
to a newer revision (or the working tree). It then

- only applies reformatting in regions which have changed in the Git working tree
  between the two revisions, and
- only reports those linting messages which appeared after the modifications to the
  source code files.

The reformatters supported are:

- Black_ for code reformatting
- isort_ for sorting imports
- flynt_ for turning old-style format strings to f-strings

See `Using linters`_ below for the list of supported linters.

To easily run Darker as a Pytest_ plugin, see pytest-darker_.

To integrate Darker with your IDE or with pre-commit_,
see the relevant sections below in this document.

.. _Black: https://github.com/python/black
.. _isort: https://github.com/timothycrosley/isort
.. _flynt: https://github.com/ikamensh/flynt
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

You want to start unifying code style in your project using Black_.
Maybe you also like to standardize on how to order your imports,
or do static type checking or other static analysis for your code.

However, instead of formatting the whole code base in one giant commit,
you'd like to only change formatting when you're touching the code for other reasons.

This can also be useful
when contributing to upstream codebases that are not under your complete control.

Partial formatting is not supported by Black_ itself,
for various good reasons, and so far there hasn't been a plan to implemented it either
(`134`__, `142`__, `245`__, `370`__, `511`__, `830`__).
However, in September 2021 Black developers started to hint towards adding this feature
after all (`1352`__). This might at least simplify Darker's algorithm substantially.

__ https://github.com/psf/black/issues/134
__ https://github.com/psf/black/issues/142
__ https://github.com/psf/black/issues/245
__ https://github.com/psf/black/issues/370
__ https://github.com/psf/black/issues/511
__ https://github.com/psf/black/issues/830
__ https://github.com/psf/black/issues/1352

But for the time being, this is where ``darker`` enters the stage.
This tool is for those who want to do partial formatting right now.

Note that this tool is meant for special situations
when dealing with existing code bases.
You should just use Black_ and isort_ as is when starting a project from scratch.

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

  pip install --upgrade darker~=2.1.0

Or, if you're using Conda_ for package management::

  conda install -c conda-forge darker~=2.1.0 isort
  conda update -c conda-forge darker

..

    **Note:** It is recommended to use the '``~=``' "`compatible release`_" version
    specifier for Darker. See `Guarding against Black compatibility breakage`_ for more
    information.

The ``darker <myfile.py>`` or ``darker <directory>`` command
reads the original file(s),
formats them using Black_,
combines original and formatted regions based on edits,
and writes back over the original file(s).

Alternatively, you can invoke the module directly through the ``python`` executable,
which may be preferable depending on your setup.
Use ``python -m darker`` instead of ``darker`` in that case.

By default, ``darker`` just runs Black_ to reformat the code.
You can enable additional features with command line options:

- ``-i`` / ``--isort``: Reorder imports using isort_. Note that isort_ must be
  run in the same Python environment as the packages to process, as it imports
  your modules to determine whether they are first or third party modules.
- ``-f`` / ``--flynt``: Also convert string formatting to use f-strings using the
  ``flynt`` package
- ``-L <linter>`` / ``--lint <linter>``: Run a supported linter (see `Using linters`_)

*New in version 1.1.0:* The ``-L`` / ``--lint`` option.
*New in version 1.2.2:* Package available in conda-forge_.
*New in version 1.7.0:* The ``-f`` / ``--flynt`` option

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


Customizing ``darker``, Black_, isort_, flynt_ and linter behavior
==================================================================

``darker`` invokes Black_ and isort_ internals directly instead of running their
binaries, so it needs to read and pass configuration options to them explicitly.
Project-specific default options for ``darker`` itself, Black_ and isort_ are read from
the project's ``pyproject.toml`` file in the repository root. isort_ does also look for
a few other places for configuration.

Mypy_, Pylint_, Flake8_ and other compatible linters are invoked as
subprocesses by ``darker``, so normal configuration mechanisms apply for each of those
tools. Linters can also be configured on the command line, for example::

    darker -L "mypy --strict" .
    darker --lint "pylint --errors-only" .
  
flynt_ (option ``-f`` / ``--flynt``) is also invoked as a subprocess, but passing
command line options to it is currently not supported. Configuration files need to be
used instead.

Darker does honor exclusion options in Black configuration files when recursing
directories, but the exclusions are only applied to Black reformatting. Isort and
linters are still run on excluded files. Also, individual files explicitly listed on the
command line are still reformatted even if they match exclusion patterns.

For more details, see:

- `Black documentation about pyproject.toml`_
- `isort documentation about config files`_
- `public GitHub repositories which install and run Darker`_
- `flynt documentation about configuration files`_

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
       that other tools like ``flynt``, ``mypy``, ``pylint`` or ``flake8`` won't use
       this configuration file.
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
-L CMD, --lint CMD
       Run a linter on changed files. ``CMD`` can be a name or path of the linter
       binary, or a full quoted command line with the command and options. Linters read
       their configuration as normally, and aren't affected by ``-c`` / ``--config``.
       Linter output is syntax highlighted when the ``pygments`` package is available if
       run on a terminal and or enabled by explicitly (see ``--color``).
-S, --skip-string-normalization
       Don't normalize string quotes or prefixes
--no-skip-string-normalization
       Normalize string quotes or prefixes. This can be used to override
       ``skip_string_normalization = true`` from a configuration file.
--skip-magic-trailing-comma
       Skip adding trailing commas to expressions that are split by comma where each
       element is on its own line. This includes function signatures. This can be used
       to override ``skip_magic_trailing_comma = true`` from a configuration file.
-l LENGTH, --line-length LENGTH
       How many characters per line to allow [default: 88]
-t VERSION, --target-version VERSION
       [py33\|py34\|py35\|py36\|py37\|py38\|py39\|py310\|py311\|py312] Python versions
       that should be supported by Black's output. [default: per-file auto-detection]

To change default values for these options for a given project,
add a ``[tool.darker]`` or ``[tool.black]`` section to ``pyproject.toml`` in the
project's root directory, or to a different TOML file specified using the ``-c`` /
``--config`` option. For example:

.. code-block:: toml

   [tool.darker]
   src = [
       "src/mypackage",
   ]
   revision = "master"
   diff = true
   check = true
   isort = true
   flynt = true
   lint = [
       "pylint",
   ]
   line-length = 80                  # Passed to isort and Black, override their config
   log_level = "INFO"

   [tool.black]
   line-length = 88                  # Overridden by [tool.darker] above
   skip-magic-trailing-comma = false
   skip-string-normalization = false
   target-version = ["py38", "py39", "py310", "py311", "py312"]
   exclude = "test_*\.py"
   extend_exclude = "/generated/"
   force_exclude = ".*\.pyi"

   [tool.isort]
   profile = "black"
   known_third_party = ["pytest"]
   line_length = 88                  # Overridden by [tool.darker] above

While isort_ reads all of its options from the configuration file, Black_ only honors
the ones listed above when called by ``darker``. Other tools are invoked as
subprocesses and use their configuration mechanisms unmodified.

Be careful to not use options which generate output which is unexpected for
other tools. For example, VSCode only expects the reformat diff, so
``lint = [ ... ]`` can't be used with it.

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

.. _Black documentation about pyproject.toml: https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file
.. _isort documentation about config files: https://timothycrosley.github.io/isort/docs/configuration/config_files/
.. _public GitHub repositories which install and run Darker: https://github.com/search?q=%2Fpip+install+.*darker%2F+path%3A%2F%5E.github%5C%2Fworkflows%5C%2F.*%2F&type=code
.. _flynt documentation about configuration files: https://github.com/ikamensh/flynt#configuration-files
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

     $ pip install darker

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
    "python.formatting.blackArgs": [],

VSCode will always add ``--diff --quiet`` as arguments to Darker,
but you can also pass additional arguments in the ``blackArgs`` option
(e.g. ``["--isort", "--revision=master..."]``).
Be sure to *not* enable any linters here or in ``pyproject.toml``
since VSCode won't be able to understand output from them.

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
        rev: v2.1.0
        hooks:
          - id: darker

4. install the Git hook scripts and update to the newest version::

       pre-commit install
       pre-commit autoupdate

When auto-updating, care is being taken to protect you from possible incompatibilities
introduced by Black updates. See `Guarding against Black compatibility breakage`_ for
more information.

If you'd prefer to not update but keep a stable pre-commit setup, you can pin Black and
other reformatter/linter tools you use to known compatible versions, for example:

.. code-block:: yaml

   - repo: https://github.com/akaihola/darker
     rev: v2.1.0
     hooks:
       - id: darker
         args:
           - --isort
           - --lint
           - mypy
           - --lint
           - flake8
           - --lint
           - pylint
         additional_dependencies:
           - black==22.12.0
           - isort==5.11.4
           - mypy==0.990
           - flake8==5.0.4
           - pylint==2.15.5

.. _pre-commit: https://pre-commit.com/
.. _pre-commit Installation: https://pre-commit.com/#installation


Using arguments
---------------

You can provide arguments, such as enabling isort, by specifying ``args``.
Note the inclusion of the isort Python package under ``additional_dependencies``:

.. code-block:: yaml

   - repo: https://github.com/akaihola/darker
     rev: v2.1.0
     hooks:
       - id: darker
         args: [--isort]
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

   name: Lint

   on: [push, pull_request]

   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0 
         - uses: actions/setup-python@v5
         - uses: akaihola/darker@2.1.0
           with:
             options: "--check --diff --isort --color"
             src: "./src"
             version: "~=2.1.0"
             lint: "flake8,pylint==2.13.1"

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

To run linters through Darker, you can provide a comma separated list of linters using
the ``lint:`` option. Only ``flake8``, ``pylint`` and ``mypy`` are supported. Other
linters may or may not work with Darker, depending on their message output format.
Versions can be constrained using ``pip`` syntax, e.g. ``"flake8>=3.9.2"``.

*New in version 1.1.0:*
GitHub Actions integration. Modeled after how Black_ does it,
thanks to Black authors for the example!

*New in version 1.4.1:*
The ``revision:`` option, with smart default value if omitted.

*New in version 1.5.0:*
The ``lint:`` option.


.. _Using linters:

Using linters
=============

One way to use Darker is to filter linter output to only those linter messages
which appeared after the modifications to source code files,
as well as old messages which concern modified lines.
Darker supports any linter with output in one of the following formats::

    <file>:<linenum>: <description>
    <file>:<linenum>:<col>: <description>

Most notably, the following linters/checkers have been verified to work with Darker:

- Mypy_ for static type checking
- Pylint_ for generic static checking of code
- Flake8_ for style guide enforcement
- `cov_to_lint.py`_ for test coverage

*New in version 1.1.0:* Support for Mypy_, Pylint_, Flake8_ and compatible linters.

*New in version 1.2.0:* Support for test coverage output using `cov_to_lint.py`_.

To run a linter, use the ``--lint`` / ``-L`` command line option with the linter
command or a full command line to pass to a linter. Some examples:

- ``-L flake8``: enforce the Python style guide using Flake8_
- ``-L "mypy --strict"``: do static type checking using Mypy_
- ``--lint="pylint --ignore='setup.py'"``: analyze code using Pylint_
- ``-L cov_to_lint.py``: read ``.coverage`` and list non-covered modified lines

**Note:** Full command lines aren't fully tested on Windows. See issue `#456`_ for a
possible bug.

Darker also groups linter output into blocks of consecutive lines
separated by blank lines.
Here's an example of `cov_to_lint.py`_ output::

    $ darker --revision 0.1.0.. --check --lint cov_to_lint.py src
    src/darker/__main__.py:94:  no coverage:             logger.debug("No changes in %s after isort", src)
    src/darker/__main__.py:95:  no coverage:             break

    src/darker/__main__.py:125: no coverage:         except NotEquivalentError:

    src/darker/__main__.py:130: no coverage:             if context_lines == max_context_lines:
    src/darker/__main__.py:131: no coverage:                 raise
    src/darker/__main__.py:132: no coverage:             logger.debug(

+-----------------------------------------------------------------------+
|                               ⚠ NOTE ⚠                                |
+=======================================================================+
| Don't enable linting on the command line or in the configuration when |
| running Darker as a reformatter in VSCode. You will confuse VSCode    |
| with unexpected output from Darker, as it only expect black's output  |
+-----------------------------------------------------------------------+

.. _Mypy: https://pypi.org/project/mypy
.. _Pylint: https://pypi.org/project/pylint
.. _Flake8: https://pypi.org/project/flake8
.. _cov_to_lint.py: https://gist.github.com/akaihola/2511fe7d2f29f219cb995649afd3d8d2
.. _#456: https://github.com/akaihola/darker/issues/456


Syntax highlighting
===================

Darker automatically enables syntax highlighting for the ``--diff``,
``-d``/``--stdout`` and ``-L``/``--lint`` options if it's running on a terminal and the
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


Guarding against Black compatibility breakage
=============================================

Darker accesses some Black internals which don't belong to its public API. Darker is
thus subject to becoming incompatible with future versions of Black.

To protect users against such breakage, we test Darker daily against the `Black main
branch`_ and strive to proactively fix any potential incompatibilities through this
process. If a commit to Black ``main`` branch introduces an incompatibility with
Darker, we will release a first patch version for Darker that prevents upgrading Black
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
- run Black_ on edited and added files
- compare before and after reformat, noting each continuous chunk of reformatted lines
- discard reformatted chunks on which no edited/added line falls on
- keep reformatted chunks on which some edited/added lines fall on

To sort imports when the ``--isort`` option was specified, Darker proceeds like this:

- run isort_ on each edited and added file before applying Black_
- only if any of the edited or added lines falls between the first and last line
  modified by isort_, are those modifications kept
- if all lines between the first and last line modified by isort_ were unchanged between
  the revisions, discard import sorting modifications for that file

For details on how linting support works, see Graylint_ documentation.


Limitations and work-arounds
=============================

Black doesn't support partial formatting natively.
Because of this, Darker lets Black reformat complete files.
Darker then accepts or rejects chunks of contiguous lines touched by Black,
depending on whether any of the lines in a chunk were edited or added
between the two revisions.

Due to the nature of this algorithm,
Darker is often unable to minimize the number of changes made by Black
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Awnoise" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aagandra" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3Akedhammar" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Akedhammar" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/commits?author=aljazerzen" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/search?q=akaihola" title="Answering Questions">💬</a>
         <a href="https://github.com/akaihola/darker/commits?author=akaihola" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/commits?author=akaihola" title="Documentation">📖</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Aakaihola" title="Reviewed Pull Requests">👀</a>
         <a href="https://github.com/akaihola/darker/commits?author=akaihola" title="Maintenance">🚧</a>
       </td>
       <td align="center">
         <a href="https://github.com/Ashblaze">
           <img src="https://avatars.githubusercontent.com/u/25725925?v=3" width="100px;" alt="@Ashblaze" />
           <br />
           <sub>
             <b>Ashblaze</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3AAshblaze" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/levouh">
           <img src="https://avatars.githubusercontent.com/u/31262046?v=3" width="100px;" alt="@levouh" />
           <br />
           <sub>
             <b>August Masquelier</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Alevouh" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Alevouh" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3AAckslD" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Abaod-rate" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aqubidt" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/falkben">
           <img src="https://avatars.githubusercontent.com/u/653031?v=3" width="100px;" alt="@falkben" />
           <br />
           <sub>
             <b>Ben Falk</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Afalkben" title="Documentation">📖</a>
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3Afalkben" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Abrtknr" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/bdperkin">
           <img src="https://avatars.githubusercontent.com/u/3385145?v=3" width="100px;" alt="@bdperkin" />
           <br />
           <sub>
             <b>Brandon Perkins</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Abdperkin" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Acasio" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/mrfroggg">
           <img src="https://avatars.githubusercontent.com/u/35123233?v=3" width="100px;" alt="@mrfroggg" />
           <br />
           <sub>
             <b>Cedric</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Amrfroggg&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Achmouel" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Achmouel" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Acclauss" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Achrisdecker1201" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Achrisdecker1201" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/KangOl">
           <img src="https://avatars.githubusercontent.com/u/38731?v=3" width="100px;" alt="@KangOl" />
           <br />
           <sub>
             <b>Christophe Simonis</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3AKangOl" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/commits?author=CorreyL" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/commits?author=CorreyL" title="Documentation">📖</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3ACorreyL" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/dkeraudren">
           <img src="https://avatars.githubusercontent.com/u/82873215?v=3" width="100px;" alt="@dkeraudren" />
           <br />
           <sub>
             <b>Damien Keraudren</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Adkeraudren&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Afizbin" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3ADavidCDreher" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Ashangxiao" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ashangxiao" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/dhrvjha">
           <img src="https://avatars.githubusercontent.com/u/43818577?v=3" width="100px;" alt="@dhrvjha" />
           <br />
           <sub>
             <b>Dhruv Kumar Jha</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Adhrvjha&type=issues" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Adhrvjha" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Adshemetov" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/k-dominik">
           <img src="https://avatars.githubusercontent.com/u/24434157?v=3" width="100px;" alt="@k-dominik" />
           <br />
           <sub>
             <b>Dominik Kutra</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Ak-dominik&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Avirtuald" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3ADylanYoung" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aphitoduck" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Eyobkibret15">
           <img src="https://avatars.githubusercontent.com/u/64076953?v=3" width="100px;" alt="@Eyobkibret15" />
           <br />
           <sub>
             <b>Eyob Kibret</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3AEyobkibret15" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/philipgian">
           <img src="https://avatars.githubusercontent.com/u/6884633?v=3" width="100px;" alt="@philipgian" />
           <br />
           <sub>
             <b>Filippos Giannakos</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Aphilipgian" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/search?q=foxwhite25" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Agdiscry" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Agergelypolonkai" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/commits?author=muggenhor" title="Code">💻</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/jabesq">
           <img src="https://avatars.githubusercontent.com/u/12049794?v=3" width="100px;" alt="@jabesq" />
           <br />
           <sub>
             <b>Hugo Dupras</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Ajabesq" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ajabesq" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Ahugovk" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Airynahryshanovich" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Ayajo&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
       <td align="center">
         <a href="https://github.com/jasleen19">
           <img src="https://avatars.githubusercontent.com/u/30443449?v=3" width="100px;" alt="@jasleen19" />
           <br />
           <sub>
             <b>Jasleen Kaur</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ajasleen19" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Ajasleen19" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ajedie" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/jenshnielsen">
           <img src="https://avatars.githubusercontent.com/u/548266?v=3" width="100px;" alt="@jenshnielsen" />
           <br />
           <sub>
             <b>Jens Hedegaard Nielsen</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=jenshnielsen" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Awkentaro" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3AAsuskf" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Krischtopp">
           <img src="https://avatars.githubusercontent.com/u/56152637?v=3" width="100px;" alt="@Krischtopp" />
           <br />
           <sub>
             <b>Krischtopp</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3AKrischtopp" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aleotrs" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Amagnunm" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/markddavidoff">
           <img src="https://avatars.githubusercontent.com/u/1360543?v=3" width="100px;" alt="@markddavidoff" />
           <br />
           <sub>
             <b>Mark Davidoff</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Amarkddavidoff" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Adwt" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Amatclayton" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/Carreau">
           <img src="https://avatars.githubusercontent.com/u/335567?v=3" width="100px;" alt="@Carreau" />
           <br />
           <sub>
             <b>Matthias Bussonnier</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/commits?author=Carreau" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/commits?author=Carreau" title="Documentation">📖</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3ACarreau" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3AMatthijsBurgh" title="Bug reports">🐛</a>
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
         <a href="https://github.com/conda-forge/darker-feedstock/search?q=darker+author%3Aminrk&type=issues" title="Code">💻</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/my-tien">
           <img src="https://avatars.githubusercontent.com/u/3898364?v=3" width="100px;" alt="@my-tien" />
           <br />
           <sub>
             <b>My-Tien Nguyen</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Amy-tien" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/commits?author=Mystic-Mirage" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/commits?author=Mystic-Mirage" title="Documentation">📖</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3AMystic-Mirage" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Anjhuffman" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/commits?author=njhuffman" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/wasdee">
           <img src="https://avatars.githubusercontent.com/u/8089231?v=3" width="100px;" alt="@wasdee" />
           <br />
           <sub>
             <b>Nutchanon Ninyawee</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Awasdee" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3APacu2" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3APacu2" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3APatrickJordanCongenica" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/ivanov">
           <img src="https://avatars.githubusercontent.com/u/118211?v=3" width="100px;" alt="@ivanov" />
           <br />
           <sub>
             <b>Paul Ivanov</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/commits?author=ivanov" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aivanov" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Aivanov" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Agesslerpd" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aflying-sheep" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/RishiKumarRay">
           <img src="https://avatars.githubusercontent.com/u/87641376?v=3" width="100px;" alt="@RishiKumarRay" />
           <br />
           <sub>
             <b>Rishi Kumar Ray</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=RishiKumarRay" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Aioggstream&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aroniemartinez" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/rossbar">
           <img src="https://avatars.githubusercontent.com/u/1268991?v=3" width="100px;" alt="@rossbar" />
           <br />
           <sub>
             <b>Ross Barnowski</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Arossbar" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Asgaist" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aseweissman" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/sherbie">
           <img src="https://avatars.githubusercontent.com/u/15087653?v=3" width="100px;" alt="@sherbie" />
           <br />
           <sub>
             <b>Sean Hammond</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Asherbie" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ahauntsaninja" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Asimgunz&type=issues" title="Reviewed Pull Requests">👀</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/soxofaan">
           <img src="https://avatars.githubusercontent.com/u/44946?v=3" width="100px;" alt="@soxofaan" />
           <br />
           <sub>
             <b>Stefaan Lippens</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Asoxofaan" title="Documentation">📖</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Astrzonnek" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3ASvenito" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/tkolleh">
           <img src="https://avatars.githubusercontent.com/u/3095197?v=3" width="100px;" alt="@tkolleh" />
           <br />
           <sub>
             <b>TJ Kolleh</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Atkolleh" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/commits?author=talhajunaidd" title="Code">💻</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aguettli" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Timple">
           <img src="https://avatars.githubusercontent.com/u/5036851?v=3" width="100px;" alt="@Timple" />
           <br />
           <sub>
             <b>Tim Clephas</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3ATimple&type=issues" title="Bug reports">🐛</a>
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
       <td align="center">
         <a href="https://github.com/tapted">
           <img src="https://avatars.githubusercontent.com/u/1721312?v=3" width="100px;" alt="@tapted" />
           <br />
           <sub>
             <b>Trent Apted</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Atapted" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Atgross35" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Avictorcui96&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Ayoursvivek" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/commits?author=yoursvivek" title="Documentation">📖</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/Hainguyen1210">
           <img src="https://avatars.githubusercontent.com/u/15359217?v=3" width="100px;" alt="@Hainguyen1210" />
           <br />
           <sub>
             <b>Will</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3AHainguyen1210" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Awjdp" title="Bug reports">🐛</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Awjdp" title="Documentation">📖</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Awpnbos" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Azachnorton4C" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aclintonsteiner" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/deadkex">
           <img src="https://avatars.githubusercontent.com/u/59506422?v=3" width="100px;" alt="@deadkex" />
           <br />
           <sub>
             <b>deadkex</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3Adeadkex" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/dsmanl">
           <img src="https://avatars.githubusercontent.com/u/67360039?v=3" width="100px;" alt="@dsmanl" />
           <br />
           <sub>
             <b>dsmanl</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Adsmanl" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Aleej3&type=issues" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/discussions?discussions_q=author%3Ajsuit" title="Bug reports">🐛</a>
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
         <a href="https://github.com/conda-forge/staged-recipes/search?q=darker&type=issues&author=martinRenou" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3AmartinRenou" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/issues?q=author%3Amayk0gan" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/okuuva">
           <img src="https://avatars.githubusercontent.com/u/2804020?v=3" width="100px;" alt="@okuuva" />
           <br />
           <sub>
             <b>okuuva</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Aokuuva&type=issues" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/overratedpro">
           <img src="https://avatars.githubusercontent.com/u/1379994?v=3" width="100px;" alt="@overratedpro" />
           <br />
           <sub>
             <b>overratedpro</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/issues?q=author%3Aoverratedpro" title="Bug reports">🐛</a>
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
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Asamoylovfp" title="Reviewed Pull Requests">👀</a>
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
         <a href="https://github.com/akaihola/darker/search?q=commenter%3Asimonf-dev&type=issues" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/rogalski">
           <img src="https://avatars.githubusercontent.com/u/9485217?v=3" width="100px;" alt="@rogalski" />
           <br />
           <sub>
             <b>Łukasz Rogalski</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Arogalski" title="Code">💻</a>
         <a href="https://github.com/akaihola/darker/issues?q=author%3Arogalski" title="Bug reports">🐛</a>
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
