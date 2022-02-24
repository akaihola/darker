#!/usr/bin/env python

"""Helper script for templating contributor lists in `README` and `CONTRIBUTORS.rst`

Usage::

    python release_tools/update_contributors.py generate \
        --token=<ghp_your_github_token> \
        --modify-readme \
        --modify-contributors

"""

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import total_ordering
from itertools import groupby
from pathlib import Path
from textwrap import dedent, indent
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Text, cast

import click
from airium import Airium
from requests.models import Response
from requests_cache.session import CachedSession
from ruamel import yaml

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


@click.group()
def cli() -> None:
    """Main command group for command line parsing"""


def _load_contributor_table(path: Path) -> ET.Element:
    """Load and parse the HTML contributor table as seen in `README.rst`

    :param path: Path to `README.rst`
    :return: The parsed HTML as an element tree

    """
    readme = Path(path).read_text(encoding="utf-8")
    match = re.search(r"<table>.*</table>", readme, re.DOTALL)
    assert match
    contributor_table = match.group(0)
    contributor_table = contributor_table.replace("&", "&amp;")
    try:
        return ET.fromstring(contributor_table)
    except ET.ParseError as exc_info:
        linenum, column = exc_info.position
        line = contributor_table.splitlines()[linenum - 1]
        click.echo(line, err=True)
        click.echo((column - 1) * " ", nl=False, err=True)
        click.echo("^", err=True)
        raise


@cli.command()
def verify() -> None:
    """Verify generated contributor table HTML in `README.rst`

    Output the corresponding YAML source.

    """
    root = _load_contributor_table(Path("README.rst"))
    users = {}
    for td_user in root.findall("tr/td"):
        profile_link = td_user[0]
        profile_url = profile_link.attrib["href"]
        username = profile_url.rsplit("/", 1)[-1]
        avatar_alt = profile_link[0].attrib["alt"]
        if username != avatar_alt[1:]:
            click.echo(f"@{username} != {avatar_alt}")
        contributions = []
        for contribution_link in td_user.findall("a")[1:]:
            url = contribution_link.attrib["href"]
            assert url.startswith("https://github.com/")
            path = url[19:]
            contribution_type = contribution_link.attrib["title"]
            if path.startswith("akaihola/darker/issues?q=author%3A"):
                assert contribution_type == "Bug reports"
                link_type = "issues"
            elif path.startswith("akaihola/darker/commits?author="):
                assert contribution_type in {"Code", "Documentation", "Maintenance"}
                link_type = "commits"
            elif path.startswith("akaihola/darker/pulls?q=is%3Apr+reviewed-by%3A"):
                assert contribution_type == "Reviewed Pull Requests"
                link_type = "pulls-reviewed"
            elif path.startswith("akaihola/darker/pulls?q=is%3Apr+author%3A"):
                assert contribution_type in {"Code", "Documentation"}
                link_type = "pulls-author"
            elif path.startswith("akaihola/darker/search?q="):
                assert contribution_type in {"Bug reports", "Answering Questions"}
                link_type = "search"
            elif path.startswith(
                "conda-forge/staged-recipes/search?q=darker&type=issues&author="
            ):
                assert contribution_type == "Code"
                link_type = "conda-issues"
            else:
                assert False, (username, path, contribution_type)
            contributions.append({"type": contribution_type, "link_type": link_type})
        users[username] = contributions
    click.echo(yaml.dump(users))  # type: ignore[attr-defined]


CONTRIBUTION_SYMBOLS = {
    "Bug reports": "🐛",
    "Code": "💻",
    "Documentation": "📖",
    "Reviewed Pull Requests": "👀",
    "Answering Questions": "💬",
    "Maintenance": "🚧",
}
CONTRIBUTION_LINKS = {
    "issues": "akaihola/darker/issues?q=author%3A{username}",
    "commits": "akaihola/darker/commits?author={username}",
    "pulls-reviewed": "akaihola/darker/pulls?q=is%3Apr+reviewed-by%3A{username}",
    "pulls-author": "akaihola/darker/pulls?q=is%3Apr+author%3A{username}",
    "search": "akaihola/darker/search?q={username}",
    "conda-issues": (
        "conda-forge/staged-recipes/search" "?q=darker&type=issues&author={username}"
    ),
}


