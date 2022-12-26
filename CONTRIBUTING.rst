========================
 Contributing to Darker
========================

This is a micro project with a small code base, few contributors and hobby maintainership.
For this reason, please don't expect immediate responses to bug reports and pull requests.
They will all be responded to eventually.

We follow common conventions and code of conduct for Open Source collaboration on GitHub.

Some additional simple guidelines:

Bug reports
===========

Please include

- release or Git commit for the version of Darker you're using
- Python, black and isort versions
- your command line
- file to be formatted as an attachment, if possible – also great if squeezed down to a minimal example
- resulting output or error message
- expected output

Pull requests
=============

To speed up review and increase odds for the PR to be accepted, please

- keep all code black & isort formatted
- include a test case for new or modified code
- use type hinting
- make sure the test suite passes
- verify that mypy static type checking passes
- document new features or changed behavior in ``README.rst``
- summarize end-user affecting changes in ``CHANGES.rst``
- add your information in ``CONTRIBUTORS.rst``

GitHub is configured to use Travis CI on each pull request to

- run the test suite using Pytest
- do static type checking using Mypy
- check code formatting using Black

Setting up a development environment
====================================

To set up an isolated virtualenv for Darker development, run the test suite and lint
the code base on a Unix-like system::

    git clone git@github.com:akaihola/darker.git
    python -m venv .venv-darker
    source .venv-darker/bin/activate
    cd darker
    pip install -e '.[test]' mypy pylint flake8
    pytest
    pylint src
    mypy .
    flake8 src

Before pushing your commits to a feature branch, it's good to run::

    darker --isort -L mypy -L pylint -L flake8 -r master... .

This will fix formatting on modified lines and list any linting errors your changes may
have introduced compared to the branching point of your feature branch from ``master``.
