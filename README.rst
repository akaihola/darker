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
.. |next-milestone| image:: https://img.shields.io/github/milestones/progress/akaihola/darker/10?color=red&label=release%201.3.2
   :alt: Next milestone
.. _next-milestone: https://github.com/akaihola/darker/milestone/10


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

.. _Black: https://github.com/python/black
.. _isort: https://github.com/timothycrosley/isort
.. _Mypy: https://pypi.org/project/mypy
.. _Pylint: https://pypi.org/project/pylint
.. _Flake8: https://pypi.org/project/flake8

+------------------------------------------------+---------------------------------+
| |you-can-help|                                 | |support|                       |
+================================================+=================================+
| We're asking the community kindly for help to  | We're considering to start a    |
| review pull requests for |next-milestone|_ .   | community support chat channel. |
| If you have a moment to spare, please take a   | Please vote for your preferred  |
| look at one of them and shoot us a comment!    | medium in issue `#151`_!        |
+------------------------------------------------+---------------------------------+

.. |you-can-help| image:: https://img.shields.io/badge/-You%20can%20help-green?style=for-the-badge
   :alt: You can help
.. |support| image:: https://img.shields.io/badge/-Support-green?style=for-the-badge
   :alt: Support
.. _#151: https://github.com/akaihola/darker/issues/151

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

How?
====

To install, use::

  pip install darker

Or, if you're using Conda_ for package management::

  conda install -c conda-forge darker isort

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

- ``-i`` / ``--isort``: Reorder imports using isort_
- ``-L <linter>`` / ``--lint <linter>``: Run a supported linter:

  - ``-L mypy``: do static type checking using Mypy_
  - ``-L pylint``: analyze code using Pylint_
  - ``-L flake8``: enforce the Python style guide using Flake8_

*New in version 1.1.0:* The ``-L`` / ``--lint`` option.
*New in version 1.2.2:* Package available in conda-forge_.

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

.. code-block:: python

   $ darker --stdout our_file.py
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


Customizing ``darker``, Black and isort behavior
================================================

Project-specific default options for ``darker``, Black_ and isort_
are read from the project's ``pyproject.toml`` file in the repository root.
isort_ also looks for a few other places for configuration.

For more details, see:

- `Black documentation about pyproject.toml`_
- `isort documentation about config files`_

The following `command line arguments`_ can also be used to modify the defaults:

-r REV, --revision REV
       Git revision against which to compare the working tree. Tags, branch names,
       commit hashes, and other expressions like ``HEAD~5`` work here. Also a range like
       ``master...HEAD`` or ``master...`` can be used to compare the best common
       ancestor. With the magic value ``:PRE-COMMIT:``, Darker works in pre-commit
       compatible mode. Darker expects the revision range from the
       ``PRE_COMMIT_FROM_REF`` and ``PRE_COMMIT_TO_REF`` environment variables. If those
       are not found, Darker works against ``HEAD``.
--diff
       Don't write the files back, just output a diff for each file on stdout. Highlight
       syntax on screen if the ``pygments`` package is available.
-d, --stdout
       Force complete reformatted output to stdout, instead of in-place. Only valid if
       there's just one file to reformat.
--check
       Don't write the files back, just return the status. Return code 0 means nothing
       would change. Return code 1 means some files would be reformatted.
-i, --isort
       Also sort imports using the ``isort`` package
-L CMD, --lint CMD
       Also run a linter on changed files. ``CMD`` can be a name of path of the linter
       binary, or a full quoted command line
-c PATH, --config PATH
       Ask ``black`` and ``isort`` to read configuration from ``PATH``.
-v, --verbose
       Show steps taken and summarize modifications
-q, --quiet
       Reduce amount of output
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

To change default values for these options for a given project,
add a ``[tool.darker]`` section to ``pyproject.toml`` in the project's root directory.
For example:

.. code-block:: toml

   [tool.darker]
   src = [
       "src/mypackage",
   ]
   revision = "master"
   diff = true
   check = true
   isort = true
   lint = [
       "pylint",
   ]
   log_level = "INFO"

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

*New in version 1.3.0:* Support for command line option ``--skip-magic-trailing-comma``

*New in version 1.3.0:* The ``-d`` / ``--stdout`` command line option

.. _Black documentation about pyproject.toml: https://black.readthedocs.io/en/stable/pyproject_toml.html
.. _isort documentation about config files: https://timothycrosley.github.io/isort/docs/configuration/config_files/
.. _command line arguments: https://black.readthedocs.io/en/stable/installation_and_usage.html#command-line-options

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