class GitHubSession(CachedSession):
    """Caching HTTP request session with useful defaults

    - GitHub authorization header generated from a given token
    - Accept HTTP paths and prefix them with the GitHub API server name

    """

    def __init__(self, token: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.token = token

    def request(  # type: ignore[override]  # pylint: disable=arguments-differ
        self,
        method: str,
        url: str,
        headers: MutableMapping[Text, Text] = None,
        **kwargs: Any,
    ) -> Response:
        """Query GitHub API with authorization, caching and host auto-fill-in

        Complete the request information with the GitHub API HTTP scheme and hostname,
        and add a GitHub authorization header. Serve requests from the cache if they
        match.

        :param method: method for the new `Request` object.
        :param url: URL for the new `Request` object.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
                        `Request`.
        :return: The response object

        """
        hdrs = {"Authorization": f"token {self.token}", **(headers or {})}
        if url.startswith("/"):
            url = f"https://api.github.com{url}"
        response = super().request(method, url, headers=hdrs, **kwargs)
        if response.status_code != 200:
            raise RuntimeError(f"{response.status_code} {response.text}")
        return response


AVATAR_URL_TEMPLATE = "https://avatars.githubusercontent.com/u/{}?v=3"


ALL_CONTRIBUTORS_START = (
    "   <!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->\n"
)
ALL_CONTRIBUTORS_END = "   <!-- ALL-CONTRIBUTORS-LIST:END -->"


@cli.command()
@click.option("--token")
@click.option("-r/+r", "--modify-readme/--no-modify-readme", default=False)
@click.option("-c/+c", "--modify-contributors/--no-modify-contributors", default=False)
def generate(token: str, modify_readme: bool, modify_contributors: bool) -> None:
    """Generate an HTML table for `README.rst` and a list for `CONTRIBUTORS.rst`

    These contributor lists are generated based on `contributors.yaml`.

    :param token: The GitHub authorization token for avoiding throttling

    """
    with Path("contributors.yaml").open(encoding="utf-8") as yaml_file:
        users_and_contributions: Dict[str, List[Contribution]] = {
            login: [Contribution(**c) for c in contributions]
            for login, contributions in yaml.main.safe_load(yaml_file).items()
        }
    session = GitHubSession(token)
    users = join_github_users_with_contributions(users_and_contributions, session)
    doc = render_html(users)
    print(doc)
    contributor_list = render_contributor_list(users)
    contributors_text = "\n".join(sorted(contributor_list, key=lambda s: s.lower()))
    print(contributors_text)
    if modify_readme:
        write_readme(doc)
    if modify_contributors:
        write_contributors(contributors_text)


@dataclass
class Contribution:
    """A type of contribution from a user"""

    type: str
    link_type: str

    def github_search_link(self, login: str) -> str:
        """Return a link to a GitHub search for a user's contributions

        :param login: The GitHub username for the user
        :return: A URL link to a GitHub search

        """
        link_template = CONTRIBUTION_LINKS[self.link_type]
        return f"https://github.com/{link_template}".format(username=login)


class GitHubUser(TypedDict):
    """User record as returned by GitHub API `/users/` endpoint"""

    id: int
    name: Optional[str]
    login: str


@dataclass
@total_ordering
class Contributor:
    """GitHub user information coupled with a list of Darker contributions"""

    user_id: int
    name: Optional[str]
    login: str
    contributions: List[Contribution]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Contributor):
            return NotImplemented
        return self.login == other.login

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Contributor):
            return NotImplemented
        return self.display_name < other.display_name

    @property
    def avatar_url(self) -> str:
        """Return a link to the user's avatar image on GitHub

        :return: A URL to the avatar image

        """
        return AVATAR_URL_TEMPLATE.format(self.user_id)

    @property
    def display_name(self) -> str:
        """A user's display name – either the full name or the login username

        :return: The user's display name

        """
        return self.name or self.login


