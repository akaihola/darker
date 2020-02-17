===========================================================================
 Darker – Apply Black formatting only in regions changed since last commit
===========================================================================


What?
=====

This is a small utility built on top of the black_ Python code formatter
to enable formatting of only regions which have changed since the last Git commit.

.. _black: https://github.com/python/black

Why?
====

Python code should be black, just like outer space.
However, sometimes people insist on staying on the Earth.
Since there's no complete blackness on the Earth,
you eventually settle for just a little darker as a compromise.

In other words, you want to use black_ for the code you write,
but for some reason you don't want to convert the whole files,
e.g. when contributing to upstream codebases that are not under your complete control.

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

Note that this tool is a stopgap measure, and you should avoid using it if you can.

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

5. Format the currently opened file by selecting ``Tools -> External Tools -> Darker``.

   - Alternatively, you can set a keyboard shortcut by navigating to
     ``Preferences or Settings -> Keymap -> External Tools -> External Tools - Darker``

6. Optionally, run ``darker`` on every file save:

   1. Make sure you have the `File Watcher`__ plugin installed.
   2. Go to ``Preferences or Settings -> Tools -> File Watchers`` and click ``+`` to add
      a new watcher:

      - Name: Darner
      - File type: Python
      - Scope: Project Files
      - Program: <install_location_from_step_2>
      - Arguments: ``$FilePath$``
      - Output paths to refresh: ``$FilePath$``
      - Working directory: ``$ProjectFileDir$``

   3. Uncheck "Auto-save edited files to trigger the watcher"

__ https://plugins.jetbrains.com/plugin/7177-file-watchers


License
=======

BSD. See ``LICENSE.rst``.


Prior art
=========

- black-macchiato__
- darken__

__ https://github.com/wbolster/black-macchiato
__ https://github.com/Carreau/darken