Using as a pre-commit hook
==========================

*New in version 1.2.1*

To use Darker locally as a Git pre-commit hook for a Python project,
do the following:

1. Install pre-commit_ in your environment
   (see `pre-commit Installation`_ for details).

1. Create a base pre-commit configuration::

       pre-commit sample-config >.pre-commit-config.yaml

1. Append to the created ``.pre-commit-config.yaml`` the following lines::

       -   repo: https://github.com/akaihola/darker
           rev: 1.3.1
           hooks:
           -   id: darker

2. install the Git hook scripts::

       pre-commit install

.. _pre-commit: https://pre-commit.com/
.. _pre-commit Installation: https://pre-commit.com/#installation


How does it work?
=================

Darker takes a ``git diff`` of your Python files,
records which lines of current files have been edited or added since the last commit.
It then runs Black_ and notes which chunks of lines were reformatted.
Finally, only those reformatted chunks on which edited lines fall (even partially)
are applied to the edited file.

Also, in case the ``--isort`` option was specified,
isort_ is run on each edited file before applying Black_.
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


Contributors ✨
===============

Thanks goes to these wonderful people (`emoji key`_):

.. raw:: html

   <!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
   <table>
       <tr>
           <td align="center">
               <a href="https://github.com/AcksID">
                   <img src="https://avatars.githubusercontent.com/u/23341710?v=3" width="100px;" alt="@AcksID"/>
                   <br />
                   <sub><b>Axel Dahlberg</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3AAcksID"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/akaihola">
                   <img src="https://avatars.githubusercontent.com/u/13725?v=3" width="100px;" alt="@akaihola"/>
                   <br />
                   <sub><b>Antti Kaihola</b></sub>
               </a>
               <br />
               <a href="#question-akaihola" title="Answering Questions">💬</a>
               <a href="https://github.com/akaihola/darker/commits?author=akaihola"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/commits?author=akaihola"
                  title="Documentation">📖</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Aakaihola"
                  title="Reviewed Pull Requests">👀</a>
               <a href="#maintenance-akaihola" title="Maintenance">🚧</a>
           </td>
           <td align="center">
               <a href="https://github.com/Carreau">
                   <img src="https://avatars.githubusercontent.com/u/335567?v=3" width="100px;" alt="@Carreau"/>
                   <br />
                   <sub><b>Matthias Bussonnier</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=Carreau"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/commits?author=Carreau"
                  title="Documentation">📖</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3ACarreau"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td align="center">
               <a href="https://github.com/casio">
                   <img src="https://avatars.githubusercontent.com/u/29784?v=3" width="100px;" alt="@casio"/>
                   <br />
                   <sub><b>Carsten Kraus</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Acasio"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/CircleOnCircles">
                   <img src="https://avatars.githubusercontent.com/u/8089231?v=3" width="100px;" alt="@CircleOnCircles"/>
                   <br />
                   <sub><b>Nutchanon Ninyawee</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3ACircleOnCircles"
                  title="Bug reports">🐛</a>
           </td>
           <td>
               <a href="https://github.com/CorreyL">
                   <img src="https://avatars.githubusercontent.com/u/16601729?v=3" width="100px;" alt="@CorreyL"/>
                   <br />
                   <sub><b>Correy Lim</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=CorreyL"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/commits?author=CorreyL"
                  title="Documentation">📖</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3ACorreyL"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td align="center">
               <a href="https://github.com/dsmanl">
                   <img src="https://avatars.githubusercontent.com/u/67360039?v=3" width="100px;" alt="@dsmanl"/>
                   <br />
                   <sub><b>@dsmanl</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Adsmanl"
                  title="Bug reports">🐛</a>
           </td>
       </tr>
       <tr>
           <td align="center">
               <a href="https://github.com/DylanYoung">
                   <img src="https://avatars.githubusercontent.com/u/5795220?v=3" width="100px;" alt="@DylanYoung"/>
                   <br />
                   <sub><b>@DylanYoung</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3ADylanYoung"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/fizbin">
                   <img src="https://avatars.githubusercontent.com/u/4110350?v=3" width="100px;" alt="@fizbin"/>
                   <br />
                   <sub><b>Daniel Martin</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Afizbin"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/flying-sheep">
                   <img src="https://avatars.githubusercontent.com/u/292575?v=3" width="100px;" alt="@flying-sheep"/>
                   <br />
                   <sub><b>Philipp A.</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Aflying-sheep"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/Hainguyen1210">
                   <img src="https://avatars.githubusercontent.com/u/15359217?v=3" width="100px;" alt="@Hainguyen1210"/>
                   <br />
                   <sub><b>Will</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3AHainguyen1210"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/hauntsaninja">
                   <img src="https://avatars.githubusercontent.com/u/12621235?v=3" width="100px;" alt="@hauntsaninja"/>
                   <br />
                   <sub><b>Shantanu</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Ahauntsaninja"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/irynahryshanovich">
                   <img src="https://avatars.githubusercontent.com/u/62266480?v=3" width="100px;" alt="@irynahryshanovich"/>
                   <br />
                   <sub><b>Iryna</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Airynahryshanovich"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/ivanov">
                   <img src="https://avatars.githubusercontent.com/u/118211?v=3" width="100px;" alt="@ivanov"/>
                   <br />
                   <sub><b>Paul Ivanov</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=ivanov"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/issues?q=author%3Aivanov"
                  title="Bug reports">🐛</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Aivanov"
                  title="Reviewed Pull Requests">👀</a>
           </td>
       </tr>
       <tr>
           <td align="center">
               <a href="https://github.com/jabesq">
                   <img src="https://avatars.githubusercontent.com/u/12049794?v=3" width="100px;" alt="@jabesq"/>
                   <br />
                   <sub><b>Hugo Dupras</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Ajabesq"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/KangOl">
                   <img src="https://avatars.githubusercontent.com/u/38731?v=3" width="100px;" alt="@KangOl"/>
                   <br />
                   <sub><b>Christophe Simonis</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3AKangOl"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/Krischtopp">
                   <img src="https://avatars.githubusercontent.com/u/56152637?v=3" width="100px;" alt="@Krischtopp"/>
                   <br />
                   <sub><b>Krischtopp</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3AKrischtopp"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/leotrs">
                   <img src="https://avatars.githubusercontent.com/u/1096704?v=3" width="100px;" alt="@leotrs"/>
                   <br />
                   <sub><b>Leo Torres</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Aleotrs"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/markddavidoff">
                   <img src="https://avatars.githubusercontent.com/u/1360543?v=3" width="100px;" alt="@markddavidoff"/>
                   <br />
                   <sub><b>Mark Davidoff</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Amarkddavidoff"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/martinRenou">
                   <img src="https://avatars.githubusercontent.com/u/21197331?v=3" width="100px;" alt="@martinRenou"/>
                   <br />
                   <sub><b>Martin Renou</b></sub>
               </a>
               <br />
               <a href="https://github.com/conda-forge/staged-recipes/search?q=darker&type=issues&author=martinRenou"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3AmartinRenou"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td>
               <a href="https://github.com/matclayton">
                   <img src="https://avatars.githubusercontent.com/u/126218?v=3" width="100px;" alt="@matclayton"/>
                   <br />
                   <sub><b>Mat Clayton</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Amatclayton"
                  title="Bug reports">🐛</a>
           </td>
       </tr>
       <tr>
           <td>
               <a href="https://github.com/muggenhor">
                   <img src="https://avatars.githubusercontent.com/u/484066?v=3" width="100px;" alt="@muggenhor"/>
                   <br />
                   <sub><b>Giel van Schijndel</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=muggenhor"
                  title="Code">💻</a>
           </td>
           <td>
               <a href="https://github.com/Mystic-Mirage">
                   <img src="https://avatars.githubusercontent.com/u/1079805?v=3" width="100px;" alt="@Mystic-Mirage"/>
                   <br />
                   <sub><b>Alexander Tishin</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=Mystic-Mirage"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/commits?author=Mystic-Mirage"
                  title="Documentation">📖</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3AMystic-Mirage"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td>
               <a href="https://github.com/overratedpro">
                   <img src="https://avatars.githubusercontent.com/u/1379994?v=3" width="100px;" alt="@overratedpro"/>
                   <br />
                   <sub><b>overratedpro</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Aoverratedpro"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/Pacu2">
                   <img src="https://avatars.githubusercontent.com/u/21290461?v=3" width="100px;" alt="@Pacu2"/>
                   <br />
                   <sub><b>Filip Kucharczyk</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3APacu2"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3APacu2"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td align="center">
               <a href="https://github.com/philipgian">
                   <img src="https://avatars.githubusercontent.com/u/6884633?v=3" width="100px;" alt="@philipgian"/>
                   <br />
                   <sub><b>Filippos Giannakos</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Aphilipgian"
                  title="Code">💻</a>
           </td>
           <td align="center">
               <a href="https://github.com/rogalski">
                   <img src="https://avatars.githubusercontent.com/u/9485217?v=3" width="100px;" alt="@rogalski"/>
                   <br />
                   <sub><b>Łukasz Rogalski</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Arogalski"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/issues?q=author%3Arogalski"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/roniemartinez">
                   <img src="https://avatars.githubusercontent.com/u/2573537?v=3" width="100px;" alt="@roniemartinez"/>
                   <br />
                   <sub><b>Ronie Martinez</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Aroniemartinez"
                  title="Bug reports">🐛</a>
           </td>
       </tr>
       <tr>
           <td align="center">
               <a href="https://github.com/rossbar">
                   <img src="https://avatars.githubusercontent.com/u/1268991?v=3" width="100px;" alt="@rossbar"/>
                   <br />
                   <sub><b>Ross Barnowski</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Arossbar"
                  title="Bug reports">🐛</a>
           </td>
           <td>
               <a href="https://github.com/samoylovfp">
                   <img src="https://avatars.githubusercontent.com/u/17025459?v=3" width="100px;" alt="@samoylovfp"/>
                   <br />
                   <sub><b>samoylovfp</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Asamoylovfp"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td align="center">
               <a href="https://github.com/shangxiao">
                   <img src="https://avatars.githubusercontent.com/u/1845938?v=3" width="100px;" alt="@shangxiao"/>
                   <br />
                   <sub><b>David Sanders</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+author%3Ashangxiao"
                  title="Code">💻</a>
               <a href="https://github.com/akaihola/darker/issues?q=author%3Ashangxiao"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/sherbie">
                   <img src="https://avatars.githubusercontent.com/u/15087653?v=3" width="100px;" alt="@sherbie"/>
                   <br />
                   <sub><b>Sean Hammond</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/pulls?q=is%3Apr+reviewed-by%3Asherbie"
                  title="Reviewed Pull Requests">👀</a>
           </td>
           <td align="center">
               <a href="https://github.com/talhajunaidd">
                   <img src="https://avatars.githubusercontent.com/u/6547611?v=3" width="100px;" alt="@talhajunaidd"/>
                   <br />
                   <sub><b>Talha Juanid</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/commits?author=talhajunaidd"
                  title="Code">💻</a>
           </td>
           <td align="center">
               <a href="https://github.com/tkolleh">
                   <img src="https://avatars.githubusercontent.com/u/3095197?v=3" width="100px;" alt="@tkolleh"/>
                   <br />
                   <sub><b>TJ Kolleh</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Atkolleh"
                  title="Bug reports">🐛</a>
           </td>
           <td align="center">
               <a href="https://github.com/virtuald">
                   <img src="https://avatars.githubusercontent.com/u/567900?v=3" width="100px;" alt="@virtuald"/>
                   <br />
                   <sub><b>Dustin Spicuzza</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Avirtuald"
                  title="Bug reports">🐛</a>
           </td>
       </tr>
       <tr>
           <td align="center">
               <a href="https://github.com/yoursvivek">
                   <img src="https://avatars.githubusercontent.com/u/163296?v=3" width="100px;" alt="@yoursvivek"/>
                   <br />
                   <sub><b>Vivek Kushwaha</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Ayoursvivek"
                  title="Bug reports">🐛</a>
                  <a href="https://github.com/akaihola/darker/commits?author=yoursvivek"
                  title="Documentation">📖</a>
           </td>
           <td align="center">
               <a href="https://github.com/wnoise">
                   <img src="https://avatars.githubusercontent.com/u/9107?v=3" width="100px;" alt="@wnoise"/>
                   <br />
                   <sub><b>Aaron Denney</b></sub>
               </a>
               <br />
               <a href="https://github.com/akaihola/darker/issues?q=author%3Awnoise"
                  title="Bug reports">🐛</a>
           </td>
       </tr>
   </table>
   <!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the all-contributors_ specification.
Contributions of any kind are welcome!

.. _README.rst: https://github.com/akaihola/darker/README.rst
.. _emoji key: https://allcontributors.org/docs/en/emoji-key
.. _all-contributors: https://allcontributors.org


GitHub stars trend
==================

|stargazers|_

.. |stargazers| image:: https://starchart.cc/akaihola/darker.svg
.. _stargazers: https://starchart.cc/akaihola/darker