def join_github_users_with_contributions(
    users_and_contributions: Dict[str, List[Contribution]],
    session: GitHubSession,
) -> List[Contributor]:
    """Join GitHub user information with their Darker contributions

    :param users_and_contributions: GitHub user logins and their Darker contributions
    :param session: A GitHub API HTTP session
    :return: GitHub user information and the user's darker contributions merged together

    """
    users: List[Contributor] = []
    for username, contributions in users_and_contributions.items():
        gh_user = cast(GitHubUser, session.get(f"/users/{username}").json())
        try:
            contributor = Contributor(
                gh_user["id"], gh_user["name"], gh_user["login"], contributions
            )
        except KeyError:
            click.echo(gh_user, err=True)
            raise
        users.append(contributor)
    return users


def make_rows(users: List[Contributor], columns: int) -> List[List[Contributor]]:
    """Partition users into table rows

    :param users: User and contribution information for each contributor
    :param columns: Number of columns in the table
    :return: A list of contributor objects for each table row

    """
    users_and_contributions_by_row = groupby(
        enumerate(sorted(users)), lambda item: item[0] // columns
    )
    return [
        [user for _, user in rownum_and_users]
        for _, rownum_and_users in users_and_contributions_by_row
    ]


def render_html(users: List[Contributor]) -> Airium:
    """Convert users and contributions into an HTML table for `README.rst`

    :param users: GitHub user records and the users' contributions to Darker
    :return: An Airium document describing the HTML table

    """
    doc = Airium()
    rows_of_users: List[List[Contributor]] = make_rows(users, columns=6)
    with doc.table():
        for row_of_users in rows_of_users:
            with doc.tr():
                for user in row_of_users:
                    with doc.td(align="center"):
                        with doc.a(href=f"https://github.com/{user.login}"):
                            doc.img(
                                src=user.avatar_url,
                                width="100px;",
                                alt=f"@{user.login}",
                            )
                            doc.br()
                            doc.sub().b(_t=user.display_name)
                        doc.br()
                        for contribution in user.contributions:
                            doc.a(
                                href=contribution.github_search_link(user.login),
                                title=contribution.type,
                                _t=CONTRIBUTION_SYMBOLS[contribution.type],
                            )
    return doc


def render_contributor_list(users: Iterable[Contributor]) -> List[str]:
    """Render a list of contributors for `CONTRIBUTORS.rst`

    :param users_and_contributions: Data from `contributors.yaml`
    :return: A list of strings to go into `CONTRIBUTORS.rst`

    """
    return [f"- {user.display_name} (@{user.login})" for user in users]


def write_readme(doc: Airium) -> None:
    """Write an updated `README.rst` file

    :param doc: The generated contributors HTML table

    """
    readme_content = Path("README.rst").read_text(encoding="utf-8")
    start_index = readme_content.index(ALL_CONTRIBUTORS_START) + len(
        ALL_CONTRIBUTORS_START
    )
    end_index = readme_content.index(ALL_CONTRIBUTORS_END)
    before = readme_content[:start_index]
    after = readme_content[end_index:]
    table = indent(str(doc), "   ")
    new_readme_content = f"{before}{table}{after}"
    Path("README.rst").write_text(new_readme_content, encoding="utf-8")


def write_contributors(text: str) -> None:
    """Write an updated `CONTRIBUTORS.rst` file

    :param text: The generated list of contributors using reStructuredText markup

    """
    Path("CONTRIBUTORS.rst").write_text(
        dedent(
            """\
            ========================
             Contributors to Darker
            ========================

            (in alphabetic order and with GitHub handles)

            {}
            """
        ).format(text),
        encoding="utf-8",
    )


if __name__ == "__main__":
    cli()
