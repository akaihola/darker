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
- add your information in ``contributors.yaml``
- contributor information will be updated to ``CONTRIBUTORS.rst`` and ``README.rst`` in
  the next release; however, if you have a `GitHub personal access token`_ and want to
  do this yourself, you can run::

      python release_tools/update_contributors.py \
        generate \
        --token=<your GitHub personal access token> \
        --modify-readme \
        --modify-contributors

GitHub is configured to use Github Actions on each pull request to

- run the test suite using Pytest
- do static type checking using Mypy
- lint the code using various linters
- check code formatting using Black

.. _GitHub personal access token:

Creating a GitHub personal access token
---------------------------------------

Below are the necessary steps to create a GitHub token. You can either go interactively
step by step, or start straight at step 6. by clicking on the `Generate new token`_
link. For more information, see `Creating a fine-grained personal access token`_ in
GitHub Docs.

1. `Verify your email address`_, if it hasn't been verified yet.
2. In the upper-right corner of any page, click your profile photo, then click Settings_.

   .. image:: https://docs.github.com/assets/cb-34573/images/help/settings/userbar-account-settings.png
      :width: 150px
3. In the left sidebar, click `Developer settings`_.
4. In the left sidebar, under **Personal access tokens**, click `Fine-grained tokens`_.
5. Click `Generate new token`_.
6. Under **Token name**, enter "``Update Darker contributors``".
7. Under **Expiration**, select an expiration for the token.
8. Under **Description**, type "``Allow darker/release_tools/update_contributors.py to
   retrieve any user's login, full name and link to avatar picture.``"
9. Click **Generate token**.
10. Copy and save the token (you won't be able to see it again), and use it on the
    ``update_contributors.py`` command line as shown above.

.. _Verify your email address: //docs.github.com/en/github/getting-started-with-github/verifying-your-email-address
.. _Settings: https://github.com/settings/profile
.. _Developer settings: https://github.com/settings/apps
.. _Fine-grained tokens: https://github.com/settings/tokens?type=beta
.. _Generate new token: https://github.com/settings/personal-access-tokens/new
.. _Creating a fine-grained personal access token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-fine-grained-personal-access-token


Setting up a development environment
====================================

To set up an isolated virtualenv for Darker development, modify code in your own branch,
run the test suite and lint modified code on a Unix-like system::

    git clone git@github.com:akaihola/darker.git
    python -m venv .venv-darker
    source .venv-darker/bin/activate
    cd darker
    pip install -e '.[test]'
    git checkout -b my-feature-branch
    # modify code
    git commit -m "My feature"
    pytest
    darker --config=check-darker.toml

Darker will fix formatting on modified lines and list any linting errors your changes
may have introduced compared to the branching point of your feature branch from
``master``.

Darker is configured in ``check-darker.toml`` to do the following on modified lines:
- reformat using Black
- sort imports using isort
- run Flake8
- run Mypy
- run Pydocstyle
- run Pylint
- run Ruff

Those tools have also been configured to match the conventions in the Darker code
base.
