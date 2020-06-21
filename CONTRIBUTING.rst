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
